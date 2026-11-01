/**
 * V2.0 Travelogue Store — 游记 & 社交素材 & 分享
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  generateTravelogue, getTravelogues, getTravelogue, updateTravelogue,
  publishTravelogue, generateMaterials, getMaterials, favoriteMaterial,
  createShare, getShareByCode, deleteTravelogue, getTravelogueByTrip,
} from '@/api/travelogue'
import type { TravelogueData, SocialMaterial, ShareData } from '@/api/travelogue'

export const useTravelogueStore = defineStore('travelogue', () => {
  /* ===== State ===== */
  const travelogues = ref<TravelogueData[]>([])
  const current = ref<TravelogueData | null>(null)
  const materials = ref<SocialMaterial[]>([])
  const currentShare = ref<ShareData | null>(null)
  const isGenerating = ref(false)

  /* ===== Getters ===== */
  const publishedTravelogues = computed(() =>
    travelogues.value.filter(t => t.status === 'published' || t.status === 'shared'))
  const draftTravelogues = computed(() =>
    travelogues.value.filter(t => t.status === 'draft'))
  const favoriteMaterials = computed(() =>
    materials.value.filter(m => m.is_favorite))
  const materialsByType = computed(() => {
    const map: Record<string, SocialMaterial[]> = {}
    for (const m of materials.value) {
      (map[m.type] ??= []).push(m)
    }
    return map
  })

  /* ===== Actions ===== */

  async function generate(tripId: string, style: string = 'diary', regenerate = false) {
    isGenerating.value = true
    try {
      const res = await generateTravelogue(tripId, style, regenerate)
      current.value = res.data.data ?? null
      return current.value
    } finally {
      isGenerating.value = false
    }
  }

  async function fetchByTrip(tripId: string) {
    const result = await getTravelogueByTrip(tripId)
    current.value = result.data.data ?? null
    return current.value
  }

  async function fetchList(status?: string) {
    try {
      const result = await getTravelogues({ status })
      travelogues.value = result.data.data?.list ?? []
      return
    } catch {
      if (!_mockLoaded) await loadMockData()
    }
  }

  async function fetchOne(id: string) {
    try {
      const result = await getTravelogue(id)
      current.value = result.data.data ?? null
      return current.value
    } catch {
      // 后端不可用时降级到 mock 数据。
    }
    await loadMockData()
    current.value = travelogues.value.find(t => t.id === id) ?? null
    return current.value
  }

  async function update(id: string, data: Partial<TravelogueData>) {
    const res = await updateTravelogue(id, data)
    current.value = res.data.data ?? current.value
    return current.value
  }

  async function publish(id: string) {
    const res = await publishTravelogue(id)
    current.value = res.data.data ?? current.value
    return current.value
  }

  // ---- Materials ----

  async function generateAllMaterials(tripId: string) {
    isGenerating.value = true
    try {
      const res = await generateMaterials(tripId)
      const newMaterials = res.data.data?.materials ?? []
      materials.value = [...newMaterials, ...materials.value]
      return newMaterials
    } finally {
      isGenerating.value = false
    }
  }

  async function fetchMaterials(tripId: string, type?: string) {
    try {
      const result = await getMaterials(tripId, type)
      materials.value = result.data.data ?? []
      return
    } catch {
      // 后端不可用时直接从 mock 数据降级，不依赖列表是否已加载。
    }
    try {
      const module = await import('@/test/mockTravelogueData')
      let filtered = module.MOCK_MATERIALS.filter(
        material => material.trip_id === tripId && (!type || material.type === type),
      )
      if (!filtered.length) {
        filtered = type
          ? module.MOCK_MATERIALS.filter(material => material.type === type)
          : [...module.MOCK_MATERIALS]
      }
      materials.value = filtered as SocialMaterial[]
    } catch {
      materials.value = []
    }
  }

  async function toggleFavorite(materialId: string, fav: boolean = true) {
    await favoriteMaterial(materialId, fav)
    const m = materials.value.find(m => m.id === materialId)
    if (m) m.is_favorite = fav
  }

  // ---- Shares ----

  async function share(targetType: string, targetId: string, options?: { password?: string; expireHours?: number }) {
    const res = await createShare({
      target_type: targetType,
      target_id: targetId,
      password: options?.password,
      expire_hours: options?.expireHours,
    })
    currentShare.value = res.data.data ?? null
    return currentShare.value
  }

  async function fetchShare(code: string) {
    const res = await getShareByCode(code)
    currentShare.value = res.data.data ?? null
    return currentShare.value
  }

  async function remove(id: string) {
    try {
      await deleteTravelogue(id)
    } catch {
      // 可能无后端，静默从本地移除
    }
    travelogues.value = travelogues.value.filter(t => t.id !== id)
    if (current.value?.id === id) {
      current.value = null
    }
  }

  let _mockLoaded = false
  async function loadMockData() {
    if (_mockLoaded) return
    try {
      const mod = await import('@/test/mockTravelogueData')
      if (mod?.MOCK_TRAVELOGUES?.length) {
        travelogues.value = mod.MOCK_TRAVELOGUES as TravelogueData[]
      }
      if (mod?.MOCK_MATERIALS?.length) {
        materials.value = mod.MOCK_MATERIALS as SocialMaterial[]
      }
      _mockLoaded = true
      console.log(`[Mock] loaded ${travelogues.value?.length ?? 0} travelogues, ${materials.value?.length ?? 0} materials`)
    } catch (e) {
      console.warn('[Mock] failed to load mock data', e)
    }
  }

  function clear() {
    current.value = null
    materials.value = []
    currentShare.value = null
  }

  return {
    travelogues, current, materials, currentShare, isGenerating,
    publishedTravelogues, draftTravelogues, favoriteMaterials, materialsByType,
    generate, fetchByTrip, fetchList, fetchOne, update, publish, remove,
    generateAllMaterials, fetchMaterials, toggleFavorite,
    share, fetchShare, clear, loadMockData,
  }
})
