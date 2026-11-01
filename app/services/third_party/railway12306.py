"""
12306 余票查询 — 极简持久连接版
"""

import json, ssl, time
from typing import Optional
from urllib.parse import urlencode

import httpx

INIT_URL = "https://kyfw.12306.cn/otn/leftTicket/init"
QUERY_BASE = "https://kyfw.12306.cn/otn/leftTicket/query"
PRICE_URL = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice"
STOPS_URL = "https://kyfw.12306.cn/otn/czxx/queryByTrainNo"
STATION_URL = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9230"

QUERY_SUFFIXES = list("ZOXYABCDEFGH")
PRICE_CODES = {"A9":"商务座","M":"一等座","O":"二等座","A4":"软卧","A3":"硬卧","A1":"硬座","WZ":"无座"}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
REF = "https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc"


class Railway12306:
    def __init__(self):
        self._active: Optional[str] = None
        self._stations: dict[str, str] = {}
        self._cookies: dict = {}

    def _client(self) -> httpx.Client:
        return httpx.Client(verify=False, timeout=30, headers={"User-Agent": UA})

    def _save(self, r: httpx.Response):
        self._cookies.update(dict(r.cookies))

    # ---- 车站 ----

    def fetch_stations(self) -> dict[str, str]:
        if self._stations: return self._stations
        try:
            with self._client() as c:
                body = c.get(STATION_URL).text
            s = body.find("'"); e = body.rfind("'")
            if s != -1 and e != -1:
                for seg in body[s+1:e].split("@"):
                    p = seg.split("|")
                    if len(p) >= 3: self._stations[p[1]] = p[2]
            print(f"  [12306] {len(self._stations)} 车站")
        except Exception as ex:
            print(f"  [12306] 车站: {ex}")
        return self._stations

    def _code(self, city: str) -> str:
        self.fetch_stations()
        if city in self._stations: return self._stations[city]
        for k, v in self._stations.items():
            if city in k or k in city: return v
        return city

    def _station_name(self, code: str) -> str:
        if not code:
            return ""
        self.fetch_stations()
        for name, station_code in self._stations.items():
            if station_code == code:
                return name
        return code

    # ---- 探测 ----

    def _detect(self, c: httpx.Client) -> Optional[str]:
        if self._active: return self._active
        h = {"User-Agent": UA, "Referer": REF, "X-Requested-With": "XMLHttpRequest", "If-Modified-Since": "0"}
        params = {"leftTicketDTO.train_date": "2026-07-10", "leftTicketDTO.from_station": "BJP",
                  "leftTicketDTO.to_station": "SHH", "purpose_codes": "ADULT"}
        # 先探测 c_url 重定向，再探测直接可用端点
        for s in QUERY_SUFFIXES:
            try:
                r = c.get(f"{QUERY_BASE}{s}?{urlencode(params)}", headers=h)
                body = r.text.replace("﻿", "").strip()
                if "c_url" in body:
                    cu = json.loads(body).get("c_url", "")
                    ex = cu.replace("leftTicket/query", "").replace("/otn/leftTicket/query", "").strip()
                    if ex and len(ex) <= 2:
                        self._active = ex; return ex
                if r.status_code == 200 and body.startswith("{") and json.loads(body).get("httpstatus") == 200:
                    self._active = s; return s
            except Exception: continue
        # 兜底：用 G（已验证有效）
        self._active = "G"
        return "G"

    # ---- 查询 ----

    def query_all_trains(self, fcity: str, tcity: str, date: str = "") -> list[dict]:
        fc = self._code(fcity); tc = self._code(tcity)
        if not date: date = time.strftime("%Y-%m-%d")

        # 单个会话内完成全部操作
        with self._client() as c:
            # 1. init
            c.get(INIT_URL)

            # 2. 探测
            suffix = self._detect(c)
            if not suffix: return []

            # 3. 查询
            h = {"User-Agent": UA, "Referer": REF, "X-Requested-With": "XMLHttpRequest",
                 "If-Modified-Since": "0"}
            params = {"leftTicketDTO.train_date": date, "leftTicketDTO.from_station": fc,
                      "leftTicketDTO.to_station": tc, "purpose_codes": "ADULT"}
            r = c.get(f"{QUERY_BASE}{suffix}?{urlencode(params)}", headers=h)
            body = r.text.replace("﻿", "").strip()

            # c_url → 同会话重试
            if "c_url" in body:
                cu = json.loads(body).get("c_url", "")
                ex = cu.replace("leftTicket/query", "").replace("/otn/leftTicket/query", "").strip()
                if ex and len(ex) <= 2:
                    self._active = ex
                    r = c.get(f"{QUERY_BASE}{ex}?{urlencode(params)}", headers=h)
                    body = r.text.replace("﻿", "").strip()

            if body.startswith("{"):
                return self._parse(body)
            return []

    def query_price(self, train_no: str, from_station_no: str, to_station_no: str,
                    date: str = "", seat_types: str = "") -> dict:
        if not date: date = time.strftime("%Y-%m-%d")
        try:
            with self._client() as c:
                c.get(INIT_URL)
                h = {"Referer": REF, "X-Requested-With": "XMLHttpRequest"}
                params = {"train_no": train_no, "from_station_no": from_station_no,
                          "to_station_no": to_station_no, "seat_types": seat_types or "".join(PRICE_CODES),
                          "train_date": date}
                data = c.get(f"{PRICE_URL}?{urlencode(params)}", headers=h).json()
            if data.get("httpstatus") != 200: return {}
            p = data.get("data", {})
            return {cn: p.get(cd, "").replace("¥", "").strip()
                    for cd, cn in PRICE_CODES.items() if p.get(cd)}
        except Exception as ex:
            print(f"  [12306] 票价: {ex}")
            return {}

    def query_stops(self, train_no: str, fcity: str, tcity: str, date: str = "") -> list[dict]:
        fc = self._code(fcity); tc = self._code(tcity)
        if not date: date = time.strftime("%Y-%m-%d")
        try:
            with self._client() as c:
                c.get(INIT_URL)
                h = {"Referer": REF, "X-Requested-With": "XMLHttpRequest"}
                params = {"train_no": train_no, "from_station_telecode": fc,
                          "to_station_telecode": tc, "depart_date": date}
                data = c.get(f"{STOPS_URL}?{urlencode(params)}", headers=h).json()
            return [{"stationNo": s.get("station_no", ""), "stationName": s.get("station_name", ""),
                     "arriveTime": s.get("arrive_time", ""), "startTime": s.get("start_time", ""),
                     "stopoverTime": s.get("stopover_time", "")}
                    for s in (data.get("data", {}).get("data") or [])]
        except Exception as ex:
            print(f"  [12306] 经停: {ex}")
            return []

    # ---- 解析 ----

    def _parse(self, raw: str) -> list[dict]:
        obj = json.loads(raw)
        if obj.get("httpstatus") != 200: return []
        results = obj.get("data", {}).get("result", [])
        trains = []
        for r in (results or []):
            a = r.split("|")
            if len(a) < 35: continue
            trains.append({
                "trainNo": a[2], "trainCode": a[3], "fromStation": a[6], "toStation": a[7],
                "startStation": a[4], "endStation": a[5],
                "fromStationCode": a[6], "toStationCode": a[7],
                "startStationName": self._station_name(a[4]),
                "endStationName": self._station_name(a[5]),
                "fromStationName": self._station_name(a[6]),
                "toStationName": self._station_name(a[7]),
                "departureTime": a[8], "arrivalTime": a[9], "duration": a[10],
                "fromStationNo": a[16], "toStationNo": a[17],
                "startTrainDate": a[13], "seatTypes": a[35] if len(a) > 35 else "",
                "businessClass": _f(a[32]), "firstClass": _f(a[31]), "secondClass": _f(a[30]),
                "softSleeper": _f(a[23]), "hardSleeper": _f(a[28]),
                "hardSeat": _f(a[29]), "noSeat": _f(a[26]),
            })
        return trains


def _f(v: str) -> str:
    if not v: return "--"
    if v == "无": return "无票"
    if v == "有": return "有票"
    if v.isdigit(): return f"{v}张"
    return v


railway = Railway12306()
