import re

def parse_quake_json(json_data, min_display="1", mode="full"):
    """
    気象庁の地震・津波関連JSONを受け取り、
    title, description, color, url を持つ辞書を返す
    mode: "full" (詳細・各地の震度含む) または "limit" (サマリのみ)
    """
    if not json_data or not isinstance(json_data, dict):
        return None

    # --- 震度比較・ソート用マッピングテーブル ---
    int_order = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5弱": 5, "5-": 5,
        "5強": 6, "5+": 6,
        "6弱": 7, "6-": 7,
        "6強": 8, "6+": 8,
        "7": 9
    }

    # --- リスト化保証ヘルパー（XML/JSONパース用） ---
    def safe_list(obj):
        if obj is None:
            return []
        if isinstance(obj, list):
            return obj
        return [obj]

    # 最上位直下に 'detail' がネストされている場合は展開する
    if "detail" in json_data and isinstance(json_data["detail"], dict):
        base_url = json_data.get("jma_web_url") or json_data.get("jma_url")
        json_data = json_data["detail"]
        if base_url and "jma_web_url" not in json_data and "jma_url" not in json_data:
            json_data["jma_web_url"] = base_url

    # URLの取得（最上位データ内、またはControl等からの取得に対応）
    jma_web_url = json_data.get("jma_web_url") or json_data.get("jma_url", "")

    # 出典フッターの作成
    footer = "（出典: 気象庁発表データ）"
    if jma_web_url:
        footer += f"\n{jma_web_url}"

    # --- 形式判定：気象庁 Web API（直下キー）形式かどうかのチェック ---
    if "earthquake" in json_data or "issue" in json_data:
        eq = json_data.get("earthquake", {})
        issue = json_data.get("issue", {})
        
        origin_time = eq.get("time", issue.get("time", "不明"))
        hypocenter = eq.get("hypocenter", {}).get("name", "調査中")
        magnitude = eq.get("hypocenter", {}).get("magnitude", "不明")
        max_int_raw = eq.get("maxScale", "-")
        
        # 数値表記の震度 (例: 10->1, 20->2, 45->5弱 ...) を文字列にマッピング
        scale_map = {
            10: "1", 20: "2", 30: "3", 40: "4",
            45: "5弱", 50: "5強", 55: "6弱", 60: "6強", 70: "7"
        }
        max_int = scale_map.get(max_int_raw, str(max_int_raw) if max_int_raw != -1 else "-")

        tsunami_msg = eq.get("domesticTsunami", "なし")
        if tsunami_msg == "None": tsunami_msg = "なし"
        elif tsunami_msg == "Warning": tsunami_msg = "津波警報発表中"
        elif tsunami_msg == "NonEffective": tsunami_msg = "若干の海面変動あり（被害の心配なし）"

        lines = [
            f"発生時刻：{origin_time}",
            f"震源地 ：{hypocenter}（M{magnitude}）",
            f"最大震度：{max_int}",
            f"津波影響：{tsunami_msg}"
        ]

        # full モードの時だけ「各地の震度」を展開
        if mode == "full":
            lines.append("----------------")
            lines.append(f"各地の震度（震度 {min_display} 以上を表示）")

            min_val = int_order.get(str(min_display), 1)
            points = json_data.get("points", [])
            report_struct = {}
            
            for pt in points:
                pt_int_raw = pt.get("scale", 0)
                pt_int = scale_map.get(pt_int_raw, str(pt_int_raw))
                if int_order.get(str(pt_int), 0) < min_val:
                    continue
                
                pref_name = pt.get("pref", "その他")
                addr_name = pt.get("addr", pt.get("name", ""))
                
                if pt_int not in report_struct: report_struct[pt_int] = {}
                if pref_name not in report_struct[pt_int]: report_struct[pt_int][pref_name] = []
                if addr_name:
                    report_struct[pt_int][pref_name].append(addr_name)

            if not report_struct:
                lines.append("該当する詳細情報はありません。")
            else:
                for int_level in sorted(report_struct.keys(), key=lambda x: int_order.get(str(x), 0), reverse=True):
                    lines.append(f"■震度 {int_level}")
                    for pref, addrs in report_struct[int_level].items():
                        if addrs:
                            lines.append(f" [{pref}] {' '.join(addrs)}")

        lines.append("----------------")
        lines.append(footer)

        color = 0x3498DB
        if max_int in ["5弱", "5-", "5強", "5+"]: color = 0xE67E22
        elif max_int in ["6弱", "6-", "6強", "6+", "7"]: color = 0xFF0000

        return {
            "title": f"【地震情報（{issue.get('type', '震源・震度情報')}）】",
            "description": "\n".join(lines),
            "color": color,
            "url": jma_web_url
        }

    # --- 防災XML形式 (Control / Head / Body) の処理 ---
    control = json_data.get("Control", {})
    head = json_data.get("Head", {})
    body = json_data.get("Body", {})
    c_title = control.get("Title", "")
    h_title = head.get("Title", "地震情報")

    # --- A. 津波情報の場合 ---
    if "津波" in h_title or head.get("InfoKind") == "津波警報・注意報・予報":
        headline = head.get("Headline", {}).get("Text", "詳細な情報は本文を確認してください。")
        tsunami_node = body.get("Tsunami", {})
        
        warn_details = []  
        forecast_details = []
        
        # 1. 予報（エリア名と種別）
        forecast_items = safe_list(tsunami_node.get("Forecast", {}).get("Item", []))
        for item in forecast_items:
            area_name = item.get('Area', {}).get('Name', '不明なエリア')
            kind_name = item.get('Category', {}).get('Kind', {}).get('Name', '情報なし')
            if "予報" in kind_name:
                forecast_details.append(area_name)
            else:
                warn_details.append(f"・{area_name}：{kind_name}")

        lines = [
            f"発表時刻：{head.get('ReportDateTime', '不明')}",
            "----------------",
            f"概況：\n{headline}",
            "----------------"
        ]

        if warn_details or forecast_details:
            lines.append("情報詳細：")
            lines.extend(warn_details)
            if forecast_details:
                lines.append(f"・予報(若干の海面変動)：{', '.join(forecast_details)}")

        # full モードの時だけ潮位観測値リストを含める
        if mode == "full":
            obs_data_list = []
            obs_items = safe_list(tsunami_node.get("Observation", {}).get("Item", []))
            for item in obs_items:
                stations = safe_list(item.get("Station", []))
                if not stations and "Target" in item:
                    stations = safe_list(item.get("Target", {}).get("Station", []))

                for st in stations:
                    st_name = st.get("Name", "不明な地点")
                    max_h = st.get("MaxHeight", {})
                    h_val = max_h.get("TsunamiHeight")
                    condition = max_h.get("Condition")
                    
                    sort_val = -1.0
                    if h_val is not None:
                        matches = re.findall(r"\d+\.?\d*", str(h_val))
                        if matches:
                            try:
                                sort_val = float(matches[0])
                            except ValueError:
                                sort_val = -1.0

                    display_val = f"{h_val}m" if h_val is not None else (condition if condition else "観測中")
                    obs_data_list.append({"name": st_name, "val": display_val, "sort_key": sort_val})

            obs_data_list.sort(key=lambda x: x["sort_key"], reverse=True)

            if obs_data_list:
                lines.append("--- 潮位観測値（高い順） ---")
                for d in obs_data_list:
                    lines.append(f"・{d['name']}：{d['val']}")

        lines.append(footer)

        return {
            "title": f"【{h_title}】",
            "description": "\n".join(lines),
            "color": 0xFF0000 if ("警報" in h_title or "大津波" in headline) else 0xE67E22,
            "url": jma_web_url
        }

    # --- C. 遠地地震に関する情報の場合 ---
    elif "遠地地震" in h_title:
        eq = body.get("Earthquake", {})
        if not eq: 
            eqs = safe_list(body.get("Earthquakes", []))
            if eqs: eq = eqs[0]
            else: return None
            
        origin_time = eq.get("OriginTime", "不明")
        hypocenter = eq.get("Hypocenter", {}).get("Area", {}).get("Name", "調査中")
        magnitude = eq.get("Magnitude", "不明")

        comments = body.get("Comments", {})
        tsunami_msg = comments.get("ForecastComment", {}).get("Text", "なし")
        free_comment = comments.get("FreeFormComment", "")

        lines = [
            f"発生時刻：{origin_time}",
            f"震源地 ：{hypocenter}（M{magnitude}）",
            f"津波影響：\n{tsunami_msg.strip()}",
            "----------------"
        ]

        if free_comment and mode == "full":
            lines.append(f"付随情報：{free_comment}")
            lines.append("----------------")

        lines.append("※海外で発生した大規模な地震の情報です。")
        lines.append(footer)

        return {
            "title": "【遠地地震に関する情報】",
            "description": "\n".join(lines),
            "color": 0x3498DB,
            "url": jma_web_url
        }

    # --- B. 地震情報（震源・震度報）の場合 ---
    elif "震源" in c_title or "震度" in h_title or "地震" in h_title:
        eq = body.get("Earthquake", {})
        origin_time = eq.get("OriginTime", "不明")
        hypocenter = eq.get("Hypocenter", {}).get("Area", {}).get("Name", "調査中")
        magnitude = eq.get("Magnitude", "不明")
        
        intensity_obs = body.get("Intensity", {}).get("Observation", {})
        max_int = intensity_obs.get("MaxInt", "-")
        tsunami_msg = body.get("Comments", {}).get("ForecastComment", {}).get("Text", "なし")

        lines = [
            f"発生時刻：{origin_time}",
            f"震源地 ：{hypocenter}（M{magnitude}）",
            f"最大震度：{max_int}",
            f"津波影響：{tsunami_msg}"
        ]

        # full モードの時だけ「各地の震度」の市町村リストを組み立てて追加する
        if mode == "full":
            lines.append("----------------")
            lines.append(f"各地の震度（震度 {min_display} 以上を表示）")

            min_val = int_order.get(str(min_display), 1)
            report_struct = {}
            
            for pref in safe_list(intensity_obs.get("Pref", [])):
                pref_name = pref.get("Name")
                for area in safe_list(pref.get("Area", [])):
                    area_name = area.get("Name")
                    for city in safe_list(area.get("City", [])):
                        city_int = city.get("MaxInt", "-")
                        if int_order.get(str(city_int), 0) < min_val: continue
                        
                        if city_int not in report_struct: report_struct[city_int] = {}
                        if pref_name not in report_struct[city_int]: report_struct[city_int][pref_name] = {}
                        if area_name not in report_struct[city_int][pref_name]: report_struct[city_int][pref_name][area_name] = []
                        
                        c_name = city.get("Name")
                        if c_name:
                            report_struct[city_int][pref_name][area_name].append(c_name)

            if not report_struct:
                lines.append("該当する詳細情報はありません。")
            else:
                for int_level in sorted(report_struct.keys(), key=lambda x: int_order.get(str(x), 0), reverse=True):
                    lines.append(f"■震度 {int_level}")
                    for pref, areas in report_struct[int_level].items():
                        for area, cities in areas.items():
                            if cities:
                                lines.append(f" [{area}] {' '.join(cities)}")

        lines.append("----------------")
        lines.append(footer)

        color = 0x3498DB  # デフォルト青
        if max_int in ["5弱", "5-", "5強", "5+"]:
            color = 0xE67E22  # オレンジ
        elif max_int in ["6弱", "6-", "6強", "6+", "7"]:
            color = 0xFF0000  # 赤

        return {
            "title": f"【{h_title}】",
            "description": "\n".join(lines),
            "color": color,
            "url": jma_web_url
        }
        
    # --- D. その他の地震関連情報・解説情報の場合（南海トラフ等） ---
    earthquake_info = body.get("EarthquakeInfo", {})
    text_content = earthquake_info.get("Text") or head.get("Headline", {}).get("Text") or body.get("Text", "")
    
    if text_content or h_title:
        headline_text = head.get("Headline", {}).get("Text", "")
        body_text = earthquake_info.get("Text", "") or body.get("Text", "")
        appendix = earthquake_info.get("Appendix", "")
        
        lines = [
            f"発表時刻：{head.get('ReportDateTime', '不明')}",
            "----------------"
        ]
        
        if headline_text and headline_text != text_content:
            lines.append(f"概況：\n{headline_text}")
            lines.append("----------------")
            
        # full の場合のみ詳細本文と補足を入れる
        if mode == "full":
            if body_text:
                lines.append(str(body_text))
            elif text_content:
                lines.append(str(text_content))
                
            if appendix:
                lines.append("----------------")
                lines.append(str(appendix))
            lines.append("----------------")
            
        lines.append(footer)
        
        return {
            "title": f"【{h_title}】",
            "description": "\n".join(lines),
            "color": 0x3498DB,
            "url": jma_web_url
        }

    return None