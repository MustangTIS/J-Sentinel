import csv
import json
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
import discord

def load_area_hierarchy(codemaster_dir):
    """
    areakisyou.csv と areakisyou2.csv から、市町村名 -> 属する地域名・コードのマップを作る
    """
    city_to_local = {} # 例: "帯広市" -> {"local_code": "014032", "local_name": "十勝中部"}
    local_codes = set()

    city_csv = os.path.join(codemaster_dir, "areakisyou.csv")
    if os.path.exists(city_csv):
        try:
            df = pd.read_csv(city_csv, header=None, encoding="utf-8", encoding_errors="ignore")
            for idx, row in df.iterrows():
                if idx < 2: continue # ヘッダースキップ
                if len(row) >= 5:
                    city_name = str(row.iloc[2]).strip() # 例: 帯広市
                    city_code = str(row.iloc[0]).strip() # 例: 0120700
                    local_code = str(row.iloc[4]).strip() # 例: 014032
                    if city_name and local_code and local_code != "nan":
                        city_to_local[city_name] = local_code
                        # 「北海道帯広市」などのパターンにも対応
                        full_city_name = str(row.iloc[1]).strip()
                        if full_city_name:
                            city_to_local[full_city_name] = local_code
        except Exception as e:
            print(f"areakisyou.csv 読み込みエラー: {e}")

    local_name_map = {}
    local_csv = os.path.join(codemaster_dir, "areakisyou2.csv")
    if os.path.exists(local_csv):
        try:
            df_local = pd.read_csv(local_csv, header=None, encoding="utf-8", encoding_errors="ignore")
            for idx, row in df_local.iterrows():
                if idx < 2: continue
                if len(row) >= 2:
                    l_code = str(row.iloc[0]).strip()
                    l_name = str(row.iloc[1]).strip()
                    if l_code and l_name:
                        local_name_map[l_code] = l_name
        except Exception as e:
            print(f"areakisyou2.csv 読み込みエラー: {e}")

    return city_to_local, local_name_map

def get_weather_info(json_path, codemaster_dir, target_region):
    if not os.path.exists(json_path):
        return "天気データファイルが見つかりませんでした。"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"天気データの読み込みに失敗しました: {e}"

    city_to_local, local_name_map = load_area_hierarchy(codemaster_dir)

    # ターゲットが市町村名なら対応するローカルコード（十勝中部など）を割り出す
    target_local_code = city_to_local.get(target_region)
    target_local_name = local_name_map.get(target_local_code, "") if target_local_code else ""

    offices = data.get("offices", {})
    target_office_data = None
    matched_area_name = ""

    # 気象庁JSON内を走査して、該当するエリアデータを探す
    for office_code, office_info in offices.items():
        office_name = office_info.get("officeName", "")
        
        for report in office_info.get("reports", []):
            for ts in report.get("timeSeries", []):
                for area in ts.get("areas", []):
                    area_name = area.get("area", {}).get("name", "")
                    area_code = area.get("area", {}).get("code", "")
                    
                    # 1. エリア名やコードが直接一致するか
                    # 2. 紐づいたローカル名（十勝中部など）が一致するか
                    if (target_region in area_name or area_name in target_region or 
                        (target_local_name and target_local_name in area_name) or
                        (target_local_code and area_code == target_local_code)):
                        target_office_data = office_info
                        matched_area_name = area_name
                        break
                if target_office_data:
                    break
            if target_office_data:
                break
        if target_office_data:
            break

    # もしオフィスデータが直で見つからなければ、十勝・釧路などの親オフィス（例: 釧路地方気象台 = 014000系）をフォールバックで探す
    if not target_office_data:
        for office_code, office_info in offices.items():
            office_name = office_info.get("officeName", "")
            if "釧路" in office_name or "十勝" in office_name or "帯広" in office_name:
                target_office_data = office_info
                matched_area_name = office_name
                break

    if not target_office_data:
        return f"「{target_region}（関連地域: {target_local_name}）0」に該当する天気予報データが見つかりませんでした。"

    reports = target_office_data.get("reports", [])
    if not reports:
        return "有効な予報レポートが見つかりませんでした。"

    latest_report = reports[0]
    pub_office = latest_report.get("publishingOffice", "")

    now_jst = datetime.now(timezone(timedelta(hours=9)))

    daily_data = {}

    def get_bucket(d_str):
        if d_str not in daily_data:
            daily_data[d_str] = {"weather": [], "pops": [], "temps": []}
        return daily_data[d_str]

    current_weather = None
    current_temp = None
    min_weather_diff = timedelta(days=99)
    min_temp_diff = timedelta(days=99)

    for ts in latest_report.get("timeSeries", []):
        time_defines = ts.get("timeDefines", [])
        
        for area in ts.get("areas", []):
            area_name = area.get("area", {}).get("name", "")
            area_code = area.get("area", {}).get("code", "")

            # ターゲット地域、または紐づくローカル地域、あるいは十勝・全域のデータを拾う
            is_match = (
                target_region in area_name or 
                area_name in target_region or 
                (target_local_name and target_local_name in area_name) or
                (target_local_code and area_code == target_local_code) or
                "十勝" in area_name or "帯広" in area_name
            )

            if not is_match and len(daily_data) > 0:
                continue

            # A. 天気
            weathers = area.get("weathers", []) or area.get("weatherTexts", [])
            if weathers:
                for i, w in enumerate(weathers):
                    if w and i < len(time_defines):
                        dt_str = time_defines[i]
                        d_str = dt_str[:10]
                        w_clean = w.strip()
                        bucket = get_bucket(d_str)
                        if w_clean not in bucket["weather"]:
                            bucket["weather"].append(w_clean)
                        
                        try:
                            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                            diff = abs(dt - now_jst)
                            if diff < min_weather_diff:
                                min_weather_diff = diff
                                current_weather = w_clean
                        except:
                            pass

            # B. 降水確率
            pops = area.get("pops", [])
            if pops:
                for i, p in enumerate(pops):
                    if p is not None and str(p).strip() != "" and i < len(time_defines):
                        dt_str = time_defines[i]
                        try:
                            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                            time_label = dt.strftime("%H時")
                        except:
                            time_label = f"#{i+1}"
                        
                        d_str = dt_str[:10]
                        pop_entry = f"{time_label}:{p}%"
                        bucket = get_bucket(d_str)
                        if pop_entry not in bucket["pops"]:
                            bucket["pops"].append(pop_entry)

            # C. 気温
            for temp_key in ["temps", "tempsMax", "tempsMin"]:
                temps_list = area.get(temp_key, [])
                if temps_list:
                    for i, t in enumerate(temps_list):
                        if t is not None and str(t).strip() != "" and i < len(time_defines):
                            dt_str = time_defines[i]
                            d_str = dt_str[:10]
                            
                            prefix = ""
                            if "Max" in temp_key:
                                prefix = "最高"
                            elif "Min" in temp_key:
                                prefix = "最低"
                            
                            temp_entry = f"{prefix}{t}℃"
                            bucket = get_bucket(d_str)
                            if temp_entry not in bucket["temps"]:
                                bucket["temps"].append(temp_entry)
                            
                            if temp_key == "temps":
                                try:
                                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                                    diff = abs(dt - now_jst)
                                    if diff < min_temp_diff:
                                        min_temp_diff = diff
                                        current_temp = f"{t}℃"
                                except:
                                    pass

    if not current_weather:
        for d_str in sorted(daily_data.keys()):
            if daily_data[d_str]["weather"]:
                current_weather = daily_data[d_str]["weather"][0]
                break

    today_str = now_jst.strftime("%Y-%m-%d")
    if not current_temp and today_str in daily_data and daily_data[today_str]["temps"]:
        for t_item in daily_data[today_str]["temps"]:
            if "最高" not in t_item and "最低" not in t_item:
                current_temp = t_item
                break
        if not current_temp:
            current_temp = daily_data[today_str]["temps"][0]

    # --- Discord Embed の生成 ---
    embed = discord.Embed(
        color=0x2b5278
    )

    header_lines = [f"### 🗾 {target_region}"]
    sub_info = []
    if current_temp:
        sub_info.append(f"**🌡{current_temp}**")
    if current_weather:
        sub_info.append(f"{current_weather}")
    
    if sub_info:
        header_lines.append(" ".join(sub_info))
    
    header_lines.append(f"-_発表: {pub_office} ({matched_area_name})_")
    embed.description = "\n".join(header_lines)

    labels = ["今日", "明日", "明後日"]
    sorted_dates = sorted([d for d in daily_data.keys() if daily_data[d]["weather"] or daily_data[d]["temps"] or daily_data[d]["pops"]])

    for idx, d_str in enumerate(sorted_dates[:3]):
        info = daily_data[d_str]
        day_label = labels[idx] if idx < len(labels) else d_str

        field_lines = []
        if info["weather"]:
            field_lines.append(f"**天候🌦**: {' / '.join(info['weather'])}")
        if info["temps"]:
            field_lines.append(f"**気温🌡**: {' '.join(info['temps'])}")
        if info["pops"]:
            field_lines.append(f"**降水確率☔**: {' '.join(info['pops'])}")

        val_text = "\n".join(field_lines) if field_lines else "情報なし"
        embed.add_field(
            name=f"📅 {day_label} ({d_str})",
            value=val_text,
            inline=False
        )

    return embed