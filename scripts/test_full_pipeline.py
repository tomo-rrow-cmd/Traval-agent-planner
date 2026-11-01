"""完整对话测试：偏好询问 → 确认 → pipeline"""

import httpx, json, sys, time

BASE_URL = "http://localhost:8000/api/v1"

def req(method, path, **kw):
    r = httpx.request(method, f"{BASE_URL}{path}", timeout=30, **kw)
    p = r.json()
    if r.status_code >= 400 or p.get("code", 0) != 0:
        print(f"Error {method} {path}: {p}")
        sys.exit(1)
    return p.get("data")

# 1. Login + create session
token = req("POST", "/auth/sessions",
    json={"method": "phone", "phone": "13700001111", "code": "123456"})["access_token"]
sid = req("POST", "/chat/sessions", headers={"Authorization": f"Bearer {token}"}, json={})["id"]
print(f"Session: {sid}")

def stream_msg(content):
    """Send message and stream SSE response"""
    print(f"\n>>> {content}")
    with httpx.stream("POST",
        f"{BASE_URL}/chat/sessions/{sid}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": content},
        timeout=120,
    ) as r:
        if r.status_code >= 400:
            print(f"HTTP {r.status_code}")
            return None, r.read().decode()[:500]

        plan_data = None
        for line in r.iter_lines():
            if not line.startswith("data:"):
                continue
            d = json.loads(line[6:])
            if "content" in d:
                print(f"  AI: {d['content'][:100]}")
            elif "message" in d:
                print(f"  -> {d['message'][:100]}")
            elif "plan_id" in d:
                plan_data = d
        return plan_data, None

# 2. First message — UserInteractionAgent asks for preferences
plan, err = stream_msg("武汉出发去北京3天5000")
if err: print(f"Error: {err}"); sys.exit(1)
if plan: # Got plan directly (if preferences provided in message)
    pass
else:
    # 3. Reply with preferences
    plan, err = stream_msg("无偏好")

if not plan:
    print("\nNo plan generated. Trying with full params...")
    # 4. Confirm
    plan, err = stream_msg("确认")

if not plan:
    print("Failed to get plan after all turns")
    sys.exit(1)

# 5. Print plan
s = plan.get("summary", {})
print(f"\n{'='*60}")
print(f"  {s.get('origin','?')} -> {s.get('destination','?')}  {s.get('days',0)}天  ¥{s.get('trip_config',{}).get('total_budget',0)}")
print(f"{'='*60}")

daily = s.get("daily_itinerary") or s.get("daily_plan", [])
if not daily:
    print("\n  [WARN] daily_plan is empty!")
else:
    for day in daily:
        print(f"\n  [Day {day['day']}]")
        for a in day.get("attractions", []):
            p = f"¥{a['price']:.0f}" if a.get("price", 0) > 0 else "免费"
            print(f"    🏛 {a['name']} ({p}) — {a.get('reason','')[:40]}")
        for m in day.get("meals", []):
            print(f"    🍽 {m['restaurant']}: ¥{m.get('avg_price',0):.0f}/人")
        for m in day.get("meals_plan", []):
            print(f"    🍽 {m.get('restaurant','?')}: ¥{m.get('avg_price',0):.0f}/人")

# Hotel
h = s.get("hotel_plan", {})
if h.get("recommendations"):
    print(f"\n  [Hotel]")
    for r in h["recommendations"][:3]:
        print(f"    🏨 {r['name']} ¥{r.get('price_per_night',0):.0f}/晚 total=¥{r.get('total',0):.0f}")

# Budget
b = s.get("budget", {})
if b:
    print(f"\n  [Budget]")
    print(f"    实际: ¥{b.get('actual_total',0):.2f} / 预算: ¥{b.get('total_budget',0)}")
    for item in b.get("details", []):
        print(f"    {item.get('category','?')}: ¥{item.get('spent',0):.0f} / ¥{item.get('budget',0)}")

# Traffic
t = s.get("traffic", {})
if t:
    print(f"\n  [Traffic] 市内: ¥{t.get('total_cost',0):.0f}")
    for d in t.get("daily_traffic", []):
        print(f"    Day {d.get('day')}: {d.get('total_time_min',0)}min ¥{d.get('total_cost',0):.0f}")
        for seg in d.get("segments", [])[:2]:
            print(f"      {seg.get('from','?')} → {seg.get('to','?')} {seg.get('time_min',0)}min ¥{seg.get('cost',0):.0f}")

# Big traffic (处理 dict 和 list 两种情况)
bt = s.get("big_traffic", {})
if isinstance(bt, dict):
    btrains = bt.get("trains", [])
elif isinstance(bt, list):
    btrains = bt
else:
    btrains = []
if btrains:
    print(f"\n  [Big Traffic] {len(btrains)} options")
    for v in btrains[:3]:
        print(f"    {'✈' if 'flight' in str(type(v)).lower() else '🚄'} {v.get('trainCode','') or v.get('flight','?')}")

print(f"\n{'_'*60}")
print(f"plan_id: {plan.get('plan_id','?')}")
