<script setup lang="ts">
/**
 * V2.0 TraveloguePage — 游记阅览 & 编辑（优化版）
 *
 * 渲染 Markdown 游记 + 9宫格素材 + 精选合集
 * 支持：阅览模式 / 编辑模式 / 分享落地页模式
 */
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTravelogueStore } from '@/store/travelogueStore'
import { useUiStore } from '@/store/uiStore'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import PhotoGrid from '@/components/trip/PhotoGrid.vue'
import MomentCard from '@/components/trip/MomentCard.vue'
import type { SocialMaterial } from '@/api/travelogue'
import { stripDuplicateTravelogueHeading } from '@/utils/travelogue'

const route = useRoute()
const router = useRouter()
const store = useTravelogueStore()
const uiStore = useUiStore()

const travelogueId = computed(() => route.params.id as string)
const isShareView = computed(() => route.name === 'SharedView')
const isEditMode = computed(() => route.query.edit === 'true' && !isShareView.value)

const editTitle = ref('')
const editContent = ref('')
const isSaving = ref(false)

// Loading state
const isLoading = ref(true)
const error = ref<string | null>(null)

// Share
const showShareModal = ref(false)
const shareUrl = ref('')

// Material generation
const materialGenerating = ref(false)
const isRegenerating = ref(false)

const styleLabel = computed(() => ({
  diary: '日记风',
  xiaohongshu: '小红书风',
  guide: '攻略风',
}[store.current?.style || 'diary']))

onMounted(async () => {
  if (isShareView.value) {
    const code = route.params.code as string
    await store.fetchShare(code)
    isLoading.value = false
    return
  }
  isLoading.value = true
  error.value = null
  try {
    await store.fetchOne(travelogueId.value)
    if (store.current) {
      editTitle.value = store.current.title || ''
      editContent.value = store.current.content || ''
      if (store.current.trip_id) {
        store.fetchMaterials(store.current.trip_id).catch(() => {})
      }
    }
  } catch {
    error.value = '加载失败'
  } finally {
    isLoading.value = false
  }
})

watch(() => store.current, (c) => {
  if (c) {
    editTitle.value = c.title || ''
    editContent.value = c.content || ''
  }
}, { immediate: true })

// ---- Save & Publish ----

async function handleSave() {
  if (!travelogueId.value) return
  isSaving.value = true
  try {
    await store.update(travelogueId.value, {
      title: editTitle.value,
      content: editContent.value,
    })
    uiStore.showSuccess('已保存')
  } catch {
    uiStore.showError('保存失败')
  } finally {
    isSaving.value = false
  }
}

async function handlePublish() {
  if (!travelogueId.value) return
  isSaving.value = true
  try {
    await store.update(travelogueId.value, {
      title: editTitle.value,
      content: editContent.value,
    })
    await store.publish(travelogueId.value)
    uiStore.showSuccess('游记已发布')
    router.replace(`/travelogues/${travelogueId.value}`)
  } catch {
    uiStore.showError('发布失败')
  } finally {
    isSaving.value = false
  }
}

async function handleRegenerate() {
  const current = store.current
  if (!current?.trip_id || current.status !== 'draft') return
  isRegenerating.value = true
  try {
    await store.generate(current.trip_id, current.style || 'diary', true)
    uiStore.showSuccess('整趟游记初稿已重新生成')
  } catch (error: any) {
    uiStore.showError(error?.response?.data?.detail || '重新生成失败')
  } finally {
    isRegenerating.value = false
  }
}

function insertMaterialContent(mat: SocialMaterial) {
  const block = `\n\n## ${mat.title || ''}\n${mat.content || ''}${mat.hashtags?.length ? '\n' + mat.hashtags.join(' ') : ''}\n`
  editContent.value += block
  uiStore.showSuccess('素材内容已插入')
}

function handleFavoriteMaterial(id: string, fav: boolean) {
  store.toggleFavorite(id, fav)
}

// ---- Share ----

async function handleShare() {
  if (!travelogueId.value) return
  try {
    const result = await store.share('travelogue', travelogueId.value)
    if (result) {
      shareUrl.value = result.share_url
      showShareModal.value = true
    }
  } catch {
    uiStore.showError('生成分享链接失败')
  }
}

function copyShareLink() {
  navigator.clipboard.writeText(shareUrl.value).then(() => {
    uiStore.showSuccess('链接已复制')
  }).catch(() => {
    uiStore.showError('复制失败，请手动复制')
  })
}

// ---- Delete ----

async function handleDelete() {
  if (!travelogueId.value) return
  try {
    await store.remove(travelogueId.value)
    uiStore.showSuccess('游记已删除')
    router.push('/travelogues')
  } catch {
    uiStore.showError('删除失败')
  }
}

// ---- Material Generation ----

async function handleGenerateMaterials() {
  if (!store.current?.trip_id) return
  materialGenerating.value = true
  try {
    await store.generateAllMaterials(store.current.trip_id)
    uiStore.showSuccess('社交素材已生成')
  } catch {
    uiStore.showError('素材生成失败')
  } finally {
    materialGenerating.value = false
  }
}

function groupMaterialsByDay(): Record<number, SocialMaterial[]> {
  const grouped: Record<number, SocialMaterial[]> = {}
  for (const m of store.materials) {
    const day = m.source_day ?? 0
    ;(grouped[day] ??= []).push(m)
  }
  return grouped
}

function formatContent(text: string): string {
  if (!text) return ''
  const title = store.current?.title?.trim() || ''
  const normalizedText = stripDuplicateTravelogueHeading(text, title)
  const raw = marked.parse(normalizedText, { breaks: true }) as string
  return DOMPurify.sanitize(raw)
}
</script>

<template>
  <div class="travelogue-page">
    <!-- ===== Toolbar ===== -->
    <div
      class="toolbar"
      :class="{ editing: isEditMode }"
    >
      <div class="toolbar-left">
        <a-button
          type="text"
          @click="router.push('/travelogues')"
        >
          <template #icon>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            ><line
              x1="19"
              y1="12"
              x2="5"
              y2="12"
            /><polyline points="12 19 5 12 12 5" /></svg>
          </template>
          返回
        </a-button>
      </div>
      <div class="toolbar-center">
        <span class="toolbar-title">{{ isEditMode ? '编辑游记' : store.current?.title || '游记详情' }}</span>
      </div>
      <div class="toolbar-right">
        <!-- View mode actions -->
        <template v-if="!isEditMode && !isShareView && store.current">
          <a-button
            type="text"
            @click="router.push(`/travelogues/${travelogueId}?edit=true`)"
          >
            <template #icon>
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              ><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
            </template>
            编辑
          </a-button>
          <a-button
            v-if="store.current?.status === 'published'"
            type="text"
            @click="handleShare"
          >
            <template #icon>
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              ><circle
                cx="18"
                cy="5"
                r="3"
              /><circle
                cx="6"
                cy="12"
                r="3"
              /><circle
                cx="18"
                cy="19"
                r="3"
              /><line
                x1="8.59"
                y1="13.51"
                x2="15.42"
                y2="17.49"
              /><line
                x1="15.41"
                y1="6.51"
                x2="8.59"
                y2="10.49"
              /></svg>
            </template>
            分享
          </a-button>
          <a-popconfirm
            title="确定删除该游记？"
            @confirm="handleDelete"
          >
            <a-button
              type="text"
              danger
              @click.stop
            >
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                ><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
              </template>
              删除
            </a-button>
          </a-popconfirm>
        </template>
        <!-- Edit mode actions -->
        <template v-if="isEditMode">
          <a-popconfirm
            v-if="store.current?.status === 'draft'"
            title="重新生成会覆盖当前草稿，确定继续？"
            @confirm="handleRegenerate"
          >
            <a-button :loading="isRegenerating">
              ✨ AI 重新生成全文
            </a-button>
          </a-popconfirm>
          <a-button
            :loading="isSaving"
            @click="handleSave"
          >
            💾 保存草稿
          </a-button>
          <a-button
            v-if="store.current?.status === 'draft'"
            type="primary"
            :loading="isSaving"
            @click="handlePublish"
          >
            📢 发布
          </a-button>
          <a-popconfirm
            title="确定删除该游记？"
            @confirm="handleDelete"
          >
            <a-button
              danger
              @click.stop
            >
              🗑️ 删除
            </a-button>
          </a-popconfirm>
        </template>
      </div>
    </div>

    <!-- ===== Content ===== -->
    <div class="page-content">
      <!-- Loading skeleton -->
      <div
        v-if="isLoading"
        class="skeleton-container"
      >
        <div class="skeleton-cover" />
        <div class="skeleton-body">
          <div class="skeleton-line w-60" />
          <div class="skeleton-line w-80" />
          <div class="skeleton-line w-40" />
          <div class="skeleton-line w-90" />
          <div class="skeleton-line w-70" />
        </div>
      </div>

      <!-- Error -->
      <div
        v-else-if="error"
        class="state-center"
      >
        <a-result
          status="error"
          :title="error"
        >
          <template #extra>
            <a-button
              type="primary"
              @click="router.push('/travelogues')"
            >
              返回列表
            </a-button>
          </template>
        </a-result>
      </div>

      <!-- Edit Mode -->
      <template v-else-if="isEditMode && store.current">
        <div class="edit-layout">
          <div class="edit-main">
            <div class="edit-title-area">
              <input
                v-model="editTitle"
                class="edit-title-input"
                placeholder="游记标题"
              >
            </div>
            <div class="edit-content-area">
              <textarea
                v-model="editContent"
                class="edit-content-textarea"
                placeholder="用 Markdown 记录你的旅行..."
              />
            </div>
          </div>
          <!-- Material Sidebar -->
          <aside
            v-if="store.materials.length > 0"
            class="material-sidebar"
          >
            <div class="sidebar-header">
              <h3>📦 素材库</h3>
              <span class="sidebar-count">{{ store.materials.length }}</span>
            </div>
            <div class="sidebar-body">
              <div
                v-for="(dayMaterials, day) in groupMaterialsByDay()"
                :key="day"
                class="sidebar-group"
              >
                <h4 v-if="Number(day) > 0">
                  Day {{ day }}
                </h4>
                <div
                  v-for="mat in dayMaterials"
                  :key="mat.id"
                  class="sidebar-card"
                  @click="insertMaterialContent(mat)"
                >
                  <div class="sidebar-card-preview">
                    <img
                      v-if="mat.images?.[0]?.url"
                      :src="mat.images[0].url"
                      alt=""
                    >
                    <span
                      v-else
                      class="sidebar-card-type-icon"
                    >{{ mat.type === 'moment_9grid' ? '🖼' : '📇' }}</span>
                  </div>
                  <div class="sidebar-card-info">
                    <div class="sidebar-card-title">
                      {{ mat.title || '未命名' }}
                    </div>
                    <div class="sidebar-card-type">
                      {{ mat.type === 'moment_9grid' ? '9宫格' : mat.type === 'day_summary' ? '日总结' : mat.type === 'trip_highlight' ? '精选' : mat.type === 'budget_card' ? '预算' : mat.type }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </template>

      <!-- View mode -->
      <template v-else-if="store.current">
        <div class="view-layout">
          <article class="view-main">
            <!-- Cover -->
            <div
              v-if="store.current.cover_url"
              class="cover-section"
            >
              <img
                :src="store.current.cover_url"
                :alt="store.current.title ?? ''"
                class="cover-img"
              >
              <div class="cover-overlay">
                <div class="cover-meta-bar">
                  <span
                    v-if="store.current.status === 'published'"
                    class="cover-badge"
                  >已发布</span>
                  <span
                    v-else
                    class="cover-badge draft-badge"
                  >草稿</span>
                </div>
                <h1 class="cover-title">
                  {{ store.current.title }}
                </h1>
              </div>
            </div>
            <div
              v-else
              class="title-section"
            >
              <h1>{{ store.current.title }}</h1>
            </div>

            <div class="travelogue-summary">
              <div class="summary-badges">
                <span class="summary-badge primary">整趟旅行游记</span>
                <span class="summary-badge">按天组织</span>
                <span class="summary-badge">{{ styleLabel }}</span>
                <span class="summary-badge ai">AI 生成初稿，可编辑</span>
              </div>
              <div class="summary-stats">
                <span>{{ store.current.total_days || 0 }} 天</span>
                <span class="dot">·</span>
                <span>{{ store.current.total_pois || 0 }} 个实际打卡</span>
                <template v-if="store.current.total_cost && store.current.total_cost > 0">
                  <span class="dot">·</span>
                  <span>实际花费 ¥{{ store.current.total_cost.toFixed(0) }}</span>
                </template>
                <template v-else>
                  <span class="dot">·</span>
                  <span>尚未记录实际花费</span>
                </template>
              </div>
            </div>

            <!-- Markdown content -->
            <div
              v-if="store.current.content"
              class="content-section"
            >
              <!-- eslint-disable vue/no-v-html -->
              <div
                class="markdown-body"
                v-html="formatContent(store.current.content)"
              />
              <!-- eslint-enable vue/no-v-html -->
            </div>

            <!-- Photos -->
            <section
              v-if="store.current.photos?.length"
              class="section-block"
            >
              <div class="section-divider">
                <span class="section-icon">📸</span>
                <h2>旅行相册</h2>
              </div>
              <PhotoGrid
                :images="store.current.photos.map((url, i) => ({ url, order: i + 1 }))"
                layout="card-layout"
              />
            </section>

            <!-- Social Materials -->
            <section
              v-if="store.current.trip_id"
              class="section-block"
            >
              <div class="section-divider">
                <span class="section-icon">🎨</span>
                <h2>社交素材</h2>
                <a-button
                  size="small"
                  class="section-action"
                  :loading="materialGenerating"
                  @click="handleGenerateMaterials"
                >
                  {{ materialGenerating ? '生成中...' : '一键生成' }}
                </a-button>
              </div>
              <template v-if="store.materials.length > 0">
                <div
                  v-for="(dayMaterials, day) in groupMaterialsByDay()"
                  :key="day"
                  class="day-group"
                >
                  <h3
                    v-if="Number(day) > 0"
                    class="day-label"
                  >
                    Day {{ day }}
                  </h3>
                  <div class="materials-grid">
                    <MomentCard
                      v-for="mat in dayMaterials"
                      :key="mat.id"
                      :material="mat"
                      @favorite="handleFavoriteMaterial"
                    />
                  </div>
                </div>
              </template>
              <div
                v-else
                class="section-empty"
              >
                <p>暂无社交素材，点击上方按钮一键生成</p>
              </div>
            </section>

            <!-- Footer -->
            <div class="view-footer">
              <div class="footer-divider" />
              <p class="footer-text">
                AI 辅助生成 · {{ store.current.created_at?.slice(0, 10) }}
              </p>
            </div>
          </article>
        </div>
      </template>

      <!-- Share view -->
      <div
        v-else-if="isShareView && store.currentShare"
        class="share-view"
      >
        <div class="share-card">
          <div class="share-card-icon">
            🔗
          </div>
          <h2>分享链接</h2>
          <p>该游记通过分享链接访问</p>
          <div class="share-stats">
            <span>👁️ {{ store.currentShare.view_count ?? 0 }} 次浏览</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Share Modal -->
    <a-modal
      v-model:open="showShareModal"
      title="🔗 分享游记"
      :footer="null"
      :width="480"
    >
      <div class="share-modal-content">
        <p class="share-label">
          分享链接：
        </p>
        <div class="share-url-box">
          <input
            :value="shareUrl"
            readonly
            class="share-url-input"
            @click="($event.target as HTMLInputElement).select()"
          >
          <a-button
            type="primary"
            @click="copyShareLink"
          >
            复制链接
          </a-button>
        </div>
        <p class="share-hint">
          👁️ 任何人通过此链接可查看游记，链接含访问计数
        </p>
      </div>
    </a-modal>
  </div>
</template>

<style scoped>
/* ===== Layout ===== */
.travelogue-page {
  min-height: 100vh;
  background: #f8f9fa;
}

/* ===== Toolbar ===== */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  position: sticky;
  top: 0;
  z-index: 100;
}
.toolbar.editing {
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 160px;
}
.toolbar-right {
  justify-content: flex-end;
}
.toolbar-center {
  flex: 1;
  text-align: center;
}
.toolbar-title {
  font-size: 14px;
  font-weight: 500;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
  display: inline-block;
}

/* ===== Page Content ===== */
.page-content {
  max-width: 840px;
  margin: 0 auto;
  padding: 0 24px 60px;
}

/* ===== Loading Skeleton ===== */
.skeleton-container {
  padding: 24px 0;
}
.skeleton-cover {
  height: 280px;
  border-radius: 12px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  margin-bottom: 32px;
}
.skeleton-body {
  padding: 0 4px;
}
.skeleton-line {
  height: 16px;
  border-radius: 8px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  margin-bottom: 12px;
}
.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-80 { width: 80%; }
.skeleton-line.w-40 { width: 40%; }
.skeleton-line.w-90 { width: 90%; }
.skeleton-line.w-70 { width: 70%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ===== Cover Section ===== */
.cover-section {
  position: relative;
  margin: 24px 0 32px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0,0,0,0.1);
}
.cover-img {
  width: 100%;
  height: 360px;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
}
.cover-section:hover .cover-img {
  transform: scale(1.03);
}
.cover-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 60px 32px 28px;
  background: linear-gradient(transparent 20%, rgba(0,0,0,0.75));
  color: #fff;
}
.cover-meta-bar {
  margin-bottom: 12px;
}
.cover-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(82, 196, 26, 0.85);
  color: #fff;
}
.cover-badge.draft-badge {
  background: rgba(250, 173, 20, 0.85);
}
.cover-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 10px;
  line-height: 1.3;
}
.cover-stats {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  opacity: 0.9;
}
.cover-stats .dot {
  margin: 0 4px;
  opacity: 0.5;
}

.title-section {
  padding: 32px 0 24px;
}
.title-section h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  color: var(--color-text-primary, #1a1a2e);
}

.travelogue-summary {
  margin: 0 0 28px;
  padding: 16px 20px;
  border: 1px solid #eee8df;
  border-radius: 12px;
  background: #fffcf8;
}
.summary-badges,
.summary-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.summary-stats {
  margin-top: 12px;
  color: #6f685f;
  font-size: 14px;
}
.summary-badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f2eee8;
  color: #746b61;
  font-size: 12px;
}
.summary-badge.primary {
  background: #e6f4ef;
  color: #3e806d;
}
.summary-badge.ai {
  background: #eef4ff;
  color: #4c72a8;
}

/* ===== Content Section ===== */
.content-section {
  padding: 0 4px 32px;
}
.markdown-body {
  line-height: 1.9;
  font-size: 16px;
  color: var(--color-text-primary, #333);
}
.markdown-body :deep(h1) { font-size: 26px; margin: 28px 0 14px; }
.markdown-body :deep(h2) {
  font-size: 21px;
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #f0f0f0;
}
.markdown-body :deep(h3) { font-size: 18px; margin: 20px 0 10px; }
.markdown-body :deep(p) { margin: 0 0 16px; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 24px; margin: 0 0 16px; }
.markdown-body :deep(li) { margin-bottom: 6px; }
.markdown-body :deep(blockquote) {
  border-left: 4px solid #1890ff;
  margin: 16px 0;
  padding: 12px 20px;
  background: #f8f9fa;
  border-radius: 0 8px 8px 0;
  color: #555;
}
.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 10px;
  margin: 16px 0;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(code) {
  background: #f5f5f5;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 14px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.markdown-body :deep(pre) {
  background: #f6f8fa;
  border-radius: 10px;
  padding: 16px 20px;
  overflow-x: auto;
  margin: 16px 0;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}
.markdown-body :deep(hr) {
  margin: 32px 0;
  border: none;
  border-top: 2px solid #f0f0f0;
}
.markdown-body :deep(a) { color: #1890ff; text-decoration: none; }
.markdown-body :deep(a:hover) { text-decoration: underline; }
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 14px;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  padding: 10px 14px;
  border: 1px solid #e8e8e8;
  text-align: left;
}
.markdown-body :deep(th) { background: #fafafa; font-weight: 600; }

/* ===== Section Blocks ===== */
.section-block {
  margin: 40px 0;
}
.section-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}
.section-icon {
  font-size: 20px;
}
.section-divider h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary, #333);
  flex: 1;
}
.section-action {
  flex-shrink: 0;
}
.section-empty {
  padding: 40px 0;
  text-align: center;
  color: #999;
}

.day-group {
  margin-bottom: 28px;
}
.day-label {
  font-size: 15px;
  font-weight: 600;
  color: #1890ff;
  margin: 0 0 12px;
}
.materials-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

/* ===== View Footer ===== */
.view-footer {
  margin: 48px 0 24px;
  text-align: center;
}
.footer-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e0e0e0, transparent);
  margin-bottom: 12px;
}
.footer-text {
  font-size: 13px;
  color: #bbb;
  margin: 0;
}

/* ===== Share View ===== */
.share-view {
  padding: 80px 0;
  text-align: center;
}
.share-card {
  background: #fff;
  border-radius: 16px;
  padding: 48px 32px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.share-card-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.share-card h2 {
  font-size: 20px;
  margin: 0 0 8px;
}
.share-stats {
  margin-top: 16px;
  color: #999;
}

/* ===== State Center ===== */
.state-center {
  padding: 80px 0;
  text-align: center;
}

/* ===== Share Modal ===== */
.share-modal-content {
  padding: 8px 0;
}
.share-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}
.share-url-box {
  display: flex;
  gap: 8px;
}
.share-url-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  background: #fafafa;
  outline: none;
  cursor: text;
}
.share-hint {
  margin-top: 12px;
  font-size: 13px;
  color: #999;
}

/* ===== Edit Layout ===== */
.edit-layout {
  display: flex;
  gap: 24px;
  padding: 24px 0;
  min-height: calc(100vh - 56px);
}
.edit-main {
  flex: 1;
  min-width: 0;
}
.edit-title-area {
  margin-bottom: 20px;
}
.edit-title-input {
  width: 100%;
  font-size: 28px;
  font-weight: 700;
  border: none;
  outline: none;
  padding: 8px 0 12px;
  border-bottom: 2px solid #e8e8e8;
  transition: border-color 0.2s;
  background: transparent;
  color: var(--color-text-primary, #333);
}
.edit-title-input:focus {
  border-color: #1890ff;
}
.edit-content-area {
}
.edit-content-textarea {
  width: 100%;
  min-height: 60vh;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  padding: 16px 20px;
  font-size: 15px;
  line-height: 1.8;
  resize: vertical;
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fff;
}
.edit-content-textarea:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.08);
}

/* ===== Material Sidebar (edit mode) ===== */
.material-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #f0f0f0;
  max-height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
  border-bottom: 1px solid #f5f5f5;
}
.sidebar-header h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}
.sidebar-count {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 1px 8px;
  border-radius: 10px;
}
.sidebar-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}
.sidebar-group {
  margin-bottom: 16px;
}
.sidebar-group h4 {
  font-size: 12px;
  color: #1890ff;
  font-weight: 600;
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.sidebar-card {
  display: flex;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #fafafa;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;
}
.sidebar-card:hover {
  background: #e6f7ff;
  transform: translateX(2px);
}
.sidebar-card-preview {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
}
.sidebar-card-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.sidebar-card-type-icon {
  font-size: 18px;
}
.sidebar-card-info {
  flex: 1;
  min-width: 0;
}
.sidebar-card-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sidebar-card-type {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .toolbar {
    padding: 0 12px;
  }
  .toolbar-center {
    display: none;
  }
  .toolbar-left, .toolbar-right {
    min-width: auto;
  }
  .page-content {
    padding: 0 12px 40px;
  }
  .cover-img {
    height: 220px;
  }
  .cover-overlay {
    padding: 40px 20px 20px;
  }
  .cover-title {
    font-size: 22px;
  }
  .edit-layout {
    flex-direction: column;
  }
  .material-sidebar {
    width: 100%;
    max-height: 300px;
  }
  .markdown-body {
    font-size: 15px;
  }
}
</style>
