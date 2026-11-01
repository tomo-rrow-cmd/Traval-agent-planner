# Helper script to replace getTestContentBlocks function
import re

with open('D:/TLA-Mul-agents/frontend/src/views/PlanDetailPage.vue', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'function getTestContentBlocks()'
end_marker = '</script>'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)
if start_idx == -1 or end_idx == -1:
    print("ERROR: markers not found")
    exit(1)

before = content[:start_idx]
after = content[end_idx:]

new_test_func = r"""function getTestContentBlocks() {
  return [
    { type: 'header', data: { title: '长沙7日深度游', destination: '长沙', origin: '广州', days: 7, pace: '适中', traveler_count: 1, total_budget: 5000, estimated_cost: 3932 } },
    { type: 'text', data: { content: '**广州 \u2192 长沙** 深度7日游。总预算\u00a55000，预估花费\u00a53932，剩余\u00a51068。' } },
    { type: 'highlights', data: { items: [{emoji:'\U0001F3DB',text:'湖南省博物馆马王堆'},{emoji:'\U0001F304',text:'登岳麓山俯瞰湘江'},{emoji:'\U0001F35C',text:'太平老街美食之旅'},{emoji:'\U0001F3A8',text:'梅溪湖艺术打卡'}] } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon: 'sun', title: '每日行程', subtitle: '7天3个核心区域，节奏舒适' } },
    { type: 'day_card', data: { day:1, date:'2026-07-10', label:'\u5468\u4e94', weather_summary:'\u6674 32\u00b0C', day_cost:315, day_summary:'从千年学府到湘江中心，感受长沙底蕴。', activities: [
      { title:'\u5cb3\u9e93\u5c71', description:'长沙地标，海拔300米。先参观岳麓书院(四大书院之一)，登顶俯瞰湘江和橘子洲全景。顺路看爱晚亭。建议穿舒适步行鞋，全程约3小时。', cost:0, duration_minutes:180, tags:['\u6587\u5316','\u5fc5\u53bb'], type:'attraction', location:{lng:112.947,lat:28.193} },
      { title:'\u6a58\u5b50\u6d32', description:'湘江狭长岛屿，长5公里。核心是毛泽东雕塑(高32米)。可乘小火车(\u00a520)往返，傍晚夕阳洒江面最佳拍照。', cost:0, duration_minutes:120, tags:['\u7ecf\u5178','\u62cd\u7167'], type:'attraction', location:{lng:112.960,lat:28.175} },
      { title:'\u592a\u5e73\u8001\u8857', description:'保存最完好的历史街区，汇集黑色经典臭豆腐、糖油粑粑等标志性小吃。建议晚上前往，灯光下更有韵味。', cost:0, duration_minutes:90, tags:['\u7f8e\u98df','\u591c\u666f'], type:'attraction', location:{lng:112.978,lat:28.197} },
    ], accommodation:{hotel_name:'\u5320\u5bbf\u9152\u5e97(\u4e94\u4e00\u5e7f\u573a)', price:400, address:'\u8299\u84c9\u533a\u4e94\u4e00\u5e7f\u573a', rating:4.7} } },
    { type: 'day_card', data: { day:2, date:'2026-07-11', label:'\u5468\u516d', weather_summary:'\u591a\u4e91 30\u00b0C', day_cost:280, day_summary:'深入文化内核，千年古墓文物到古城墙历史回望。', activities: [
      { title:'\u6e56\u5357\u7701\u535a\u7269\u9986', description:'国家一级博物馆。最大看点马王堆汉墓\u2014\u2014辛追夫人遗体(2100年)、素纱襌衣(49克)、T型帛画。免费但需公众号预约，周一闭馆。', cost:0, duration_minutes:180, tags:['\u6587\u5316','\u535a\u7269\u9986'], type:'attraction', location:{lng:113.004,lat:28.209} },
      { title:'\u5929\u5fc3\u9601', description:'长沙古城标志，明代始建。登顶俯瞰古城风貌，附近保留明清城墙遗迹。', cost:32, duration_minutes:90, tags:['\u5386\u53f2','\u767b\u9ad8'], type:'attraction', location:{lng:112.982,lat:28.186} },
      { title:'\u5761\u5b50\u8857', description:'最负盛名美食街。火宫殿(260年历史)聚集长沙最全小吃。', cost:0, duration_minutes:120, tags:['\u7f8e\u98df'], type:'attraction', location:{lng:112.976,lat:28.191} },
    ], accommodation:{hotel_name:'\u5320\u5bbf\u9152\u5e97(\u4e94\u4e00\u5e7f\u573a)', price:400, address:'\u8299\u84c9\u533a\u4e94\u4e00\u5e7f\u573a', rating:4.7} } },
    { type: 'day_card', data: { day:3, date:'2026-07-12', label:'\u5468\u65e5', weather_summary:'\u9635\u96e8 28\u00b0C', day_cost:195, day_summary:'自然与艺术碰撞，城市绿肺到世界级建筑地标。', activities: [
      { title:'\u6e56\u5357\u7701\u690d\u7269\u56ed', description:'140公顷城市森林氧吧。世界名花园、樱花园等园区，夏季绿树成荫适合散步拍照。', cost:20, duration_minutes:150, tags:['\u81ea\u7136','\u62cd\u7167'], type:'attraction', location:{lng:113.028,lat:28.118} },
      { title:'\u6885\u6eaa\u6e56\u6587\u5316\u827a\u672f\u4e2d\u5fc3', description:'扎哈\u00b7哈迪德遗作，三朵芙蓉花造型。即使不看演出，外围散步拍照也很值。', cost:0, duration_minutes:90, tags:['\u5efa\u7b51','\u6253\u5361'], type:'attraction', location:{lng:112.897,lat:28.193} },
      { title:'\u4e07\u5bb6\u4e3d\u5e7f\u573a', description:'亚洲最大单体建筑之一。顶层空中花园俯瞰城市天际线，傍晚看日落绝佳。', cost:0, duration_minutes:90, tags:['\u901b\u8857','\u65e5\u843d'], type:'attraction', location:{lng:113.035,lat:28.195} },
    ], accommodation:{hotel_name:'\u5320\u5bbf\u9152\u5e97(\u4e94\u4e00\u5e7f\u573a)', price:400, address:'\u8299\u84c9\u533a\u4e94\u4e00\u5e7f\u573a', rating:4.7} } },
    { type: 'callout', data: { icon:'landmark', level:'info', title:'博物馆参观提示', text:'提前3天公众号预约。周一闭馆，周末建议上午9点前到场。禁止闪光灯。' } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon:'train', title:'大交通推荐', subtitle:'广州南站到长沙南站，高铁2.5-3小时' } },
    { type: 'traffic_list', data: { trains: [{ trainCode:'G6101', fromStationName:'广州南', toStationName:'长沙南', departureTime:'08:00', arrivalTime:'11:30', duration:'3h30m', prices:{'二等座':314,'一等座':504} }, { trainCode:'G6112', fromStationName:'广州南', toStationName:'长沙南', departureTime:'09:15', arrivalTime:'12:45', duration:'3h30m', prices:{'二等座':314,'一等座':504} }, { trainCode:'G6028', fromStationName:'广州南', toStationName:'长沙南', departureTime:'14:30', arrivalTime:'17:55', duration:'3h25m', prices:{'二等座':299,'一等座':478} }] } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon:'tip', title:'市内交通', subtitle:'地铁为主，打车/共享单车为辅' } },
    { type: 'text', data: { content: '6条线路覆盖主要景点。推荐下载长沙地铁APP或微信/支付宝乘车码。3日票\u00a540不限次。打车起步价\u00a58，市区15-30元。' } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon:'info', title:'预算分析', subtitle:'总预算\u00a55000，预估\u00a53932，剩余\u00a51068' } },
    { type: 'budget_chart', data: { total:5000, breakdown:{transport:942, accommodation:1960, food:910, attractions:120, souvenirs:0, contingency:500} } },
    { type: 'callout', data: { icon:'warning', level:'warning', title:'住宿预警', text:'住宿\u00a5500/晚\u00d76晚=\u00a53000，超预算\u00a51250。建议2-3晚经济型。' } },
    { type: 'callout', data: { icon:'tip', level:'success', title:'省钱建议', text:'核心景点多免费。餐饮\u00a51000绰绰有余，长沙美食丰俭由人。' } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon:'tip', title:'出行贴士', subtitle:'行前准备和实用建议' } },
    { type: 'text', data: { content: '**行前**：防晒伞+防晒霜+便携风扇必备。湘菜偏辣备肠胃药。每天步行1-2万步穿舒适鞋。\\n\\n**技巧**：太平老街坡子街晚上去。省博周一闭馆需预约。地铁微信/支付宝扫码。岳麓山南大门上东大门下。' } },
    { type: 'list', data: { title:'行李清单', description:'逐项核对不遗漏', items:['身份证','手机+充电器','充电宝','防晒霜','遮阳帽','便携风扇','肠胃药','雨伞','步行鞋','换洗衣物','洗漱用品'], style:'tags'} },
  ]
}"""

result = before + new_test_func + after
with open('D:/TLA-Mul-agents/frontend/src/views/PlanDetailPage.vue', 'w', encoding='utf-8') as f:
    f.write(result)
print("OK:", len(content), "->", len(result))
