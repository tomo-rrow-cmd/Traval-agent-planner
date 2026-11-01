"""
插入游记测试数据 — 生成 3 篇风格各异的示例游记
用法：python scripts/seed_travelogues.py
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import async_session_factory
from app.db.models.travelogue import Travelogue
from app.db.models.base import generate_uuid

# ===== 真实外键（从数据库查询） =====
TEST_USER_ID = "f7673a60-a95a-460e-bf5d-46de4773f60f"
TEST_TRIP_ID = "8d9b2e15-4dd0-4171-bce4-1715869e3888"

# ===== 封面图（Unsplash 旅行摄影） =====
COVERS = [
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",
    "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80",
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800&q=80",
]

# ===== 示例照片 =====
PHOTOS = [
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400&q=80",
    "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=400&q=80",
    "https://images.unsplash.com/photo-1528127269322-539801943592?w=400&q=80",
    "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=400&q=80",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=400&q=80",
    "https://images.unsplash.com/photo-1504198453319-5ce911bafcde?w=400&q=80",
    "https://images.unsplash.com/photo-1524396309943-e03f5249f002?w=400&q=80",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&q=80",
]

# ===== 游记数据 =====

TRAVELOGUES = [
    # ---- 1. 日记风 ----
    {
        "title": "京都五日：在古都的秋天里慢慢走",
        "status": "published",
        "total_days": 5,
        "total_pois": 12,
        "total_cost": 8500.0,
        "total_photos": 8,
        "cover_url": COVERS[0],
        "photos": PHOTOS[:8],
        "content": """# 京都五日：在古都的秋天里慢慢走

> 京都 | 5天 | 总花费 ¥8500

## Day 1：初见·祇园的黄昏

从关西机场坐 Haruka 到京都站已经是下午三点。出了站，看到京都塔在蓝天里发着光，心里突然踏实了。

酒店安顿好之后直奔**祇园**。花见小路两旁的老木屋在黄昏里泛着温润的光，偶尔有穿着和服的游客踩着木屐嗒嗒嗒走过。日落时分游客散了大半，灯笼亮起来的时候才真正有了京都的味道。

晚饭在祇园边上一家叫「十二段家」的寿喜烧解决。肉质很好，酱汁微甜，配白饭简直绝了。一个人吃了四千日元，值。

![祇园黄昏](https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=600&q=80)

## Day 2：伏见稻荷·千本�的红色隧道

起了个大早去**伏见稻荷大社**。七点半到的时候人很少，千本�的光影刚刚好。走到四ツ辻（半山腰观景台）用了大概四十分钟，俯瞰京都市区，秋天早晨的空气清透得不像话。

> 攻略 tip：越往上走人越少，建议至少走到半山腰。全程走完要 2-3 小时，量力而行。

下山后去了附近的**东福寺**。红叶季的东福寺是京都赏枫第一名所，通天桥上看下去真的像红色的云海。门票 1000 日元，值回票价。

## Day 3：岚山·竹林与抹茶

岚山的**竹林小径**比想象中短，但确实很美。阳光从竹叶缝隙漏下来的时候，站在那里什么都不做就觉得很好。

天龙寺的庭院特别棒，坐在廊下看枯山水看了半个小时。

下午在**% Arabica** 买了杯拿铁，拿着咖啡在**渡月桥**上走。桂川的水很清，远处山上红叶正盛。

![岚山竹林](https://images.unsplash.com/photo-1528127269322-539801943592?w=600&q=80)

## Day 4：清水寺·三年坂的闲逛

清水寺在修葺，但舞台还是开放的。站在舞台上眺望京都市区，终于理解了为什么那么多人喜欢这座城市——它有一种把时间放慢的魔力。

从清水寺下来走了**三年坂**和**二年坂**，一路都是可爱的小店。买了一个信乐烧的狸猫摆件，三千日元。

下午茶在**茶寮都路里**吃了抹茶芭菲，浓郁但不甜腻，强烈推荐。

## Day 5：再见·西芳寺的青苔

最后一天去了最难预约的**西芳寺（苔寺）**。提前两个月写了明信片预约，终于得见。庭院里有一百二十多种苔藓，绿色的地毯一样铺满整个院子。抄经的时候心特别静。

下午去京都站买了各种伴手礼，坐上傍晚的 Haruka 去机场。

---

*京都之旅 · 日记风格 · AI辅助生成*
""",
    },
    # ---- 2. 小红书风 ----
    {
        "title": "厦门三天两夜｜吃吃喝喝的快乐周末✨",
        "status": "published",
        "total_days": 3,
        "total_pois": 9,
        "total_cost": 3200.0,
        "total_photos": 6,
        "cover_url": COVERS[1],
        "photos": PHOTOS[2:8],
        "content": """# 厦门三天两夜｜吃吃喝喝的快乐周末✨

> 厦门 | 3天 | 总花费 ¥3200

谁懂啊！！厦门真的太好吃了😭 三天胖了三斤但完全值得！！

---

## Day 1 🏝️ 鼓浪屿暴走

上岛第一件事：**叶氏麻糍**！！1.5 一个，花生碎超香，排队也值得🥹

然后就是各种小路乱窜～鼓浪屿不用做攻略，随便走都很美。日光岩顶上的风景绝了，整个鹭江尽收眼底🌊

> 📍 鼓浪屿日光岩 | 门票 50 元 | 建议早上8点前人少

晚饭在**林四喜**吃的姜母鸭，鸭肉嫩到脱骨，姜片炸得酥酥的直接吃！人均 80 吃到撑👏

## Day 2 🌸 山海步道 & 沙坡尾

山海健康步道一定要走！！从林海线到天泉步道广场那段，**大海和城市同框**太震撼了🏙️🌊

下午逛沙坡尾，超多可爱的小店！
- **酒场 SAKE NOMI BAR** 门口超日系，拍照📸
- **人间百货** 古着店，淘了件花衬衫 120 元
- **涠霖甜品** 的糖水，加阿达籽和莲藕，清爽！

晚上去**八市**吃海鲜。推荐阿杰五香卷，现炸的超脆，4 元一条要什么自行车🚲

![沙坡尾](https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=600&q=80)

## Day 3 ☕ 咖啡时间

临走前去**华新路**一带逛了逛。老别墅改的咖啡店太有感觉了！

- **Bamn Coffee** — 特调「厦门」加了话梅和气泡水，很特别✨
- **向日葵之家** — 院子里有棵大榕树，坐了一整个上午

下午三点的飞机，带着两盒**阿吉仔**馅饼回家啦🥮

---

> 💡 小贴士
> - 住宿选在思明区，去哪都方便
> - 厦门公交 1 元，但打车也不贵
> - 防晒！防晒！防晒！

#厦门旅行 #鼓浪屿 #厦门美食 #周末去哪儿 #旅行日记
""",
    },
    # ---- 3. 攻略风 + 草稿 ----
    {
        "title": "大理环洱海全攻略：租车/路线/拍照点一网打尽",
        "status": "draft",
        "total_days": 4,
        "total_pois": 15,
        "total_cost": 4200.0,
        "total_photos": 7,
        "cover_url": COVERS[2],
        "photos": PHOTOS[1:7],
        "content": """# 大理环洱海全攻略：租车/路线/拍照点一网打尽

> 大理 | 4天 | 总花费 ¥4200

---

## 行前准备

### 最佳季节
- **3-5月**：花开季节，风景最好
- **9-11月**：秋高气爽，人少
- 避开 7-8 月雨季和春节黄金周

### 交通方式
- **飞大理**：全国主要城市有直飞，机场到古城 30 分钟
- **飞昆明 + 高铁**：昆明到大理 2 小时，二等座 145 元
- **环洱海租车**：电动车 80-120 元/天，汽车 200-400 元/天

---

## Day 1：大理古城 & 崇圣寺

### 上午：大理古城
免费。建议走人民路和复兴路，避开商业化严重的洋人街。

> 推荐：床单厂艺术区有独立书店和手作工作室，很好逛。

### 下午：崇圣寺三塔
门票 75 元。三塔倒影公园是经典拍照机位，建议下午去，光线正好。

### 晚上：古城夜景
**云游火塘酒吧**有驻唱，点一壶青梅酒听歌很舒服。

---

## Day 2：环洱海西线

### 路线：古城 → 才村 → 喜洲 → 双廊

| 站点 | 特色 | 停留时间 | 费用 |
|------|------|---------|------|
| 才村 | 洱海生态廊道骑行 | 1.5h | 免费 |
| 喜洲古镇 | 白族建筑、喜洲粑粑 | 2h | 免费 |
| 双廊古镇 | 海景咖啡馆、日落 | 2h+ | 免费 |

### 必吃
- **喜洲粑粑**：推荐「酥香园」，咸口的加肉末 15 元
- **双廊酸辣鱼**：路边随便一家都好吃，人均 50

![洱海](https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=600&q=80)

---

## Day 3：环洱海东线 & 理想邦

### 路线：双廊 → 理想邦 → 圣托里尼 → 古城

**理想邦**（大理圣托里尼）：
- 门票：免费（部分区域收费 50 元）
- 拍照：蓝白建筑很出片，建议穿纯色衣服
- 避坑：周末人多，建议工作日去

**小普陀**：
- 路边就可以看到，不用特地上岛
- 冬天有海鸥，可以带面包喂

### 拍照机位总结 📸
1. **鹿卧山** — 俯瞰洱海的悬崖机位
2. **S 湾** — 生态廊道上的 S 形弯道，配白桌椅
3. **双廊海街** — 日落时分金色水面

---

## Day 4：苍山 & 返程

### 苍山
- 索道：洗马潭索道（最长）往返 280 元
- 温度：山顶比山下低 10°C，带外套
- 时间：全程 4-5 小时，建议一早出发

### 省钱技巧 💰
1. 住宿选古城周边民宿，150-300 元/晚就能住很好
2. 吃饭不要在景区门口，走 200 米巷子里便宜一半
3. 环海租电动车最划算，一天 80 元能跑 200 公里
4. 大理大学附近的夜市比古城便宜很多

---

*大理攻略 · 攻略风格 · AI辅助生成*
""",
    },
]


async def seed():
    async with async_session_factory() as db:
        # 清空现有的测试游记
        from sqlalchemy import delete
        await db.execute(delete(Travelogue))
        print("已清空旧测试数据")

        for data in TRAVELOGUES:
            t = Travelogue(
                id=generate_uuid(),
                trip_id=TEST_TRIP_ID,
                user_id=TEST_USER_ID,
                title=data["title"],
                content=data["content"],
                cover_url=data["cover_url"],
                photos=data["photos"],
                total_days=data["total_days"],
                total_pois=data["total_pois"],
                total_cost=data["total_cost"],
                total_photos=data["total_photos"],
                status=data["status"],
            )
            db.add(t)

        await db.commit()
        print(f"已插入 {len(TRAVELOGUES)} 篇测试游记")
        print()

        # 列出已插入的数据
        from sqlalchemy import select
        result = await db.execute(select(Travelogue))
        for t in result.scalars().all():
            print(f"  [{t.status}] {t.title} ({t.total_days}天/{t.total_pois}个景点)")

    print("\n测试数据准备完成！")


if __name__ == "__main__":
    asyncio.run(seed())
