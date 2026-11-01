<script setup lang="ts">
/* ============================================================
   ChatInput — 输入框 + 图片上传 + 发送按钮 + 上下文建议
   借鉴 Layla.ai 的上下文建议按钮设计
   对应文档：前端界面设计文档.md · §8.1
   ============================================================ */

import { ref, computed, watch, nextTick } from 'vue'
import { uploadImage } from '@/api/upload'

const emit = defineEmits<{
  'update:modelValue': [value: string]
  send: [content: string, images?: string[]]
  suggest: [value: string]  // 点击建议快捷选项
}>()

const props = withDefaults(defineProps<{
  modelValue?: string
  disabled?: boolean
  suggestions?: string[]  // 上下文建议列表
}>(), {
  modelValue: '',
  disabled: false,
  suggestions: () => [],
})

const content = ref(props.modelValue)
const isComposing = ref(false)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

// 图片上传状态
interface PendingImage {
  id: string
  file: File
  preview: string       // 本地预览 URL (ObjectURL)
  url: string           // 上传后的远程 URL
  uploading: boolean
  error: string | null
}
const selectedImages = ref<PendingImage[]>([])
const isUploading = computed(() => selectedImages.value.some(img => img.uploading))

// 同步父组件 v-model 到本地
watch(() => props.modelValue, (val) => {
  content.value = val
})

// 本地变化同步回父组件
watch(content, (val) => {
  emit('update:modelValue', val)
})

const hasContent = computed(() => content.value.trim().length > 0)

// 解除禁用后自动聚焦输入框
watch(() => props.disabled, (val) => {
  if (!val) {
    nextTick(() => textareaRef.value?.focus())
  }
})

function handleSend() {
  const text = content.value.trim()
  if ((!text && selectedImages.value.length === 0) || isComposing.value || props.disabled || isUploading.value) return
  const urls = selectedImages.value.map(img => img.url).filter(Boolean)
  emit('send', text, urls.length > 0 ? urls : undefined)
  content.value = ''
  selectedImages.value = []
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleSuggestion(value: string) {
  emit('suggest', value)
}

// ========== 图片上传 ==========

function triggerFilePick() {
  fileInputRef.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return

  const remaining = 9 - selectedImages.value.length
  const files = Array.from(input.files).slice(0, remaining)

  for (const file of files) {
    // 校验类型
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      continue
    }
    // 校验大小 (10MB)
    if (file.size > 10 * 1024 * 1024) {
      continue
    }

    const id = `img_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
    const pending: PendingImage = {
      id,
      file,
      preview: URL.createObjectURL(file),
      url: '',
      uploading: true,
      error: null,
    }
    selectedImages.value.push(pending)

    // 异步上传
    uploadImage(file).then(res => {
      pending.url = res.data.data?.url ?? ''
      pending.uploading = false
    }).catch(() => {
      pending.error = '上传失败'
      pending.uploading = false
    })
  }

  // 重置 input 以允许重复选择同一文件
  input.value = ''
}

function removeImage(index: number) {
  const img = selectedImages.value[index]
  if (img.preview) URL.revokeObjectURL(img.preview)
  selectedImages.value.splice(index, 1)
}

const suggestIcons: Record<string, string> = {
  '北京': '🏙️', '上海': '🌆', '广州': '🌇', '深圳': '🌃',
  '成都': '🐼', '重庆': '🌶️', '杭州': '🏞️', '西安': '🏛️',
  '大理': '🌊', '丽江': '🏔️', '三亚': '🏖️', '厦门': '🌅',
  '3天': '📅', '5天': '📅', '7天': '📅',
  '休闲': '😌', '紧凑': '🏃', '美食': '🍜', '文化': '🏛️',
}
</script>

<template>
  <div class="chat-input">
    <!-- 上下文建议按钮（借鉴 Layla/Mindtrip 的 context-aware prompts） -->
    <div
      v-if="suggestions.length > 0 && !hasContent && selectedImages.length === 0"
      class="chat-input__suggestions"
    >
      <button
        v-for="s in suggestions"
        :key="s"
        class="chat-input__chip"
        :disabled="disabled"
        @click="handleSuggestion(s)"
      >
        <span
          v-if="suggestIcons[s]"
          class="chat-input__chip-icon"
        >{{ suggestIcons[s] }}</span>
        {{ s }}
      </button>
    </div>

    <!-- 图片缩略图预览 -->
    <div
      v-if="selectedImages.length > 0"
      class="chat-input__thumbs"
    >
      <div
        v-for="(img, i) in selectedImages"
        :key="img.id"
        class="chat-input__thumb"
        :class="{ 'chat-input__thumb--error': img.error, 'chat-input__thumb--uploading': img.uploading }"
      >
        <img
          :src="img.preview"
          alt=""
        >
        <div
          v-if="img.uploading"
          class="chat-input__thumb-spinner"
        />
        <div
          v-if="img.error"
          class="chat-input__thumb-error"
        >
          !
        </div>
        <button
          class="chat-input__thumb-remove"
          @click="removeImage(i)"
        >
          ✕
        </button>
      </div>
      <span
        v-if="selectedImages.length"
        class="chat-input__thumb-count"
      >{{ selectedImages.length }}/9</span>
    </div>

    <div class="chat-input__wrapper">
      <!-- 图片上传按钮 -->
      <button
        class="chat-input__image-btn"
        :class="{ 'chat-input__image-btn--disabled': disabled || selectedImages.length >= 9 }"
        :disabled="disabled || selectedImages.length >= 9"
        title="上传图片"
        @click="triggerFilePick"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect
            x="3"
            y="3"
            width="18"
            height="18"
            rx="2"
            ry="2"
          />
          <circle
            cx="8.5"
            cy="8.5"
            r="1.5"
          />
          <polyline points="21 15 16 10 5 21" />
        </svg>
      </button>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        hidden
        @change="handleFileChange"
      >

      <textarea
        ref="textareaRef"
        v-model="content"
        class="chat-input__textarea"
        placeholder="输入您的旅行需求..."
        rows="1"
        :disabled="disabled"
        @keydown="handleKeydown"
        @compositionstart="isComposing = true"
        @compositionend="isComposing = false"
      />
      <button
        class="chat-input__send"
        :class="{ 'chat-input__send--active': (hasContent || selectedImages.length > 0) && !disabled && !isUploading }"
        :disabled="(!hasContent && selectedImages.length === 0) || disabled || isUploading"
        @click="handleSend"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <line
            x1="22"
            y1="2"
            x2="11"
            y2="13"
          />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>
    <div class="chat-input__hint">
      <span v-if="disabled">AI 正在生成中...</span>
      <span v-else-if="isUploading">图片上传中...</span>
      <span v-else>按 Enter 发送，Shift + Enter 换行</span>
    </div>
  </div>
</template>

<style scoped>
.chat-input {
  padding: var(--space-4);
  background: var(--color-bg-primary);
  position: relative;
}

/* 装饰顶部分隔线 */
.chat-input::before {
  content: '';
  position: absolute;
  top: 0;
  left: var(--space-6);
  right: var(--space-6);
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-brand-300), transparent);
}

/* 上下文建议按钮 */
.chat-input__suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  animation: slideUp 0.3s var(--ease-out-expo);
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-input__chip {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 6px 14px;
  border: 1.5px solid var(--color-brand-200);
  border-radius: 12px;
  background: var(--color-bg-card);
  color: var(--color-brand-700);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s var(--ease-spring);
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(139, 115, 85, 0.04);
}
.chat-input__chip:hover {
  background: var(--color-brand-50);
  border-color: var(--color-brand-400);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(232, 168, 124, 0.12);
}
.chat-input__chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.chat-input__chip-icon {
  font-size: 14px;
}

/* ===== 图片缩略图预览 ===== */
.chat-input__thumbs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  align-items: center;
}

.chat-input__thumb {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid var(--color-border);
  background: var(--color-bg-tertiary);
  flex-shrink: 0;
}
.chat-input__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chat-input__thumb--uploading {
  opacity: 0.6;
}
.chat-input__thumb--error {
  border-color: #ef4444;
}

.chat-input__thumb-spinner {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.3);
}
.chat-input__thumb-spinner::after {
  content: '';
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.6);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.chat-input__thumb-error {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 16px;
  height: 16px;
  background: #ef4444;
  color: white;
  border-radius: 50%;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-input__thumb-remove {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border: none;
  background: rgba(0,0,0,0.5);
  color: white;
  border-radius: 50%;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s;
}
.chat-input__thumb:hover .chat-input__thumb-remove {
  opacity: 1;
}

.chat-input__thumb-count {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-left: var(--space-1);
}

/* ===== 输入框 ===== */
.chat-input__wrapper {
  display: flex;
  align-items: flex-end;
  gap: var(--space-2);
  background: var(--color-bg-card);
  border: 2px solid var(--color-border);
  border-radius: 16px;
  padding: var(--space-2) var(--space-2) var(--space-2) var(--space-1);
  transition: all 0.25s var(--ease-in-out);
  box-shadow: 0 2px 12px rgba(139, 115, 85, 0.04);
}
.chat-input__wrapper:focus-within {
  border-color: var(--color-brand-400);
  box-shadow: 0 0 0 4px rgba(232, 168, 124, 0.08), 0 4px 20px rgba(139, 115, 85, 0.06);
}

.chat-input__textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  color: var(--color-text-primary);
  background: transparent;
  line-height: 1.6;
  max-height: 120px;
  font-family: inherit;
  padding: var(--space-1) 0;
}
.chat-input__textarea::placeholder {
  color: var(--color-text-placeholder);
}
.chat-input__textarea:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* ===== 图片上传按钮 ===== */
.chat-input__image-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s var(--ease-in-out);
  margin-bottom: 2px;
}
.chat-input__image-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-brand-500);
}
.chat-input__image-btn:active {
  transform: scale(0.92);
}
.chat-input__image-btn--disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.chat-input__image-btn--disabled:hover {
  background: transparent;
  color: var(--color-text-tertiary);
}

/* ===== 发送按钮 ===== */
.chat-input__send {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  border: none;
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.25s var(--ease-spring);
}
.chat-input__send--active {
  background: var(--gradient-gold);
  color: white;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(232, 168, 124, 0.25);
}
.chat-input__send--active:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(232, 168, 124, 0.35);
}
.chat-input__send--active:active {
  transform: scale(0.95);
}

.chat-input__hint {
  font-size: 11px;
  color: var(--color-text-tertiary);
  text-align: right;
  margin-top: var(--space-2);
  opacity: 0.5;
  letter-spacing: 0.3px;
}
</style>
