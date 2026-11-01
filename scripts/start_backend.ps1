$ErrorActionPreference = "Stop"

$InitDb = $false
$RebuildVectors = $false
$SkipDbCheck = $false
$NoReload = $false
$BindHost = ""
$PortOverride = ""
$CondaEnv = if ([string]::IsNullOrWhiteSpace($env:BACKEND_CONDA_ENV)) { "ai-travel-planning" } else { $env:BACKEND_CONDA_ENV }
$PythonOverride = $env:BACKEND_PYTHON

function Show-Usage {
  @"
用法:
  .\scripts\start_backend.ps1 [选项]
  scripts\start_backend.cmd [选项]

常用:
  .\scripts\start_backend.ps1
  .\scripts\start_backend.ps1 --init-db
  .\scripts\start_backend.ps1 --rebuild-vectors

选项:
  --init-db             启动前初始化数据库/表结构
  --rebuild-vectors     启动前从 PostgreSQL 重建 Chroma 向量库
  --skip-db-check       跳过 PostgreSQL 连通性检查
  --no-reload           关闭 uvicorn 热重载
  --host HOST           覆盖 .env/settings.HOST
  --port PORT           覆盖 .env/settings.PORT
  --env CONDA_ENV       使用指定 conda 环境，默认 ai-travel-planning
  --python PYTHON       使用指定 Python 解释器，优先级最高
  -h, --help            显示帮助

环境变量:
  BACKEND_CONDA_ENV     默认 conda 环境名
  BACKEND_PYTHON        指定 Python 解释器，等同 --python

Python 选择顺序:
  --python/BACKEND_PYTHON -> 当前 python -> .venv -> conda -> uv -> python/python3/py
"@
}

$RawArgs = @($args)
for ($i = 0; $i -lt $RawArgs.Count; $i++) {
  $arg = [string]$RawArgs[$i]
  $key = $arg.ToLowerInvariant()

  switch -Regex ($key) {
    '^(-{1,2}h|-{1,2}help|/h|\?)$' {
      Show-Usage
      exit 0
    }
    '^--?init-db$|^-initdb$' {
      $InitDb = $true
      continue
    }
    '^--?rebuild-vectors$|^-rebuildvectors$' {
      $RebuildVectors = $true
      continue
    }
    '^--?skip-db-check$|^-skipdbcheck$' {
      $SkipDbCheck = $true
      continue
    }
    '^--?no-reload$|^-noreload$' {
      $NoReload = $true
      continue
    }
    '^--?host$|^-host$' {
      if ($i + 1 -ge $RawArgs.Count) {
        Write-Host "错误：--host 需要地址"
        exit 1
      }
      $i++
      $BindHost = [string]$RawArgs[$i]
      continue
    }
    '^--?port$|^-port$' {
      if ($i + 1 -ge $RawArgs.Count) {
        Write-Host "错误：--port 需要端口"
        exit 1
      }
      $i++
      $PortOverride = [string]$RawArgs[$i]
      continue
    }
    '^--?env$|^-env$' {
      if ($i + 1 -ge $RawArgs.Count) {
        Write-Host "错误：--env 需要 conda 环境名"
        exit 1
      }
      $i++
      $CondaEnv = [string]$RawArgs[$i]
      continue
    }
    '^--?python$|^-python$' {
      if ($i + 1 -ge $RawArgs.Count) {
        Write-Host "错误：--python 需要解释器路径或命令名"
        exit 1
      }
      $i++
      $PythonOverride = [string]$RawArgs[$i]
      continue
    }
    default {
      Write-Host "未知参数：$arg"
      Show-Usage
      exit 1
    }
  }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
  $env:PYTHONPATH = $ProjectRoot
} else {
  $env:PYTHONPATH = "$ProjectRoot;$env:PYTHONPATH"
}

$script:PythonCommand = @()
$script:PythonSource = ""

function Get-CommandPrefix {
  param([string[]]$Command)
  if ($Command.Count -le 1) {
    return @()
  }
  return $Command[1..($Command.Count - 1)]
}

function Invoke-CommandArray {
  param(
    [string[]]$Command,
    [string[]]$Arguments = @(),
    [switch]$Quiet
  )

  $exe = $Command[0]
  $prefix = Get-CommandPrefix -Command $Command
  if ($Quiet) {
    & $exe @prefix @Arguments *> $null
  } else {
    & $exe @prefix @Arguments
  }
  return $LASTEXITCODE
}

function Invoke-CommandArrayCapture {
  param(
    [string[]]$Command,
    [string[]]$Arguments = @()
  )

  $exe = $Command[0]
  $prefix = Get-CommandPrefix -Command $Command
  $output = & $exe @prefix @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    $output | ForEach-Object { Write-Host $_ }
    exit $exitCode
  }
  return @($output)
}

function Invoke-Python {
  param([string[]]$Arguments = @())
  $exitCode = Invoke-CommandArray -Command $script:PythonCommand -Arguments $Arguments
  if ($exitCode -ne 0) {
    exit $exitCode
  }
}

function Invoke-PythonCapture {
  param([string[]]$Arguments = @())
  return Invoke-CommandArrayCapture -Command $script:PythonCommand -Arguments $Arguments
}

function Test-PythonHasCoreDeps {
  param([string[]]$Command)

  $code = @'
import importlib.util

missing = [
    module
    for module in ("uvicorn", "fastapi", "sqlalchemy", "asyncpg")
    if importlib.util.find_spec(module) is None
]
raise SystemExit(1 if missing else 0)
'@
  return (Invoke-CommandArray -Command $Command -Arguments @("-c", $code) -Quiet) -eq 0
}

function Test-CondaPythonAvailable {
  if ([string]::IsNullOrWhiteSpace($CondaEnv)) {
    return $false
  }
  if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    return $false
  }

  & conda run --no-capture-output -n $CondaEnv python -c "import sys" *> $null
  return $LASTEXITCODE -eq 0
}

function Test-UvSupportsRequirements {
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    return $false
  }

  $help = & uv run --help 2>$null
  return ($LASTEXITCODE -eq 0 -and (($help -join "`n") -like "*--with-requirements*"))
}

function Select-PythonCommand {
  if (-not [string]::IsNullOrWhiteSpace($PythonOverride)) {
    $script:PythonCommand = @($PythonOverride)
    $script:PythonSource = "指定 Python"
    return
  }

  if ((Get-Command python -ErrorAction SilentlyContinue) -and (Test-PythonHasCoreDeps -Command @("python"))) {
    $script:PythonCommand = @("python")
    $script:PythonSource = "当前 python"
    return
  }

  $venvCandidates = @(
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
    (Join-Path $ProjectRoot ".venv\bin\python")
  )
  foreach ($candidate in $venvCandidates) {
    if ((Test-Path $candidate) -and (Test-PythonHasCoreDeps -Command @($candidate))) {
      $script:PythonCommand = @($candidate)
      $script:PythonSource = ".venv"
      return
    }
  }

  if (Test-CondaPythonAvailable) {
    $script:PythonCommand = @("conda", "run", "--no-capture-output", "-n", $CondaEnv, "python")
    $script:PythonSource = "conda:$CondaEnv"
    return
  }

  if (Get-Command uv -ErrorAction SilentlyContinue) {
    if ((Test-Path "requirements.txt") -and (Test-UvSupportsRequirements)) {
      $script:PythonCommand = @("uv", "run", "--with-requirements", "requirements.txt", "python")
      $script:PythonSource = "uv + requirements.txt"
    } else {
      $script:PythonCommand = @("uv", "run", "python")
      $script:PythonSource = "uv"
    }
    return
  }

  if (Get-Command python -ErrorAction SilentlyContinue) {
    $script:PythonCommand = @("python")
    $script:PythonSource = "系统 python"
    return
  }

  if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $script:PythonCommand = @("python3")
    $script:PythonSource = "系统 python3"
    return
  }

  if (Get-Command py -ErrorAction SilentlyContinue) {
    $script:PythonCommand = @("py", "-3")
    $script:PythonSource = "Python Launcher"
    return
  }

  Write-Host "错误：未找到可用的 python、python3、py、conda 或 uv。"
  Write-Host "请先安装 Python 3.12+，或安装 uv/conda 后重试。"
  exit 1
}

Select-PythonCommand

Write-Host "=================================================="
Write-Host "AI Travel Planner - 后端启动"
Write-Host "=================================================="
Write-Host "项目目录：$ProjectRoot"
Write-Host "Python：$($script:PythonCommand -join ' ')"
Write-Host "来源：$script:PythonSource"

if (-not (Test-Path ".env")) {
  Write-Host "提示：未找到 .env，将使用代码默认配置。通常首次运行需要先：copy .env.example .env"
}

if (-not (Test-PythonHasCoreDeps -Command $script:PythonCommand)) {
  Write-Host "缺少 Python 依赖或运行器无法准备依赖。"
  if ($script:PythonSource -like "uv*") {
    Write-Host "当前使用 uv，若依赖下载失败，请检查网络后重试。"
  } else {
    Write-Host "请先安装依赖：python -m pip install -r requirements.txt"
  }
  exit 1
}

$settingsCode = @'
from app.config import settings

print(settings.HOST)
print(settings.PORT)
print("1" if settings.DEBUG else "0")
print(settings.LOG_LEVEL.lower())
'@
$settings = Invoke-PythonCapture -Arguments @("-c", $settingsCode)

$AppHost = if ([string]::IsNullOrWhiteSpace($BindHost)) { [string]$settings[0] } else { $BindHost }
$AppPort = if ([string]::IsNullOrWhiteSpace($PortOverride)) { [string]$settings[1] } else { $PortOverride }
$AppDebug = [string]$settings[2]
$AppLogLevel = [string]$settings[3]

try {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, [int]$AppPort)
  $listener.Start()
  $listener.Stop()
} catch {
  Write-Host ""
  Write-Host "错误：端口 $AppPort 已被占用。请先停止旧后端，或用 --port 指定其他端口。"
  exit 1
}

if ($InitDb) {
  if ((-not (Get-Command psql -ErrorAction SilentlyContinue)) -or (-not (Get-Command createdb -ErrorAction SilentlyContinue))) {
    Write-Host "错误：--init-db 需要 PostgreSQL 客户端命令 psql 和 createdb。"
    exit 1
  }

  Write-Host ""
  Write-Host "[1/4] 初始化数据库"
  Invoke-Python -Arguments @("scripts/init_db.py")
} else {
  Write-Host ""
  Write-Host "[1/4] 跳过数据库初始化（需要时加 --init-db）"
}

if (-not $SkipDbCheck) {
  Write-Host ""
  Write-Host "[2/4] 检查 PostgreSQL 连接"
  $dbCheckCode = @'
import asyncio
import sys

from app.db.session import engine


async def main() -> None:
    try:
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        print("PostgreSQL 连接失败。请检查 .env 里的 DATABASE_URL 和本机 PostgreSQL 服务。")
        print(f"错误信息：{exc}")
        print("首次运行可尝试：scripts\\start_backend.cmd --init-db")
        sys.exit(1)
    finally:
        await engine.dispose()


asyncio.run(main())
'@
  Invoke-Python -Arguments @("-c", $dbCheckCode)
} else {
  Write-Host ""
  Write-Host "[2/4] 跳过 PostgreSQL 连接检查"
}

if ($RebuildVectors) {
  Write-Host ""
  Write-Host "[3/4] 重建 Chroma 向量库"
  Invoke-Python -Arguments @("scripts/rebuild_vectors.py")
} else {
  Write-Host ""
  Write-Host "[3/4] 跳过向量库重建（需要时加 --rebuild-vectors）"
}

Write-Host ""
Write-Host "[4/4] 启动 uvicorn"
if ($AppDebug -eq "1") {
  Write-Host "地址：http://localhost:$AppPort/docs"
} else {
  Write-Host "地址：http://localhost:$AppPort"
}

$uvicornArgs = @("-m", "uvicorn", "app.api.router:app", "--host", $AppHost, "--port", $AppPort, "--log-level", $AppLogLevel)
if ((-not $NoReload) -and ($AppDebug -eq "1")) {
  $uvicornArgs += "--reload"
}

$exitCode = Invoke-CommandArray -Command $script:PythonCommand -Arguments $uvicornArgs
exit $exitCode
