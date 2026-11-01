/**
 * 游记 Mock 数据 — 用于测试前端渲染效果
 *
 * 包含：6 篇风格游记 + 配套社交素材
 * 目的地：京都｜厦门｜大理｜成都｜新疆｜上海
 */

import { useTravelogueStore } from '@/store/travelogueStore'
import type { TravelogueData, SocialMaterial } from '@/api/travelogue'

// ===== 各目的地专属图片 =====
// 每篇游记使用完全不同的图片集，互不重复

const IMG = {
  kyoto: {
    cover: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&q=80',
    photos: [
      'https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=400&q=80',
      'https://images.unsplash.com/photo-1528127269322-539801943592?w=400&q=80',
      'https://images.unsplash.com/photo-1478436127897-769e1b3f0f36?w=400&q=80',
      'https://images.unsplash.com/photo-1528360983277-13d401cdc186?w=400&q=80',
    ],
  },
  xiamen: {
    cover: 'https://images.unsplash.com/photo-1585779034824-7e4f2e7c1f0a?w=800&q=80',
    photos: [
      'https://images.unsplash.com/photo-1515622479250-b1fb0e0e4b8c?w=400&q=80',
      'https://images.unsplash.com/photo-1534008897995-27a23e859048?w=400&q=80',
      'https://images.unsplash.com/photo-1559304822-d7b2e4ba7f0a?w=400&q=80',
      'https://images.unsplash.com/photo-1563245372-f21724e3856d?w=400&q=80',
    ],
  },
  dali: {
    cover: 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800&q=80',
    photos: [
      'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=400&q=80',
      'https://images.unsplash.com/photo-1504198453319-5ce911bafcde?w=400&q=80',
      'https://images.unsplash.com/photo-1582653291997-079a1c04e5b7?w=400&q=80',
      'https://images.unsplash.com/photo-1599661046289-e31897846e41?w=400&q=80',
    ],
  },
  chengdu: {
    cover: 'https://images.unsplash.com/photo-1596997000109-5cd8910c90a7?w=800&q=80',
    photos: [
      'https://images.unsplash.com/photo-1563245372-f21724e3856d?w=400&q=80',
      'https://images.unsplash.com/photo-1552566626-52f8b828add9?w=400&q=80',
      'https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=400&q=80',
      'https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=400&q=80',
    ],
  },
  xinjiang: {
    cover: 'https://images.unsplash.com/photo-1506815444479-bfdb1e96c566?w=800&q=80',
    photos: [
      'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&q=80',
      'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400&q=80',
      'https://images.unsplash.com/photo-1470071459604-7b8ec44ffd6b?w=400&q=80',
      'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400&q=80',
    ],
  },
  shanghai: {
    cover: 'https://images.unsplash.com/photo-1538970270646-1a794a0f5d4a?w=800&q=80',
    photos: [
      'https://images.unsplash.com/photo-1534351590666-13e3e96b5017?w=400&q=80',
      'https://images.unsplash.com/photo-1523730206311-1c2a13f4a9c2?w=400&q=80',
      'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=400&q=80',
      'https://images.unsplash.com/photo-1583258292688-d0213dc5a3cb?w=400&q=80',
    ],
  },
}

// ===== 游记数据 =====

export const MOCK_TRAVELOGUES: TravelogueData[] = [
  // ========== 1. 京都 · 日记风 ==========
  {
    id: 'mock-travelogue-001',
    trip_id: 'mock-trip-001',
    user_id: 'mock-user-001',
    title: '京都五日：在古都的秋天里慢慢走',
    status: 'published',
    total_days: 5,
    total_pois: 12,
    total_cost: 8500,
    total_photos: 8,
    cover_url: IMG.kyoto.cover,
    photos: IMG.kyoto.photos,
    content: `# 京都五日：在古都的秋天里慢慢走

> 京都 | 5天 | 总花费 ¥8500

## Day 1：初见·祇园的黄昏

从关西机场坐 Haruka 到京都站已经是下午三点。出了站，看到京都塔在蓝天里发着光，心里突然踏实了。

酒店安顿好之后直奔**祇园**。花见小路两旁的老木屋在黄昏里泛着温润的光，偶尔有穿着和服的游客踩着木屐嗒嗒嗒走过。日落时分游客散了大半，灯笼亮起来的时候才真正有了京都的味道。

## Day 2：伏见稻荷·千本鸟居的红色隧道

起了个大早去**伏见稻荷大社**。七点半到的时候人很少，千本鸟居的光影刚刚好。走到四ツ辻（半山腰观景台）用了大概四十分钟，俯瞰京都市区，秋天早晨的空气清透得不像话。

> 越往上走人越少，建议至少走到半山腰。全程走完要 2-3 小时，量力而行。

## Day 3：岚山·竹林与抹茶

岚山的**竹林小径**比想象中短，但确实很美。阳光从竹叶缝隙漏下来的时候，站在那里什么都不做就觉得很好。

下午在 **% Arabica** 买了杯拿铁，拿着咖啡在**渡月桥**上走。桂川的水很清，远处山上红叶正盛。

| 景点 | 门票 | 推荐时间 |
|------|------|---------|
| 天龙寺 | 800 日元 | 1-2h |
| 竹林小径 | 免费 | 30min |
| 渡月桥 | 免费 | 30min |

## Day 4：清水寺·三年坂

清水寺在修葺，但舞台还是开放的。站在舞台上眺望京都市区，终于理解了为什么那么多人喜欢这座城市——它有一种把时间放慢的魔力。

从清水寺下来走了**三年坂**和**二年坂**，一路都是可爱的小店。买了一个信乐烧的狸猫摆件，三千日元。

## Day 5：再见·西芳寺的青苔

最后一天去了最难预约的**西芳寺（苔寺）**。提前两个月写了明信片预约，终于得见。庭院里有一百二十多种苔藓，绿色的地毯一样铺满整个院子。

---

*京都之旅 · 日记风格 · AI辅助生成*`,
    created_at: '2026-07-10T08:00:00Z',
    updated_at: '2026-07-12T10:00:00Z',
  },

  // ========== 2. 厦门 · 小红书风 ==========
  {
    id: 'mock-travelogue-002',
    trip_id: 'mock-trip-002',
    user_id: 'mock-user-001',
    title: '厦门三天两夜｜吃吃喝喝的快乐周末✨',
    status: 'published',
    total_days: 3,
    total_pois: 9,
    total_cost: 3200,
    total_photos: 6,
    cover_url: IMG.xiamen.cover,
    photos: IMG.xiamen.photos,
    content: `# 厦门三天两夜｜吃吃喝喝的快乐周末✨

> 厦门 | 3天 | 总花费 ¥3200

谁懂啊！！厦门真的太好吃了😭 三天胖了三斤但完全值得！！

---

## Day 1 🏝️ 鼓浪屿暴走

上岛第一件事：**叶氏麻糍**！！1.5 一个，花生碎超香，排队也值得🥹

然后就是各种小路乱窜～鼓浪屿不用做攻略，随便走都很美。日光岩顶上的风景绝了，整个鹭江尽收眼底🌊

晚饭在**林四喜**吃的姜母鸭，鸭肉嫩到脱骨，姜片炸得酥酥的直接吃！人均 80 吃到撑👏

## Day 2 🌸 山海步道 & 沙坡尾

山海健康步道一定要走！！从林海线到天泉步道广场那段，**大海和城市同框**太震撼了🏙️🌊

下午逛沙坡尾，超多可爱的小店：
- **酒场 SAKE NOMI BAR** 门口超日系，拍照📸
- **人间百货** 古着店，淘了件花衬衫 120 元
- **涠霖甜品** 的糖水，加阿达籽和莲藕，清爽！

## Day 3 ☕ 咖啡时间

临走前去**华新路**一带逛了逛。老别墅改的咖啡店太有感觉了！

- **Bamn Coffee** — 特调「厦门」加了话梅和气泡水，很特别✨
- **向日葵之家** — 院子里有棵大榕树，坐了一整个上午

---

> 💡 住宿选在思明区，去哪都方便。厦门公交 1 元，打车也不贵。

#厦门旅行 #鼓浪屿 #厦门美食 #周末去哪儿`,
    created_at: '2026-07-08T06:00:00Z',
    updated_at: '2026-07-09T14:00:00Z',
  },

  // ========== 3. 大理 · 攻略风 ==========
  {
    id: 'mock-travelogue-003',
    trip_id: 'mock-trip-003',
    user_id: 'mock-user-001',
    title: '大理环洱海全攻略：租车/路线/拍照点一网打尽',
    status: 'draft',
    total_days: 4,
    total_pois: 15,
    total_cost: 4200,
    total_photos: 7,
    cover_url: IMG.dali.cover,
    photos: IMG.dali.photos,
    content: `# 大理环洱海全攻略：租车/路线/拍照点一网打尽

> 大理 | 4天 | 总花费 ¥4200

---

## 行前准备

### 最佳季节
- **3-5月**：花开季节，风景最好
- **9-11月**：秋高气爽，人少
- 避开 7-8 月雨季和春节黄金周

### 交通方式
- **飞大理**：全国主要城市有直飞
- **飞昆明 + 高铁**：昆明到大理 2 小时，145 元
- **环洱海租车**：电动车 80-120 元/天，汽车 200-400 元/天

## Day 1：大理古城 & 崇圣寺

### 上午：大理古城
免费。建议走人民路和复兴路。

### 下午：崇圣寺三塔
门票 75 元。三塔倒影公园是经典拍照机位。

| 景点 | 门票 | 建议时长 |
|------|------|---------|
| 大理古城 | 免费 | 半天 |
| 崇圣寺三塔 | 75 元 | 2-3h |

## Day 2：环洱海西线

**路线：古城 → 才村 → 喜洲 → 双廊**

1. **才村** — 洱海生态廊道骑行 1.5h
2. **喜洲古镇** — 白族建筑、喜洲粑粑 2h
3. **双廊古镇** — 海景咖啡馆、日落 2h+

## Day 3：环洱海东线 & 理想邦

**理想邦（大理圣托里尼）** 蓝白建筑很出片，建议穿纯色衣服。

## Day 4：苍山 & 省钱技巧

### 省钱技巧 💰
1. 住宿选古城周边民宿，150-300 元/晚
2. 不要在景区门口吃饭，走 200 米便宜一半
3. 环海租电动车最划算，一天 80 元跑 200 公里

---

*大理攻略 · 攻略风格 · AI辅助生成*`,
    created_at: '2026-07-05T09:00:00Z',
    updated_at: '2026-07-06T11:00:00Z',
  },

  // ========== 4. 成都 · 美食风 ==========
  {
    id: 'mock-travelogue-004',
    trip_id: 'mock-trip-004',
    user_id: 'mock-user-001',
    title: '成都逛吃记｜除了火锅，成都还有这些宝藏🔥',
    status: 'published',
    total_days: 4,
    total_pois: 14,
    total_cost: 2800,
    total_photos: 9,
    cover_url: IMG.chengdu.cover,
    photos: IMG.chengdu.photos,
    content: `# 成都逛吃记｜除了火锅，成都还有这些宝藏🔥

> 成都 | 4天 | 总花费 ¥2800

成都，一座来了就不想走的城市。这次终于安排上了，以下是真实体验👇

---

## Day 1 🔥 火锅开道

到成都第一件事必须是**火锅**！去了本地朋友推荐的**天星正源**，排队两小时但值得🙏

锅底一端上来那个牛油香味就绝了！推荐菜：**毛肚、鹅肠、耗儿鱼**。

> 不能吃辣的点微辣就好，我高估了自己🥵

## Day 2 🐼 熊猫基地 & 文殊院

**大熊猫繁育基地**一定要早上去！七点半开门，熊猫们都在吃竹子，超治愈。月亮产房的小熊猫跟糯米团子一样，太可爱了😭

下午去了**文殊院**，门口的甜水面和凉粉都很好吃，老字号了。

## Day 3 🏛️ 三星堆 & 玉林路

**三星堆博物馆**真的震撼！青铜神树、青铜大立人，那种神秘感让人起鸡皮疙瘩。新馆修得也很有设计感。

晚上去**玉林路**的小酒馆坐坐，虽然赵雷唱火了之后人很多，但旁边的串串店更好吃😋

## Day 4 🍜 早市 & 掏耳朵

最后一天去**彭镇老茶馆**感受了一下成都的慢生活。一碗盖碗茶 10 块钱，坐了一上午。

**人民公园**的鹤鸣茶社也不错，顺便体验了掏耳朵（30 元，酥麻酥麻的很上头）。

### 美食红黑榜 ✅❌

| 美食 | 推荐 | 价格 |
|------|------|------|
| 甜水面 | ✅ 必吃 | 12 元 |
| 蛋烘糕 | ✅ 加奶油肉松 | 5 元 |
| 兔头 | ✅ 麻辣味 | 15 元 |
| 三大炮 | ❌ 拍照好看但一般 | 10 元 |

---

*成都之旅 · 美食风格 · AI辅助生成*`,
    created_at: '2026-07-14T10:00:00Z',
    updated_at: '2026-07-15T16:00:00Z',
  },

  // ========== 5. 新疆伊犁 · 攻略向 ==========
  {
    id: 'mock-travelogue-005',
    trip_id: 'mock-trip-005',
    user_id: 'mock-user-001',
    title: '伊犁七日｜夏天的新疆，是封了神的夏天🌲',
    status: 'published',
    total_days: 7,
    total_pois: 18,
    total_cost: 6800,
    total_photos: 12,
    cover_url: IMG.xinjiang.cover,
    photos: IMG.xinjiang.photos,
    content: `# 伊犁七日｜夏天的新疆，是封了神的夏天🌲

> 新疆伊犁 | 7天 | 总花费 ¥6800

如果说国内有一个地方能媲美瑞士，那一定是夏天的新疆伊犁。雪山、草原、花海、森林——所有的形容词在这里都不够用。

---

## Day 1-2：赛里木湖

大西洋的最后一滴眼泪，名不虚传。

环湖大概 90 公里，建议租车自驾。**南岸**比北岸美得多，人少，能看到雪山倒影。**S 弯公路**那段拍照绝了。

> 🎫 门票 145 元/人（自驾另算）
> 🏠 建议住景区外的蒙古包，200 元/晚，包含早晚餐

![赛里木湖](https://images.unsplash.com/photo-1504198453319-5ce911bafcde?w=600&q=80)

## Day 3-4：夏塔古道

夏塔是这次行程的**高光时刻**！从景区门口坐区间车到温泉酒店（1h），然后徒步到鲜花台（2h），一路都在哇哇哇😭

天气好的时候可以看到**木扎尔特冰川**，雪白的山峰就在眼前，震撼到失语。

区间车最后一班是晚上 8 点，注意时间。

## Day 5：琼库什台

从特克斯开车 3 小时到琼库什台。山路十八弯，但到了之后一切都值了。

后山的秋千、小木屋、远处的雪山——像走进了一幅画。骑马一小时 80 元，牧民会带着你走，很安全。

## Day 6-7：那拉提 & 返程

那拉提的**空中草原**名不虚传，但商业化比较重。网红桥排队很久，其实旁边的溪流随便拍都好看。

### 实用信息 📝

| 项目 | 费用 |
|------|------|
| 租车（SUV 一周） | 2500 元 |
| 油费 + 过路费 | 1500 元 |
| 住宿（6 晚） | 1500 元 |
| 餐饮 | 800 元 |
| 门票 | 500 元 |

### 注意事项 ⚠️
- 新疆和内地有 2 小时时差，晚上 10 点才日落
- 身份证随身带，到处要安检
- 防晒霜 SPF50+，紫外线真的很强
- 带厚外套，草原晚上只有 10 度

---

*新疆之旅 · 攻略风格 · AI辅助生成*`,
    created_at: '2026-07-13T07:00:00Z',
    updated_at: '2026-07-16T12:00:00Z',
  },

  // ========== 6. 上海 · 城市日记 ==========
  {
    id: 'mock-travelogue-006',
    trip_id: 'mock-trip-006',
    user_id: 'mock-user-001',
    title: '上海周末｜在梧桐区走了一天，啥也没干但很充实',
    status: 'draft',
    total_days: 2,
    total_pois: 7,
    total_cost: 1500,
    total_photos: 5,
    cover_url: IMG.shanghai.cover,
    photos: IMG.shanghai.photos,
    content: `# 上海周末｜在梧桐区走了一天，啥也没干但很充实

> 上海 | 2天 | 总花费 ¥1500

朋友问我周末去哪儿了，我说在上海走了走。问走了哪些地方，想了半天说不出来。但就是感觉很充实。

---

## 周六：武康路 → 安福路 → 五原路

没有目的地在**梧桐区**乱走。

武康大楼前人山人海，但拐进旁边的小路就安静下来了。**安福路**上的多抓鱼循环商店挺好逛的，淘了本绝版的摄影集，45 元。

中午在**RAC Bar** 吃了个可丽饼，排队半小时，但确实好吃。火腿芝士可丽饼配一杯 cider，阳光透过梧桐叶洒在桌上的时候，觉得这才是周末该有的样子。

下午逛到**五原路**，路过一个叫「老房子」的杂货铺，卖各种 vintage 小物。买了一个老上海搪瓷杯，30 元。

> 上海的好，在于你不需要去什么景点，走在路上本身就是一种体验。

## 周日：浦东美术馆 & 滨江

**MAP 浦东美术馆**现在有绝美的展！顶楼的露台看外滩绝了，日落时分在那里发呆了一个小时。

沿着**滨江步道**从陆家嘴走到东昌路渡口，花 2 块钱坐轮渡到外滩。江风吹着，看着两岸的天际线，突然有点喜欢这座城市了。

### 花销
- 可丽饼 + 咖啡：120 元
- 二手书：45 元
- 搪瓷杯：30 元
- 美术馆门票：100 元
- 轮渡：2 元 💰
- 地铁：10 元

> 两天花了 1500，但最快乐的是那 2 块钱的轮渡。

---

*上海周末 · 日记风格 · AI辅助生成*`,
    created_at: '2026-07-15T14:00:00Z',
    updated_at: '2026-07-16T09:00:00Z',
  },
]

// ===== 社交素材数据 =====

export const MOCK_MATERIALS: SocialMaterial[] = [
  // ---- 京都 ----
  {
    id: 'mock-mat-001',
    trip_id: 'mock-trip-001',
    user_id: 'mock-user-001',
    type: 'moment_9grid',
    title: '📍京都 Day1 打卡！祇园的黄昏真的太美了✨',
    content: '📍京都 Day1 打卡！祇园的黄昏真的太美了✨',
    hashtags: ['#京都旅行', '#祇园', '#旅行日记'],
    location_tag: '祇园',
    images: [
      { url: IMG.kyoto.photos[0], caption: '花见小路黄昏', order: 1, is_cover: false },
      { url: IMG.kyoto.photos[1], caption: '千本鸟居', order: 2, is_cover: false },
      { url: IMG.kyoto.photos[2], caption: '岚山竹林', order: 3, is_cover: false },
      { url: IMG.kyoto.photos[3], caption: '清水寺', order: 4, is_cover: false },
      { url: IMG.kyoto.photos[0], caption: '和果子', order: 5, is_cover: true },
      { url: IMG.kyoto.photos[1], caption: '渡月桥', order: 6, is_cover: false },
      { url: IMG.kyoto.photos[2], caption: '红叶', order: 7, is_cover: false },
      { url: IMG.kyoto.photos[3], caption: '抹茶', order: 8, is_cover: false },
      { url: IMG.kyoto.photos[0], caption: '街景', order: 9, is_cover: false },
    ],
    layout: 'grid_9',
    overlay_data: null,
    source_day: 1,
    source_poi: '祇园',
    is_generated: true,
    is_favorite: true,
    used_in_travelogue: false,
    created_at: '2026-07-10T10:00:00Z',
  },
  {
    id: 'mock-mat-002',
    trip_id: 'mock-trip-001',
    user_id: 'mock-user-001',
    type: 'day_summary',
    title: 'Day 1 打卡完成 ✓',
    content: '今日4个打卡点，花费¥12000',
    hashtags: ['#京都'],
    location_tag: '京都',
    images: [{ url: IMG.kyoto.photos[0], caption: '祇园黄昏', order: 1, is_cover: true }],
    layout: 'single_v',
    overlay_data: { day: '1/5', pois: 4, poi_list: '祇园 → 花见小路 → 鸭川 → 先斗町', cost: '¥12000', weather: '晴' },
    source_day: 1,
    source_poi: '祇园',
    is_generated: true,
    is_favorite: false,
    used_in_travelogue: false,
    created_at: '2026-07-10T10:00:00Z',
  },

  // ---- 厦门 ----
  {
    id: 'mock-mat-003',
    trip_id: 'mock-trip-002',
    user_id: 'mock-user-001',
    type: 'moment_9grid',
    title: '厦门也太好吃了吧😭 三天胖三斤不完全记录👇',
    content: '厦门也太好吃了吧😭 三天胖三斤不完全记录👇',
    hashtags: ['#厦门美食', '#鼓浪屿', '#小吃'],
    location_tag: '厦门中山路',
    images: [
      { url: IMG.xiamen.photos[0], caption: '沙茶面', order: 1, is_cover: false },
      { url: IMG.xiamen.photos[1], caption: '海蛎煎', order: 2, is_cover: false },
      { url: IMG.xiamen.photos[2], caption: '姜母鸭', order: 3, is_cover: false },
      { url: IMG.xiamen.photos[3], caption: '土笋冻', order: 4, is_cover: false },
      { url: IMG.xiamen.photos[0], caption: '烧肉粽', order: 5, is_cover: true },
      { url: IMG.xiamen.photos[1], caption: '花生汤', order: 6, is_cover: false },
      { url: IMG.xiamen.photos[2], caption: '沙坡尾', order: 7, is_cover: false },
      { url: IMG.xiamen.photos[3], caption: '鼓浪屿', order: 8, is_cover: false },
      { url: IMG.xiamen.photos[0], caption: '中山路', order: 9, is_cover: false },
    ],
    layout: 'grid_9',
    overlay_data: null,
    source_day: 1,
    source_poi: '中山路',
    is_generated: true,
    is_favorite: false,
    used_in_travelogue: false,
    created_at: '2026-07-08T08:00:00Z',
  },
  {
    id: 'mock-mat-004',
    trip_id: 'mock-trip-002',
    user_id: 'mock-user-001',
    type: 'trip_highlight',
    title: '厦门之旅，每一口都是惊喜。从沙茶面到花生汤，从鼓浪屿到沙坡尾，这座城市的烟火气让人着迷。',
    content: '',
    hashtags: ['#厦门旅行', '#海边的城市'],
    location_tag: '厦门',
    images: [
      { url: IMG.xiamen.photos[0], caption: '沙坡尾', order: 1, is_cover: true },
      { url: IMG.xiamen.photos[1], caption: '鼓浪屿', order: 2, is_cover: false },
      { url: IMG.xiamen.photos[2], caption: '中山路夜景', order: 3, is_cover: false },
      { url: IMG.xiamen.photos[3], caption: '海边日落', order: 4, is_cover: false },
    ],
    layout: 'card',
    overlay_data: null,
    source_day: null,
    source_poi: null,
    is_generated: true,
    is_favorite: true,
    used_in_travelogue: false,
    created_at: '2026-07-08T08:00:00Z',
  },

  // ---- 大理 ----
  {
    id: 'mock-mat-005',
    trip_id: 'mock-trip-003',
    user_id: 'mock-user-001',
    type: 'budget_card',
    title: '💰 旅行花费总结',
    content: '总预算 ¥5000 → 实际 ¥4200',
    hashtags: [],
    location_tag: null,
    images: [],
    layout: 'card',
    overlay_data: { total: 5000, actual_total: 4200, accommodation: 1500, food: 800, transport: 1200, tickets: 700 },
    source_day: null,
    source_poi: null,
    is_generated: true,
    is_favorite: false,
    used_in_travelogue: false,
    created_at: '2026-07-06T10:00:00Z',
  },
  {
    id: 'mock-mat-006',
    trip_id: 'mock-trip-003',
    user_id: 'mock-user-001',
    type: 'day_summary',
    title: 'Day 2 环海骑行完成 ✓',
    content: '今日5个打卡点，环洱海西线60km！',
    hashtags: ['#大理', '#洱海'],
    location_tag: '喜洲古镇',
    images: [{ url: IMG.dali.photos[0], caption: '洱海骑行', order: 1, is_cover: true }],
    layout: 'single_v',
    overlay_data: { day: '2/4', pois: 5, poi_list: '才村 → 喜洲 → 双廊 → 小普陀', cost: '¥350', weather: '晴' },
    source_day: 2,
    source_poi: '喜洲古镇',
    is_generated: true,
    is_favorite: false,
    used_in_travelogue: false,
    created_at: '2026-07-06T10:00:00Z',
  },

  // ---- 成都 ----
  {
    id: 'mock-mat-007',
    trip_id: 'mock-trip-004',
    user_id: 'mock-user-001',
    type: 'moment_9grid',
    title: '成都火锅yyds🔥 这趟值了！',
    content: '成都火锅yyds🔥 这趟值了！',
    hashtags: ['#成都', '#火锅', '#小吃'],
    location_tag: '成都建设路',
    images: [
      { url: IMG.chengdu.photos[0], caption: '火锅', order: 1, is_cover: false },
      { url: IMG.chengdu.photos[1], caption: '熊猫', order: 2, is_cover: false },
      { url: IMG.chengdu.photos[2], caption: '甜水面', order: 3, is_cover: false },
      { url: IMG.chengdu.photos[3], caption: '串串', order: 4, is_cover: false },
      { url: IMG.chengdu.photos[0], caption: '蛋烘糕', order: 5, is_cover: true },
      { url: IMG.chengdu.photos[1], caption: '盖碗茶', order: 6, is_cover: false },
      { url: IMG.chengdu.photos[2], caption: '锦里', order: 7, is_cover: false },
      { url: IMG.chengdu.photos[3], caption: '宽窄巷子', order: 8, is_cover: false },
      { url: IMG.chengdu.photos[0], caption: '九眼桥', order: 9, is_cover: false },
    ],
    layout: 'grid_9',
    overlay_data: null,
    source_day: 1,
    source_poi: '建设路',
    is_generated: true,
    is_favorite: false,
    used_in_travelogue: false,
    created_at: '2026-07-14T12:00:00Z',
  },
  {
    id: 'mock-mat-008',
    trip_id: 'mock-trip-004',
    user_id: 'mock-user-001',
    type: 'day_summary',
    title: 'Day 1 火锅局达成 ✓',
    content: '今日6个打卡点，吃了3顿！',
    hashtags: ['#成都美食'],
    location_tag: '建设路',
    images: [{ url: IMG.chengdu.photos[0], caption: '火锅', order: 1, is_cover: true }],
    layout: 'single_v',
    overlay_data: { day: '1/4', pois: 6, poi_list: '建设路 → 电子科大 → 339电视塔', cost: '¥380', weather: '雨' },
    source_day: 1,
    source_poi: '建设路',
    is_generated: true,
    is_favorite: false,
    used_in_travelogue: false,
    created_at: '2026-07-14T12:00:00Z',
  },

  // ---- 新疆 ----
  {
    id: 'mock-mat-009',
    trip_id: 'mock-trip-005',
    user_id: 'mock-user-001',
    type: 'trip_highlight',
    title: '七月的伊犁，是上帝打翻的调色盘。赛里木湖的蓝、夏塔的绿、昭苏的金黄——每一种颜色都纯粹得不真实。',
    content: '',
    hashtags: ['#新疆', '#伊犁', '#赛里木湖'],
    location_tag: '伊犁',
    images: [
      { url: IMG.xinjiang.photos[0], caption: '赛里木湖', order: 1, is_cover: true },
      { url: IMG.xinjiang.photos[1], caption: '夏塔古道', order: 2, is_cover: false },
      { url: IMG.xinjiang.photos[2], caption: '琼库什台', order: 3, is_cover: false },
      { url: IMG.xinjiang.photos[3], caption: '那拉提', order: 4, is_cover: false },
    ],
    layout: 'card',
    overlay_data: null,
    source_day: null,
    source_poi: null,
    is_generated: true,
    is_favorite: true,
    used_in_travelogue: false,
    created_at: '2026-07-15T08:00:00Z',
  },
  {
    id: 'mock-mat-010',
    trip_id: 'mock-trip-005',
    user_id: 'mock-user-001',
    type: 'day_summary',
    title: 'Day 3 夏塔徒步达成 ✓',
    content: '今日徒步12km，海拔爬升600m，看到了冰川！',
    hashtags: ['#夏塔', '#徒步'],
    location_tag: '夏塔古道',
    images: [{ url: IMG.xinjiang.photos[1], caption: '夏塔冰川', order: 1, is_cover: true }],
    layout: 'single_v',
    overlay_data: { day: '3/7', pois: 3, poi_list: '夏塔温泉 → 鲜花台 → 冰川观景台', cost: '¥120', weather: '晴' },
    source_day: 3,
    source_poi: '夏塔古道',
    is_generated: true,
    is_favorite: false,
    used_in_travelogue: false,
    created_at: '2026-07-15T08:00:00Z',
  },
]

/**
 * 注入 mock 数据到 travelogue store
 * 在浏览器控制台执行：
 *   store.loadMockData()
 */
export function loadMockTravelogues() {
  const store = useTravelogueStore()
  store.travelogues = [...MOCK_TRAVELOGUES]
  store.current = MOCK_TRAVELOGUES[0]
  store.materials = [...MOCK_MATERIALS]
  console.log(`✅ 已注入 ${MOCK_TRAVELOGUES.length} 篇游记 + ${MOCK_MATERIALS.length} 条素材`)
  MOCK_TRAVELOGUES.forEach(t => console.log(`  [${t.status}] ${t.title}`))
}

/**
 * 注入指定 ID 的游记
 */
export function loadMockTravelogue(id: string) {
  const store = useTravelogueStore()
  const t = MOCK_TRAVELOGUES.find(t => t.id === id)
  if (t) {
    store.current = t
    store.materials = MOCK_MATERIALS.filter(m => m.trip_id === t.trip_id)
    console.log(`✅ 已加载游记：${t.title}`)
  }
}
