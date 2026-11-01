/* ============================================================
   高德地图配置
   使用前请替换为您的 High德地图 JS API Key
   ============================================================ */

export const MAP_CONFIG = {
  // 高德地图 JS API Key（安全起见推荐通过 VITE_AMAP_KEY 环境变量注入）
  key: import.meta.env.VITE_AMAP_KEY || '您的_AMap_JSAPI_Key',

  // 地图版本
  version: '2.0',

  // 默认中心点（大理古城）
  center: [100.156, 25.678] as [number, number],

  // 默认缩放级别
  zoom: 13,

  // 主题样式
  // - normal: 默认
  // - dark: 暗色
  // - light: 清新
  theme: 'light' as 'normal' | 'dark' | 'light',

  // 安全密钥（可选，JSAPI2.0 推荐使用）
  securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE || '',
}
