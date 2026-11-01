<script setup lang="ts">
/* ============================================================
   ExportDropdown — 导出按钮组
   对应文档：前端界面设计文档.md · §4.5
   ============================================================ */

import { ref } from 'vue'
import { useUiStore } from '@/store/uiStore'
import { usePlanStore } from '@/store/planStore'

const props = defineProps<{
  planId: string
}>()

const emit = defineEmits<{
  export: [format: string]
}>()

const uiStore = useUiStore()
const planStore = usePlanStore()
const dropdownOpen = ref(false)
const exporting = ref(false)
const exportMessage = ref('')

const exportFormats = [
  { key: 'md', label: '导出为 Markdown', icon: '📝' },
  { key: 'pdf', label: '导出为 PDF', icon: '📄' },
  { key: 'image', label: '导出为图片', icon: '🖼️' },
  { key: 'docx', label: '导出为 Word', icon: '📃' },
]

function canUseServerExport(planId: string): boolean {
  return Boolean(
    planId
    && planId !== 'detail'
    && planId !== 'test'
    && !planId.startsWith('test_')
    && !planId.startsWith('local_'),
  )
}

async function downloadServerExport(planId: string, format: 'pdf' | 'docx'): Promise<void> {
  const taskResp = await planStore.exportPlan(planId, format)
  const { blob, filename } = await planStore.pollExportTask(
    taskResp.task_id,
    (message: string) => { exportMessage.value = message },
    format,
  )
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

async function handleExport(format: string) {
  dropdownOpen.value = false

  // Markdown: 由父组件做客户端导出
  if (format === 'md') {
    emit('export', format)
    return
  }

  // 图片导出纯前端 html2canvas，不需要后端
  if (format === 'image') {
    exporting.value = true
    exportMessage.value = '正在截取方案图片...'
    try {
      await planStore.exportImage(
        document.getElementById('plan-detail-content') as HTMLElement,
        `travel_plan.png`,
      )
      uiStore.showSuccess('图片已下载')
    } catch (e: any) {
      uiStore.showError(e.message || '图片导出失败')
    } finally {
      exporting.value = false
    }
    return
  }

  exporting.value = true
  exportMessage.value = `正在生成 ${format.toUpperCase()}...`

  const id = props.planId
  const serverExportAvailable = canUseServerExport(id)
  try {
    const title = planStore.currentPlan?.title || 'travel_plan'
    if (format === 'pdf') {
      if (serverExportAvailable) {
        await downloadServerExport(id, 'pdf')
      } else {
        const element = document.getElementById('plan-detail-content')
        if (!element) throw new Error('找不到方案内容')
        await planStore.exportPdf(element, `${title}.pdf`)
      }
      uiStore.showSuccess('PDF 已下载')
      return
    }
    if (format === 'docx') {
      await planStore.exportDocx(`${title}.docx`)
      uiStore.showSuccess('DOCX 已下载')
      return
    }
  } catch (primaryError: any) {
    if (format !== 'docx' || !serverExportAvailable) {
      uiStore.showError(primaryError.message || '导出失败')
      return
    }
    try {
      exportMessage.value = '前端导出失败，正在切换服务器生成...'
      await downloadServerExport(id, 'docx')
      uiStore.showSuccess('DOCX 已下载')
    } catch (serverError: any) {
      uiStore.showError(serverError.message || primaryError.message || '导出失败，请稍后重试')
    }
  } finally {
    exporting.value = false
    exportMessage.value = ''
  }
}
</script>

<template>
  <a-dropdown
    v-model:open="dropdownOpen"
    trigger="click"
    placement="bottomRight"
  >
    <a-button
      class="export-dropdown__trigger"
      :loading="exporting"
    >
      <template #icon>
        <svg
          v-if="!exporting"
          class="export-dropdown__trigger-icon"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line
            x1="12"
            y1="15"
            x2="12"
            y2="3"
          />
        </svg>
      </template>
      {{ exporting ? exportMessage || '导出中...' : '导出' }}
    </a-button>

    <template #overlay>
      <div
        class="export-dropdown__overlay"
        @mousedown.stop
      >
        <div class="export-dropdown__header">
          选择导出格式
        </div>
        <div
          v-for="fmt in exportFormats"
          :key="fmt.key"
          class="export-dropdown__item"
          @click="handleExport(fmt.key)"
        >
          <span class="export-dropdown__item-icon">{{ fmt.icon }}</span>
          <div class="export-dropdown__item-label">
            {{ fmt.label }}
          </div>
        </div>
      </div>
    </template>
  </a-dropdown>
</template>

<style scoped>
/* ===== 触发按钮 ===== */
.export-dropdown__trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  border-color: var(--color-border) !important;
  color: var(--color-text-secondary) !important;
  font-weight: 500;
  padding: 4px 14px !important;
  transition: all 0.2s;
}
.export-dropdown__trigger:hover {
  border-color: var(--color-brand-400) !important;
  color: var(--color-brand-600) !important;
}
.export-dropdown__trigger-icon {
  display: block;
}

/* ===== 下拉菜单 ===== */
.export-dropdown__overlay {
  min-width: 230px;
  padding: var(--space-2);
  background: var(--color-bg-primary, #fff);
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.10), 0 2px 6px rgba(0,0,0,0.04);
  border: 1px solid var(--color-border-light, #eee);
}

.export-dropdown__header {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--color-text-tertiary, #999);
  padding: 6px 12px 4px;
  pointer-events: none;
}

/* ===== 选项 ===== */
.export-dropdown__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.export-dropdown__item:hover {
  background: var(--color-bg-secondary, #f5f5f5);
}
.export-dropdown__item:not(:last-child) {
  margin-bottom: 2px;
}

.export-dropdown__item-icon {
  font-size: 20px;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
}

.export-dropdown__item-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary, #333);
  line-height: 1.4;
}
</style>
