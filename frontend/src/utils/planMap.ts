export type PlanMapMarkerType =
  | 'transport'
  | 'attraction'
  | 'food'
  | 'shopping'
  | 'rest'
  | 'entertainment'
  | 'accommodation'

export interface PlanMapMarker {
  position: [number, number]
  title?: string
  content?: string
  type?: string
}

export interface DailyMapData {
  markers: PlanMapMarker[]
  routePath: Array<[number, number]>
  centerPoint: [number, number]
}

type MapRecord = Record<string, any>

const DEFAULT_CENTER: [number, number] = [112.98, 28.19]

export function getMapPosition(item?: MapRecord | null): [number, number] | null {
  if (!item) return null

  const location = item.location || item.coordinates || item
  const lngRaw = location.lng ?? location.longitude
  const latRaw = location.lat ?? location.latitude
  if (lngRaw == null || latRaw == null) return null
  const lng = Number(lngRaw)
  const lat = Number(latRaw)
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null
  if (lng < -180 || lng > 180 || lat < -90 || lat > 90) return null
  return [lng, lat]
}

export function normalizeMapMarkerType(type?: string): PlanMapMarkerType {
  const normalized = String(type || '').toLowerCase()
  const aliases: Record<string, PlanMapMarkerType> = {
    hotel: 'accommodation',
    lodging: 'accommodation',
    restaurant: 'food',
    meal: 'food',
    dining: 'food',
    scenic: 'attraction',
    sight: 'attraction',
  }
  const supported: PlanMapMarkerType[] = [
    'transport',
    'attraction',
    'food',
    'shopping',
    'rest',
    'entertainment',
    'accommodation',
  ]
  return aliases[normalized] || (supported.includes(normalized as PlanMapMarkerType)
    ? normalized as PlanMapMarkerType
    : 'attraction')
}

function activityMarker(activity: MapRecord): PlanMapMarker | null {
  const position = getMapPosition(activity)
  if (!position) return null
  const description = String(activity.reason || activity.description || '').slice(0, 60)
  const content = [activity.time_slot, description].filter(Boolean).join(' · ')
  return {
    position,
    title: activity.title || activity.name || '行程地点',
    content,
    type: normalizeMapMarkerType(activity.type),
  }
}

function mealMarker(meal: MapRecord): PlanMapMarker | null {
  const position = getMapPosition(meal)
  if (!position) return null
  const mealName = meal.meal || '餐饮'
  const price = Number(meal.avg_price) > 0 ? `人均 ¥${Number(meal.avg_price)}` : ''
  return {
    position,
    title: meal.restaurant || meal.name || mealName,
    content: [mealName, price, meal.reason].filter(Boolean).join(' · '),
    type: 'food',
  }
}

function accommodationMarker(accommodation?: MapRecord | null): PlanMapMarker | null {
  const position = getMapPosition(accommodation)
  if (!position) return null
  return {
    position,
    title: accommodation?.hotel_name || accommodation?.name || '酒店',
    content: accommodation?.address || '住宿地点',
    type: 'accommodation',
  }
}

function mealGroup(meal: MapRecord): 'breakfast' | 'lunch' | 'dinner' | 'other' {
  const label = String(meal.meal || '').toLowerCase()
  if (/早餐|早饭|breakfast/.test(label)) return 'breakfast'
  if (/午餐|午饭|lunch/.test(label)) return 'lunch'
  if (/晚餐|晚饭|dinner/.test(label)) return 'dinner'
  return 'other'
}

function sameMarker(a: PlanMapMarker, b: PlanMapMarker): boolean {
  return a.position[0] === b.position[0]
    && a.position[1] === b.position[1]
    && a.title === b.title
}

export function buildDailyMapData(
  day?: MapRecord | null,
  fallbackAccommodation?: MapRecord | null,
): DailyMapData {
  const activities = (day?.activities || day?.attractions || [])
    .map(activityMarker)
    .filter((marker: PlanMapMarker | null): marker is PlanMapMarker => marker !== null)
  const meals: Array<{ meal: MapRecord; marker: PlanMapMarker }> = (day?.meals || [])
    .map((meal: MapRecord) => ({ meal, marker: mealMarker(meal) }))
    .filter((item: { marker: PlanMapMarker | null }): item is { meal: MapRecord; marker: PlanMapMarker } => item.marker !== null)
  const accommodation = accommodationMarker(day?.accommodation || day?.hotel || fallbackAccommodation)

  const breakfast = meals.filter(item => mealGroup(item.meal) === 'breakfast').map(item => item.marker)
  const lunch = meals.filter(item => mealGroup(item.meal) === 'lunch').map(item => item.marker)
  const dinner = meals.filter(item => mealGroup(item.meal) === 'dinner').map(item => item.marker)
  const otherMeals = meals.filter(item => mealGroup(item.meal) === 'other').map(item => item.marker)
  const midpoint = Math.ceil(activities.length / 2)
  const orderedStops = [
    ...breakfast,
    ...activities.slice(0, midpoint),
    ...lunch,
    ...activities.slice(midpoint),
    ...dinner,
    ...otherMeals,
  ]

  const markers: PlanMapMarker[] = []
  for (const marker of accommodation ? [accommodation, ...orderedStops] : orderedStops) {
    if (!markers.some(existing => sameMarker(existing, marker))) markers.push(marker)
  }

  const routePath = markers.map(marker => marker.position)
  if (accommodation && routePath.length > 1) routePath.push(accommodation.position)

  return {
    markers,
    routePath,
    centerPoint: markers[0]?.position || DEFAULT_CENTER,
  }
}
