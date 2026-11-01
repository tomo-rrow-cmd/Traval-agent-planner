"""
自定义异常类
"""


class AppException(Exception):
    """应用基础异常"""

    def __init__(
        self,
        message: str,
        code: int = 10000,
        http_status: int = 500,
    ):
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(self.message)


class NotFoundException(AppException):
    """资源未找到"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code=10003, http_status=404)


class UnauthorizedException(AppException):
    """未授权"""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, code=20001, http_status=401)


class BadRequestException(AppException):
    """请求参数错误"""

    def __init__(self, message: str = "Bad request"):
        super().__init__(message, code=10001, http_status=400)


class PlanExportFormatException(AppException):
    """方案导出格式不支持"""

    def __init__(self, message: str = "Export format not supported"):
        super().__init__(message, code=40006, http_status=400)


class LLMServiceException(AppException):
    """LLM 服务异常"""

    def __init__(self, message: str = "LLM service error"):
        super().__init__(message, code=60003, http_status=502)


class ExternalServiceException(AppException):
    """外部服务异常（地图、天气等）"""

    def __init__(self, message: str = "External service error"):
        super().__init__(message, code=60001, http_status=502)


class NotImplementedAppException(AppException):
    """契约已预留但真实能力尚未实现"""

    def __init__(self, message: str = "Capability not implemented"):
        super().__init__(message, code=70002, http_status=202)
