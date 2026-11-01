export const COMPACT_PLAN_RESULT_FORMAT = 'compact_v1' as const

export function buildPlanResultMessage(summary: Record<string, any> | null | undefined): string {
  const data = summary && typeof summary === 'object' ? summary : {}
  const destination = text(data.destination)
  const origin = text(data.origin)
  const days = positiveInteger(data.days)
  const tripConfig = data.trip_config && typeof data.trip_config === 'object'
    ? data.trip_config
    : {}
  const travelers = positiveInteger(
    tripConfig.travelers || data.travelers || data.people_count,
  )

  const title = destination && days
    ? `${destination}${days}日方案`
    : destination
      ? `${destination}旅行方案`
      : '旅行方案'
  const lines = [`✅ ${title}已生成`]

  const routeParts: string[] = []
  if (origin && destination) routeParts.push(`${origin} → ${destination}`)
  else if (destination) routeParts.push(destination)
  else if (origin) routeParts.push(origin)
  if (days) routeParts.push(`${days}天`)
  if (travelers) routeParts.push(`${travelers}人`)
  if (routeParts.length) lines.push(routeParts.join(' · '))

  const budget = data.budget && typeof data.budget === 'object' ? data.budget : {}
  const estimated = positiveNumber(budget.actual_total, data.estimated_cost)
  const total = positiveNumber(budget.total_budget, data.total_budget)
  const budgetParts: string[] = []
  if (estimated !== null) budgetParts.push(`预计 ¥${formatNumber(estimated)}`)
  if (total !== null) budgetParts.push(`预算 ¥${formatNumber(total)}`)
  if (budgetParts.length) lines.push(budgetParts.join(' / '))

  return lines.slice(0, 3).join('\n')
}

function text(value: unknown): string {
  return String(value || '').trim()
}

function positiveInteger(value: unknown): number {
  const number = Number.parseInt(String(value || 0), 10)
  return Number.isFinite(number) && number > 0 ? number : 0
}

function positiveNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const number = Number(value)
    if (Number.isFinite(number) && number > 0) return number
  }
  return null
}

function formatNumber(value: number): string {
  return value.toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1')
}
