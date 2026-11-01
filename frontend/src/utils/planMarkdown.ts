/**
 * Generate markdown formatted plan from SSE summary data
 */
export function generatePlanMarkdown(summary: Record<string, any>): string {
  const destination = summary.trip_name || summary.destination || ''
  const origin = summary.origin || ''
  const days = summary.days || 0
  const itinerary = summary.daily_itinerary || summary.daily_plan || []
  const budget = summary.budget || {}
  const bigTraffic = summary.big_traffic

  const lines: string[] = []

  // Title
  lines.push(`# 🗺️ ${destination}${days ? `${days}日之旅` : '0日之旅'}`)

  // Route
  if (origin && destination) {
    lines.push(`${origin} → ${destination}`)
  }

  // Daily itinerary
  for (const day of itinerary) {
    const dayNum = day.day || 0
    lines.push(`## 📅 第${dayNum}天`)

    const attractions = day.attractions || day.activities || []
    for (const attr of attractions) {
      const name = attr.name || attr.title || ''
      lines.push(`### ${name}`)
      if (attr.reason) {
        lines.push(attr.reason)
      }
      if (attr.tags) {
        const tags = Array.isArray(attr.tags) ? attr.tags.join(';') : attr.tags
        if (tags) lines.push(`标签: ${tags}`)
      }
    }

    // Meals
    const meals = day.meals || []
    for (const m of meals) {
      const mealType = m.meal || m.type || ''
      const restaurant = m.restaurant || ''
      if (restaurant) {
        const priceStr = m.avg_price ? ` ¥${m.avg_price}` : ''
        lines.push(`${mealType} ${restaurant}${priceStr}`)
      }
    }

    // Hotel
    const hotel = day.hotel || day.accommodation
    if (hotel?.name) {
      lines.push(`${hotel.name}`)
    }
  }

  // Big traffic
  if (bigTraffic) {
    lines.push('## 🚄 推荐车次')
    const trains = Array.isArray(bigTraffic) ? bigTraffic : bigTraffic.trains
    if (Array.isArray(trains)) {
      for (const t of trains) {
        const code = t.trainCode || ''
        if (code) lines.push(`${code} ${t.fromStationName || ''} → ${t.toStationName || ''} ${t.departureTime || ''} - ${t.arrivalTime || ''} (${t.duration || ''})`)
      }
    }
  }

  // Budget
  if (budget && (budget.total_budget || budget.actual_total)) {
    lines.push('## 💰 预算')
    if (budget.total_budget) lines.push(`总预算: ¥${budget.total_budget}`)
    if (budget.actual_total) lines.push(`预估花费: ¥${budget.actual_total}`)
  }

  return lines.join('\n')
}
