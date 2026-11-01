/**
 * 签到/行程执行 Mock 数据
 *
 * 基于「长沙7日深度游」方案（与 planStore 的 loadTestPlan 一致），
 * 模拟真实旅行场景：Day4 进行中，每天签到记录有连贯叙事。
 */
import type { TripState, TripProgress, CheckinRecord, ExpenseRecord, AdjustmentRecord } from '@/api/trip'

// ======================================================================
// 基础行程数据 — 长沙7日，Day4 进行中
// ======================================================================
export const mockTrip: TripState = {
  id: 'mock_trip_changsha',
  plan_id: 'test_plan_001',
  user_id: 'mock_user',
  status: 'active',
  current_day: 4,
  total_pois: 21,
  checked_in: 12,
  started_at: '2026-07-10T08:00:00Z',
  paused_at: null,
  completed_at: null,
  last_lat: 28.193,
  last_lng: 112.947,
  budget_total: 5000,
  budget_spent: 3120,
  budget_remain: 1880,
  created_at: '2026-07-10T08:00:00Z',
  updated_at: '2026-07-13T21:30:00Z',
}

export const mockProgress: TripProgress = {
  trip_id: 'mock_trip_changsha',
  status: 'active',
  current_day: 4,
  progress_pct: 57,
  checked_in: 12,
  total_pois: 21,
  budget_total: 5000,
  budget_spent: 3120,
  budget_remain: 1880,
  time_delta_total_min: 65,
  last_location: { lat: 28.193, lng: 112.947 },
}

// ======================================================================
// 每日签到记录（与方案 daily_itinerary 对应）
// ======================================================================

// --- Day 1: 岳麓山 → 橘子洲 → 太平老街 ---
export const day1Checkins: CheckinRecord[] = [
  {
    id: 'ck_d1_01', trip_id: 'mock_trip_changsha',
    poi_type: 'attraction', poi_name: '岳麓山', source_day: 1,
    lat: 28.193, lng: 112.947,
    photos: [],
    planned_at: '09:00', actual_at: '2026-07-10T09:15:00Z',
    time_delta_min: 15, planned_cost: 0, actual_cost: 0,
    rating: 5, note: '南大门上山半小时到山顶，俯瞰湘江橘子洲，湘江如带橘子洲如舟，真·山水洲城',
    created_at: '2026-07-10T09:15:00Z',
  },
  {
    id: 'ck_d1_02', trip_id: 'mock_trip_changsha',
    poi_type: 'attraction', poi_name: '橘子洲', source_day: 1,
    lat: 28.175, lng: 112.960,
    photos: [],
    planned_at: '14:00', actual_at: '2026-07-10T14:25:00Z',
    time_delta_min: 25, planned_cost: 0, actual_cost: 40,
    rating: 4, note: '坐小火车到毛泽东雕塑（往返¥40），青年毛泽东雕像面朝东南方向，眼神坚毅',
    created_at: '2026-07-10T14:25:00Z',
  },
  {
    id: 'ck_d1_03', trip_id: 'mock_trip_changsha',
    poi_type: 'restaurant', poi_name: '太平老街', source_day: 1,
    lat: 28.197, lng: 112.978,
    photos: [],
    planned_at: '18:00', actual_at: '2026-07-10T18:30:00Z',
    time_delta_min: 30, planned_cost: 60, actual_cost: 85,
    rating: 4, note: '黑色经典臭豆腐¥20、糖油粑粑¥15、大香肠¥13、茶颜悦色¥18，烟火气十足',
    created_at: '2026-07-10T18:30:00Z',
  },
  {
    id: 'ck_d1_04', trip_id: 'mock_trip_changsha',
    poi_type: 'hotel', poi_name: '匠宿酒店(五一广场)', source_day: 1,
    lat: 28.195, lng: 112.979,
    photos: [],
    planned_at: '21:00', actual_at: '2026-07-10T21:15:00Z',
    time_delta_min: 15, planned_cost: 400, actual_cost: 400,
    rating: 5, note: '五一广场核心位置，楼下就是地铁口，房间干净还有小阳台',
    created_at: '2026-07-10T21:15:00Z',
  },
]

// --- Day 2: 省博物馆 → 天心阁 → 坡子街 ---
export const day2Checkins: CheckinRecord[] = [
  {
    id: 'ck_d2_01', trip_id: 'mock_trip_changsha',
    poi_type: 'attraction', poi_name: '湖南省博物馆', source_day: 2,
    lat: 28.209, lng: 113.004,
    photos: [],
    planned_at: '09:00', actual_at: '2026-07-11T09:10:00Z',
    time_delta_min: 10, planned_cost: 0, actual_cost: 0,
    rating: 5, note: '提前三天公众号预约的，辛追夫人遗体保存之好令人难以置信，素纱襌衣49克薄如蝉翼',
    created_at: '2026-07-11T09:10:00Z',
  },
  {
    id: 'ck_d2_02', trip_id: 'mock_trip_changsha',
    poi_type: 'attraction', poi_name: '天心阁', source_day: 2,
    lat: 28.186, lng: 112.982,
    photos: [],
    planned_at: '13:00', actual_at: '2026-07-11T13:20:00Z',
    time_delta_min: 20, planned_cost: 32, actual_cost: 32,
    rating: 3, note: '登阁望古城，城墙是明清遗迹，但¥32门票偏贵，半小时逛完',
    created_at: '2026-07-11T13:20:00Z',
  },
  {
    id: 'ck_d2_03', trip_id: 'mock_trip_changsha',
    poi_type: 'restaurant', poi_name: '坡子街', source_day: 2,
    lat: 28.191, lng: 112.976,
    photos: [],
    planned_at: '17:00', actual_at: '2026-07-11T17:30:00Z',
    time_delta_min: 30, planned_cost: 120, actual_cost: 150,
    rating: 4, note: '火宫殿点了口味虾¥98、剁椒鱼头¥68，辣得过瘾，配一杯豆奶解辣绝配',
    created_at: '2026-07-11T17:30:00Z',
  },
  {
    id: 'ck_d2_04', trip_id: 'mock_trip_changsha',
    poi_type: 'hotel', poi_name: '匠宿酒店(五一广场)', source_day: 2,
    lat: 28.195, lng: 112.979,
    photos: [],
    planned_at: '21:00', actual_at: '2026-07-11T21:00:00Z',
    time_delta_min: 0, planned_cost: 400, actual_cost: 400,
    rating: 4, note: '第二天了，跟前台要了两瓶水，服务不错',
    created_at: '2026-07-11T21:00:00Z',
  },
]

// --- Day 3: 植物园 → 梅溪湖 → 万家丽 ---
export const day3Checkins: CheckinRecord[] = [
  {
    id: 'ck_d3_01', trip_id: 'mock_trip_changsha',
    poi_type: 'attraction', poi_name: '湖南省植物园', source_day: 3,
    lat: 28.118, lng: 113.028,
    photos: [],
    planned_at: '09:00', actual_at: '2026-07-12T09:45:00Z',
    time_delta_min: 45, planned_cost: 20, actual_cost: 20,
    rating: 3, note: '睡过了…到的时候快十点了。植物园很大但夏天太热，走一半就想回室内',
    created_at: '2026-07-12T09:45:00Z',
  },
  {
    id: 'ck_d3_02', trip_id: 'mock_trip_changsha',
    poi_type: 'attraction', poi_name: '梅溪湖文化艺术中心', source_day: 3,
    lat: 28.193, lng: 112.897,
    photos: [],
    planned_at: '14:00', actual_at: '2026-07-12T15:00:00Z',
    time_delta_min: 60, planned_cost: 0, actual_cost: 0,
    rating: 5, note: '扎哈·哈迪德设计的流线型建筑太惊艳了，白色曲面在阳光下闪闪发光，没看演出光拍照就花了一小时',
    created_at: '2026-07-12T15:00:00Z',
  },
  {
    id: 'ck_d3_03', trip_id: 'mock_trip_changsha',
    poi_type: 'shopping', poi_name: '万家丽国际MALL', source_day: 3,
    lat: 28.195, lng: 113.035,
    photos: [],
    planned_at: '17:00', actual_at: '2026-07-12T17:15:00Z',
    time_delta_min: 15, planned_cost: 80, actual_cost: 160,
    rating: 3, note: '顶层28F空中花园看日落视野很好，但商场太大容易迷路，买了件衣服超预算了',
    created_at: '2026-07-12T17:15:00Z',
  },
  {
    id: 'ck_d3_04', trip_id: 'mock_trip_changsha',
    poi_type: 'hotel', poi_name: '匠宿酒店(五一广场)', source_day: 3,
    lat: 28.195, lng: 112.979,
    photos: [],
    planned_at: '21:00', actual_at: '2026-07-12T21:30:00Z',
    time_delta_min: 30, planned_cost: 400, actual_cost: 400,
    rating: 4, note: '今天走太多路了，脚酸',
    created_at: '2026-07-12T21:30:00Z',
  },
]

// --- Day 4: 潮宗街 → 止间书店 → 湘江夜游（当前天，部分已签） ---
export const day4Checkins: CheckinRecord[] = [
  {
    id: 'ck_d4_01', trip_id: 'mock_trip_changsha',
    poi_type: 'attraction', poi_name: '潮宗街历史文化街区', source_day: 4,
    lat: 28.200, lng: 112.973,
    photos: [],
    planned_at: '10:00', actual_at: '2026-07-13T10:20:00Z',
    time_delta_min: 20, planned_cost: 0, actual_cost: 30,
    rating: 4, note: '比太平街清净很多，青砖黛瓦民国风，文创店很好逛，买了两张明信片¥30',
    created_at: '2026-07-13T10:20:00Z',
  },
  {
    id: 'ck_d4_02', trip_id: 'mock_trip_changsha',
    poi_type: 'rest', poi_name: '止间书店', source_day: 4,
    lat: 28.184, lng: 112.946,
    photos: [],
    planned_at: '14:00', actual_at: null,
    time_delta_min: 0, planned_cost: 35, actual_cost: null,
    rating: null, note: null,
    created_at: '2026-07-13T14:00:00Z',
  },
  // 湘江夜游尚未签到（计划18:30）
]

// ======================================================================
// 花费记录
// ======================================================================
export const mockExpenses: ExpenseRecord[] = [
  // Day 1
  { id: 'exp_d1_01', trip_id: 'mock_trip_changsha', checkin_id: null, category: '交通', amount: 68, planned_amount: 50, note: '广州南→长沙南 G6102', spent_at: '2026-07-10T07:30:00Z' },
  { id: 'exp_d1_02', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d1_01', category: '门票', amount: 0, planned_amount: 0, note: '岳麓山免费', spent_at: '2026-07-10T09:15:00Z' },
  { id: 'exp_d1_03', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d1_02', category: '门票', amount: 40, planned_amount: 0, note: '橘子洲小火车', spent_at: '2026-07-10T14:25:00Z' },
  { id: 'exp_d1_04', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d1_03', category: '餐饮', amount: 85, planned_amount: 60, note: '太平老街小吃', spent_at: '2026-07-10T18:30:00Z' },
  { id: 'exp_d1_05', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d1_04', category: '住宿', amount: 400, planned_amount: 400, note: '匠宿酒店 Day1', spent_at: '2026-07-10T21:15:00Z' },
  // Day 2
  { id: 'exp_d2_01', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d2_01', category: '门票', amount: 0, planned_amount: 0, note: '省博免费预约', spent_at: '2026-07-11T09:10:00Z' },
  { id: 'exp_d2_02', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d2_02', category: '门票', amount: 32, planned_amount: 32, note: '天心阁门票', spent_at: '2026-07-11T13:20:00Z' },
  { id: 'exp_d2_03', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d2_03', category: '餐饮', amount: 150, planned_amount: 120, note: '坡子街火宫殿晚餐', spent_at: '2026-07-11T17:30:00Z' },
  { id: 'exp_d2_04', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d2_04', category: '住宿', amount: 400, planned_amount: 400, note: '匠宿酒店 Day2', spent_at: '2026-07-11T21:00:00Z' },
  { id: 'exp_d2_05', trip_id: 'mock_trip_changsha', checkin_id: null, category: '交通', amount: 25, planned_amount: 20, note: '市内地铁+打车', spent_at: '2026-07-11T18:00:00Z' },
  // Day 3
  { id: 'exp_d3_01', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d3_01', category: '门票', amount: 20, planned_amount: 20, note: '植物园门票', spent_at: '2026-07-12T09:45:00Z' },
  { id: 'exp_d3_02', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d3_02', category: '门票', amount: 0, planned_amount: 0, note: '梅溪湖免费参观', spent_at: '2026-07-12T15:00:00Z' },
  { id: 'exp_d3_03', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d3_03', category: '购物', amount: 160, planned_amount: 80, note: '万家丽买衣服', spent_at: '2026-07-12T17:15:00Z' },
  { id: 'exp_d3_04', trip_id: 'mock_trip_changsha', checkin_id: null, category: '餐饮', amount: 45, planned_amount: 50, note: '万家丽美食广场午餐', spent_at: '2026-07-12T12:30:00Z' },
  { id: 'exp_d3_05', trip_id: 'mock_trip_changsha', checkin_id: null, category: '交通', amount: 35, planned_amount: 30, note: '跨区打车', spent_at: '2026-07-12T14:30:00Z' },
  { id: 'exp_d3_06', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d3_04', category: '住宿', amount: 400, planned_amount: 400, note: '匠宿酒店 Day3', spent_at: '2026-07-12T21:30:00Z' },
  // Day 4
  { id: 'exp_d4_01', trip_id: 'mock_trip_changsha', checkin_id: 'ck_d4_01', category: '购物', amount: 30, planned_amount: 0, note: '潮宗街明信片', spent_at: '2026-07-13T10:20:00Z' },
  { id: 'exp_d4_02', trip_id: 'mock_trip_changsha', checkin_id: null, category: '餐饮', amount: 55, planned_amount: 45, note: '潮宗街咖啡馆午餐', spent_at: '2026-07-13T12:00:00Z' },
  // Day 4 后续未签到的尚未产生花费
]

// ======================================================================
// 预算超支场景 — Day5 成都
// ======================================================================
export const mockTripOverBudget: TripState = {
  ...mockTrip,
  id: 'mock_trip_over',
  plan_id: 'test_chengdu',
  current_day: 5,
  budget_total: 3000,
  budget_spent: 2850,
  budget_remain: 150,
}

export const mockProgressOverBudget: TripProgress = {
  ...mockProgress,
  trip_id: 'mock_trip_over',
  current_day: 5,
  progress_pct: 80,
  checked_in: 8,
  total_pois: 10,
  budget_total: 3000,
  budget_spent: 2850,
  budget_remain: 150,
  time_delta_total_min: 120,
  last_location: { lat: 30.670, lng: 104.060 },
}

export const mockAdjustments: AdjustmentRecord[] = [
  {
    id: 'adj_001', trip_id: 'mock_trip_over',
    trigger_type: 'time_drift',
    trigger_detail: { drift_min: 90 },
    reason: '大熊猫基地排队超2小时，严重压缩下午行程，建议武侯祠缩短参观时间',
    status: 'pending',
    created_at: '2026-07-14T11:00:00Z',
  },
  {
    id: 'adj_002', trip_id: 'mock_trip_over',
    trigger_type: 'budget_alert',
    trigger_detail: { over_budget: 850 },
    reason: '已花费¥2,850/预算¥3,000，仅剩¥150。Day5还有交通和餐饮未支付，建议晚餐简餐控制',
    status: 'pending',
    created_at: '2026-07-14T08:00:00Z',
  },
  {
    id: 'adj_003', trip_id: 'mock_trip_over',
    trigger_type: 'weather',
    trigger_detail: { weather: '高温红色预警', temp: 39 },
    reason: '预计明日39°C高温，建议户外景点改室内（博物馆/美术馆），避免中暑',
    status: 'pending',
    created_at: '2026-07-14T06:00:00Z',
  },
]

// ======================================================================
// 已完成场景 — 北京3日，全部签完
// ======================================================================
export const mockTripCompleted: TripState = {
  id: 'mock_trip_complete',
  plan_id: 'test_beijing',
  user_id: 'mock_user',
  status: 'completed',
  current_day: 3,
  total_pois: 9,
  checked_in: 9,
  started_at: '2026-07-10T08:00:00Z',
  paused_at: null,
  completed_at: '2026-07-12T18:00:00Z',
  last_lat: 39.882, last_lng: 116.407,
  budget_total: 3000,
  budget_spent: 2750,
  budget_remain: 250,
  created_at: '2026-07-10T08:00:00Z',
  updated_at: '2026-07-12T18:00:00Z',
}

export const mockProgressCompleted: TripProgress = {
  trip_id: 'mock_trip_complete',
  status: 'completed',
  current_day: 3,
  progress_pct: 100,
  checked_in: 9,
  total_pois: 9,
  budget_total: 3000,
  budget_spent: 2750,
  budget_remain: 250,
  time_delta_total_min: 80,
  last_location: { lat: 39.882, lng: 116.407 },
}

export const mockCheckinsBeijing: CheckinRecord[] = [
  // Day 1
  { id: 'ck_bj_01', trip_id: 'mock_trip_complete', poi_type: 'attraction', poi_name: '天安门广场', source_day: 1, lat: 39.905, lng: 116.398, photos: [], planned_at: '08:00', actual_at: '2026-07-10T07:50:00Z', time_delta_min: -10, planned_cost: 0, actual_cost: 0, rating: 5, note: '特意早起看升旗，国旗护卫队步伐铿锵，奏国歌时全场肃穆，旁边大爷眼眶红了', created_at: '2026-07-10T07:50:00Z' },
  { id: 'ck_bj_02', trip_id: 'mock_trip_complete', poi_type: 'attraction', poi_name: '故宫博物院', source_day: 1, lat: 39.916, lng: 116.397, photos: [], planned_at: '09:00', actual_at: '2026-07-10T09:30:00Z', time_delta_min: 30, planned_cost: 60, actual_cost: 60, rating: 5, note: '午门进神武门出，走了4小时才逛完中轴+西六宫，珍宝馆的象牙雕和点翠头冠精美绝伦', created_at: '2026-07-10T09:30:00Z' },
  { id: 'ck_bj_03', trip_id: 'mock_trip_complete', poi_type: 'restaurant', poi_name: '全聚德烤鸭', source_day: 1, lat: 39.896, lng: 116.391, photos: [], planned_at: '18:00', actual_at: '2026-07-10T18:20:00Z', time_delta_min: 20, planned_cost: 150, actual_cost: 198, rating: 4, note: '前门店总店吃的，师傅现场片鸭，鸭皮蘸白糖入口即化，三个人吃了¥598', created_at: '2026-07-10T18:20:00Z' },
  // Day 2
  { id: 'ck_bj_04', trip_id: 'mock_trip_complete', poi_type: 'attraction', poi_name: '八达岭长城', source_day: 2, lat: 40.359, lng: 116.017, photos: [], planned_at: '07:00', actual_at: '2026-07-11T08:10:00Z', time_delta_min: 70, planned_cost: 40, actual_cost: 40, rating: 5, note: '德胜门坐877路直达¥12，到的时候已经很多人了。北线爬到北八楼，下来腿抖了两天', created_at: '2026-07-11T08:10:00Z' },
  { id: 'ck_bj_05', trip_id: 'mock_trip_complete', poi_type: 'restaurant', poi_name: '海底捞(西单)', source_day: 2, lat: 39.912, lng: 116.410, photos: [], planned_at: '19:00', actual_at: '2026-07-11T19:30:00Z', time_delta_min: 30, planned_cost: 120, actual_cost: 180, rating: 4, note: '爬完长城犒劳自己，美甲＋擦鞋＋捞面表演一条龙，服务真没话说', created_at: '2026-07-11T19:30:00Z' },
  // Day 3
  { id: 'ck_bj_06', trip_id: 'mock_trip_complete', poi_type: 'attraction', poi_name: '颐和园', source_day: 3, lat: 39.999, lng: 116.275, photos: [], planned_at: '09:00', actual_at: '2026-07-12T09:25:00Z', time_delta_min: 25, planned_cost: 30, actual_cost: 30, rating: 4, note: '东宫门进，长廊→排云殿→佛香阁→石舫→十七孔桥，昆明湖划船¥60/h有点贵', created_at: '2026-07-12T09:25:00Z' },
  { id: 'ck_bj_07', trip_id: 'mock_trip_complete', poi_type: 'attraction', poi_name: '天坛', source_day: 3, lat: 39.882, lng: 116.407, photos: [], planned_at: '14:00', actual_at: '2026-07-12T14:30:00Z', time_delta_min: 30, planned_cost: 15, actual_cost: 15, rating: 3, note: '祈年殿在维修被围挡遮住了…圜丘和皇穹宇还可以，回音壁全是人听不到回音', created_at: '2026-07-12T14:30:00Z' },
  { id: 'ck_bj_08', trip_id: 'mock_trip_complete', poi_type: 'restaurant', poi_name: '东来顺涮肉', source_day: 3, lat: 39.898, lng: 116.403, photos: [], planned_at: '18:00', actual_at: '2026-07-12T18:15:00Z', time_delta_min: 15, planned_cost: 100, actual_cost: 128, rating: 5, note: '铜锅清水涮鲜切羊肉，蘸麻酱韭菜花，再来一瓶北冰洋，这才是北京的冬天…啊不对夏天', created_at: '2026-07-12T18:15:00Z' },
  { id: 'ck_bj_09', trip_id: 'mock_trip_complete', poi_type: 'hotel', poi_name: '北京华尔道夫', source_day: 3, lat: 39.912, lng: 116.415, photos: [], planned_at: '20:00', actual_at: '2026-07-12T20:30:00Z', time_delta_min: 30, planned_cost: 1200, actual_cost: 1200, rating: 5, note: '最后一晚狠心订了华尔道夫，服务体贴到令人感动，房间能看到故宫夜景', created_at: '2026-07-12T20:30:00Z' },
]

// ======================================================================
// 空场景
// ======================================================================
export const mockTripEmpty: TripState = {
  ...mockTrip,
  id: 'mock_trip_empty',
  current_day: 1,
  checked_in: 0,
  budget_spent: 0,
  budget_remain: 5000,
}

export const mockProgressEmpty: TripProgress = {
  ...mockProgress,
  trip_id: 'mock_trip_empty',
  current_day: 1,
  progress_pct: 0,
  checked_in: 0,
  time_delta_total_min: 0,
}

// ======================================================================
// 场景选择器
// ======================================================================
export type MockScenario = 'normal' | 'over-budget' | 'completed' | 'empty'

export function getMockData(scenario: MockScenario) {
  switch (scenario) {
    case 'normal':
      return {
        trip: mockTrip,
        progress: mockProgress,
        checkins: [...day1Checkins, ...day2Checkins, ...day3Checkins, ...day4Checkins],
        expenses: mockExpenses,
        adjustments: [],
      }
    case 'over-budget':
      return {
        trip: mockTripOverBudget,
        progress: mockProgressOverBudget,
        checkins: mockCheckinsBeijing.slice(0, 5), // 模拟成都行程的部分签到
        expenses: mockExpenses.slice(0, 6),
        adjustments: mockAdjustments,
      }
    case 'completed':
      return {
        trip: mockTripCompleted,
        progress: mockProgressCompleted,
        checkins: mockCheckinsBeijing,
        expenses: mockExpenses,
        adjustments: [],
      }
    case 'empty':
      return {
        trip: mockTripEmpty,
        progress: mockProgressEmpty,
        checkins: [],
        expenses: [],
        adjustments: [],
      }
  }
}
