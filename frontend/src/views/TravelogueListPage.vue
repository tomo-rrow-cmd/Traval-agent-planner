<script setup lang="ts">
/**
 * TravelogueListPage — 游记列表（卡片式布局）
 */
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTravelogueStore } from '@/store/travelogueStore'
import { useUiStore } from '@/store/uiStore'

const router = useRouter()
const store = useTravelogueStore()
const uiStore = useUiStore()

const activeKey = ref<string>('published')
const isLoading = ref(true)
const error = ref<string | null>(null)

const showGenerateModal = ref(false)
const selectedTripId = ref('')
const selectedStyle = ref<string>('diary')
const completedTrips = ref<Array<{id: string; destination: string; completed_at: string}>>([])
const isGenerating = ref(false)

async function loadList() {
  isLoading.value = true
  error.value = null
  try {
    await store.fetchList()
  } catch {
    error.value = '加载失败，请检查网络后重试'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadList)

const publishedList = computed(() => store.publishedTravelogues)
const draftList = computed(() => store.draftTravelogues)

function viewTravelogue(id: string) {
  router.push(`/travelogues/${id}`)
}

// ---- Delete ----

async function handleDelete(id: string) {
  try {
    await store.remove(id)
    uiStore.showSuccess('游记已删除')
  } catch {
    uiStore.showError('删除失败')
  }
}

// ---- Generate ----

async function openGenerateModal() {
  try {
    const { getTrips } = await import('@/api/trip')
    const res = await getTrips({ status: 'completed', page_size: 50 })
    completedTrips.value = (res.data.data?.list ?? []).map((t: any) => ({
      id: t.id,
      destination: t.destination || t.plan_id || '未知行程',
      completed_at: t.completed_at || '',
    }))
    showGenerateModal.value = true
  } catch {
    uiStore.showError('加载行程列表失败')
  }
}

async function handleGenerate() {
  if (!selectedTripId.value) {
    uiStore.showError('请选择行程')
    return
  }
  isGenerating.value = true
  try {
    const existing = await store.fetchByTrip(selectedTripId.value)
    if (existing?.id) {
      showGenerateModal.value = false
      uiStore.showSuccess('该旅行已有主游记，已为您打开')
      router.push(`/travelogues/${existing.id}`)
      return
    }
    await store.generate(selectedTripId.value, selectedStyle.value)
    if (store.current?.id) {
      showGenerateModal.value = false
      uiStore.showSuccess('游记已生成')
      router.push(`/travelogues/${store.current.id}?edit=true`)
    }
  } catch {
    uiStore.showError('游记生成失败')
  } finally {
    isGenerating.value = false
  }
}

// ---- Helpers ----

const failedImages = ref<Set<string>>(new Set())
function onImgError(url: string) {
  failedImages.value = new Set([...failedImages.value, url])
}
function isImgFailed(url: string | null | undefined): boolean {
  return !!url && failedImages.value.has(url)
}

function formatDate(d: string | null | undefined) {
  if (!d) return ''
  return d.slice(0, 10)
}
</script>

<template>
  <div class="travelogue-list-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-content">
        <h1>我的游记</h1>
        <p class="header-sub">
          记录每一次旅行的美好瞬间
        </p>
      </div>
      <div class="header-actions">
        <a-button
          type="primary"
          size="large"
          @click="openGenerateModal"
        >
          <template #icon>
            <span>✏️</span>
          </template>
          生成游记
        </a-button>
      </div>
    </div>

    <!-- Loading -->
    <div
      v-if="isLoading"
      class="state-center"
    >
      <a-spin size="large" />
      <p class="state-desc">
        加载中...
      </p>
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
            @click="loadList"
          >
            重新加载
          </a-button>
        </template>
      </a-result>
    </div>

    <!-- Empty -->
    <div
      v-else-if="!publishedList.length && !draftList.length"
      class="state-center"
    >
      <div class="empty-illustration">
        <svg
          width="120"
          height="120"
          viewBox="0 0 120 120"
          fill="none"
        >
          <rect
            x="20"
            y="25"
            width="80"
            height="70"
            rx="8"
            fill="#f0f5ff"
            stroke="#d6e4ff"
            stroke-width="2"
          />
          <line
            x1="35"
            y1="45"
            x2="85"
            y2="45"
            stroke="#d6e4ff"
            stroke-width="2"
            stroke-linecap="round"
          />
          <line
            x1="35"
            y1="55"
            x2="70"
            y2="55"
            stroke="#d6e4ff"
            stroke-width="2"
            stroke-linecap="round"
          />
          <line
            x1="35"
            y1="65"
            x2="60"
            y2="65"
            stroke="#d6e4ff"
            stroke-width="2"
            stroke-linecap="round"
          />
          <circle
            cx="85"
            cy="75"
            r="15"
            fill="#e6f7ff"
            stroke="#91d5ff"
            stroke-width="2"
          />
          <path
            d="M85 68v14M78 75h14"
            stroke="#91d5ff"
            stroke-width="2"
            stroke-linecap="round"
          />
        </svg>
      </div>
      <h3 class="empty-title">
        还没有游记
      </h3>
      <p class="state-desc">
        完成一次旅行后即可生成精美的 AI 游记
      </p>
      <a-button
        type="primary"
        class="empty-btn"
        @click="openGenerateModal"
      >
        ✏️ 生成第一篇游记
      </a-button>
    </div>

    <!-- Tabs + List -->
    <div
      v-else
      class="list-container"
    >
      <a-tabs
        v-model:active-key="activeKey"
        class="travelogue-tabs"
      >
        <a-tab-pane
          key="published"
          :tab="`已发布`"
          :disabled="!publishedList.length"
        >
          <template v-if="publishedList.length">
            <a-list
              :data-source="publishedList"
              item-layout="vertical"
              :split="false"
            >
              <template #renderItem="{ item }">
                <a-list-item class="travelogue-card">
                  <div
                    class="card-inner"
                    @click="viewTravelogue(item.id)"
                  >
                    <!-- Cover thumbnail -->
                    <div
                      v-if="item.cover_url && !isImgFailed(item.cover_url)"
                      class="card-cover"
                    >
                      <img
                        :src="item.cover_url"
                        :alt="item.title ?? ''"
                        @error="onImgError(item.cover_url!)"
                      >
                    </div>
                    <div
                      v-else
                      class="card-cover card-cover-placeholder"
                    />
                    <!-- Card body -->
                    <div class="card-body">
                      <div class="card-status-inline published">
                        已发布
                      </div>
                      <h3 class="card-title">
                        {{ item.title || '未命名游记' }}
                      </h3>
                      <p class="card-desc">
                        {{ item.content ? item.content.replace(/[#*\n]/g, '').slice(0, 100) + '...' : '暂无内容' }}
                      </p>
                      <div class="card-meta">
                        <span class="meta-item">
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                          ><rect
                            x="3"
                            y="4"
                            width="18"
                            height="18"
                            rx="2"
                          /><line
                            x1="16"
                            y1="2"
                            x2="16"
                            y2="6"
                          /><line
                            x1="8"
                            y1="2"
                            x2="8"
                            y2="6"
                          /><line
                            x1="3"
                            y1="10"
                            x2="21"
                            y2="10"
                          /></svg>
                          {{ item.total_days ?? '-' }}天
                        </span>
                        <span class="meta-item">
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                          ><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle
                            cx="12"
                            cy="10"
                            r="3"
                          /></svg>
                          {{ item.total_pois ?? '-' }}个景点
                        </span>
                        <span
                          v-if="item.total_cost"
                          class="meta-item"
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                          ><circle
                            cx="12"
                            cy="12"
                            r="10"
                          /><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8" /><path d="M12 18V6" /></svg>
                          ¥{{ item.total_cost.toFixed(0) }}
                        </span>
                        <span class="meta-item date">{{ formatDate(item.created_at) }}</span>
                      </div>
                    </div>
                  </div>
                  <template #actions>
                    <a-button
                      type="text"
                      @click.stop="viewTravelogue(item.id)"
                    >
                      <template #icon>
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          stroke-width="2"
                        ><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle
                          cx="12"
                          cy="12"
                          r="3"
                        /></svg>
                      </template>
                      查看
                    </a-button>
                    <a-popconfirm
                      title="确定删除该游记？"
                      @confirm="handleDelete(item.id)"
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
                </a-list-item>
              </template>
            </a-list>
          </template>
          <div
            v-else
            class="tab-empty"
          >
            <a-empty description="还没有已发布的游记" />
          </div>
        </a-tab-pane>
        <a-tab-pane
          key="draft"
          :tab="`草稿`"
          :disabled="!draftList.length"
        >
          <template v-if="draftList.length">
            <a-list
              :data-source="draftList"
              item-layout="vertical"
              :split="false"
            >
              <template #renderItem="{ item }">
                <a-list-item class="travelogue-card">
                  <div
                    class="card-inner"
                    @click="viewTravelogue(item.id)"
                  >
                    <div class="card-cover card-cover-placeholder" />
                    <div class="card-body">
                      <div class="card-status-inline draft">
                        草稿
                      </div>
                      <h3 class="card-title">
                        {{ item.title || '未命名游记' }}
                      </h3>
                      <p class="card-desc">
                        {{ item.content ? item.content.replace(/[#*\n]/g, '').slice(0, 100) + '...' : '暂无内容，点击编辑' }}
                      </p>
                      <div class="card-meta">
                        <span class="meta-item date">{{ formatDate(item.created_at) }}</span>
                      </div>
                    </div>
                  </div>
                  <template #actions>
                    <a-button
                      type="text"
                      @click.stop="router.push(`/travelogues/${item.id}?edit=true`)"
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
                    <a-popconfirm
                      title="确定删除该游记？"
                      @confirm="handleDelete(item.id)"
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
                </a-list-item>
              </template>
            </a-list>
          </template>
          <div
            v-else
            class="tab-empty"
          >
            <a-empty description="还没有草稿" />
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>

    <!-- Generate Modal -->
    <a-modal
      v-model:open="showGenerateModal"
      title="✏️ 生成游记"
      :confirm-loading="isGenerating"
      :ok-text="isGenerating ? '⏳ AI 生成中...' : '开始生成'"
      :width="520"
      :destroy-on-close="true"
      @ok="handleGenerate"
    >
      <a-form layout="vertical">
        <a-form-item
          label="选择行程"
          required
        >
          <a-select
            v-model:value="selectedTripId"
            placeholder="请选择已完成的旅行行程"
            size="large"
          >
            <a-select-option
              v-for="trip in completedTrips"
              :key="trip.id"
              :value="trip.id"
            >
              {{ trip.destination }} — {{ trip.completed_at?.slice(0, 10) }}
            </a-select-option>
          </a-select>
          <div
            v-if="!completedTrips.length"
            class="form-hint"
          >
            暂无已完成行程，请先完成一次旅行再生成游记
          </div>
        </a-form-item>
        <a-form-item label="写作风格">
          <a-radio-group
            v-model:value="selectedStyle"
            class="style-radio-group"
          >
            <a-radio-button value="diary">
              📖 日记风
            </a-radio-button>
            <a-radio-button value="xiaohongshu">
              📱 小红书风
            </a-radio-button>
            <a-radio-button value="guide">
              🗺️ 攻略风
            </a-radio-button>
          </a-radio-group>
          <p class="style-desc">
            {{ { diary: '第一人称叙述，真实感受，自然随意',
                 xiaohongshu: '活泼有趣，带 emoji，适合分享种草',
                 guide: '实用信息优先，结构清晰' }[selectedStyle] }}
          </p>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style scoped>
.travelogue-list-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 24px;
}

/* ===== Page Header ===== */
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 32px;
}
.header-content h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  color: var(--color-text-primary, #1a1a2e);
}
.header-sub {
  margin: 6px 0 0;
  color: var(--color-text-secondary, #999);
  font-size: 14px;
}

/* ===== States ===== */
.state-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}
.state-desc {
  margin-top: 12px;
  color: var(--color-text-secondary, #999);
  font-size: 14px;
}
.empty-illustration {
  margin-bottom: 16px;
  opacity: 0.6;
}
.empty-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--color-text-primary, #333);
}
.empty-btn {
  margin-top: 20px;
}

/* ===== Tabs ===== */
.list-container {
  min-height: 200px;
}
.travelogue-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 24px;
}
.travelogue-tabs :deep(.ant-tabs-nav::before) {
  border-bottom: 1px solid #f0f0f0;
}
.travelogue-tabs :deep(.ant-tabs-tab) {
  font-size: 15px;
  padding: 12px 0;
}
.tab-empty {
  padding: 60px 0;
  text-align: center;
}

/* ===== Cards ===== */
.travelogue-card {
  display: block !important;
  padding: 0 !important;
  margin-bottom: 20px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #f0f0f0;
  overflow: hidden;
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.travelogue-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.card-inner {
  display: flex;
  gap: 0;
  cursor: pointer;
}

.card-cover {
  width: 200px;
  min-height: 160px;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}
.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.card-cover-placeholder {
  background: #f0f0f0;
}
.placeholder-letter {
  display: none;
}
.placeholder-sub {
  display: none;
}
.card-status-inline {
  display: inline-block;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  line-height: 20px;
  margin-bottom: 6px;
}
.card-status-inline.published {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.3);
}
.card-status-inline.draft {
  background: rgba(250, 173, 20, 0.1);
  color: #faad14;
  border: 1px solid rgba(250, 173, 20, 0.3);
}

.card-body {
  flex: 1;
  padding: 20px 24px;
  min-width: 0;
}
.card-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--color-text-primary, #1a1a2e);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-desc {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-secondary, #666);
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}
.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--color-text-tertiary, #999);
  white-space: nowrap;
}
.meta-item svg {
  opacity: 0.6;
}
.meta-item.date {
  margin-left: auto;
}

.travelogue-card :deep(.ant-list-item-action) {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 8px 24px;
  margin: 0 !important;
  background: #fafafa;
  border-top: 1px solid #f5f5f5;
}
.travelogue-card :deep(.ant-list-item-action > li) {
  padding: 0;
}

/* ===== Generate Modal ===== */
.form-hint {
  margin-top: 8px;
  font-size: 13px;
  color: #999;
}
.style-radio-group {
  display: flex;
  gap: 8px;
}
.style-radio-group :deep(.ant-radio-button-wrapper) {
  flex: 1;
  text-align: center;
  height: 40px;
  line-height: 40px;
  border-radius: 8px !important;
}
.style-radio-group :deep(.ant-radio-button-wrapper:not(:first-child)::before) {
  display: none;
}
.style-desc {
  margin: 8px 0 0;
  font-size: 13px;
  color: #999;
}

/* ===== Responsive ===== */
@media (max-width: 640px) {
  .card-inner {
    flex-direction: column;
  }
  .card-cover {
    width: 100%;
    height: 140px;
  }
  .card-body {
    padding: 16px;
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  .header-actions {
    width: 100%;
  }
  .header-actions .ant-btn {
    width: 100%;
  }
}
</style>
