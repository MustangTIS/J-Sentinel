import csv
import json
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
import discord

def load_area_mapping(codemaster_dir):
    mapping = {}
    csv_path = os.path.join(codemaster_dir, "arealink.csv")
    if not os.path.exists(csv_path):
        return mapping

    try:
        df = pd.read_csv(csv_path, header=None, encoding="utf-8", encoding_errors="ignore")
        for idx, row in df.iterrows():
            if len(row) >= 2:
                region_name = str(row.iloc[0]).strip()
                cities_str = str(row.iloc[1]).strip()
                cities = cities_str.replace('＊', '').split('、')
                for city in cities:
                    city = city.strip()
                    if city:
                        mapping[city] = region_name
    except Exception as e:
        print(f"arealink.csv の読み込みエラー: {e}")
        
    return mapping

def get_weather_info(json_path, codemaster_dir, target_region):
    if not os.path.exists(json_path):
        return "天気データファイルが見つかりませんでした。"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"天気データの読み込みに失敗しました: {e}"

    area_mapping = load_area_mapping(codemaster_dir)
    search_key = area_mapping.get(target_region, target_region)

    offices = data.get("offices", {})
    target_office_data = None
    matched_office_name = ""

    # 1. 対象のオフィス（地方気象台データ）を特定する
    for office_code, office_info in offices.items():
        office_name = office_info.get("officeName", "")
        if search_key in office_name or target_region in office_name:
            target_office_data = office_info
            matched_office_name = office_name
            break

        for report in office_info.get("reports", []):
            for ts in report.get("timeSeries", []):
                for area in ts.get("areas", []):
                    area_name = area.get("area", {}).get("name", "")
                    if search_key in area_name or target_region in area_name:
                        target_office_data = office_info
                        matched_office_name = area_name
                        break
                if target_office_data:
                    break
            if target_office_data:
                break
        if target_office_data:
            break

    if not target_office_data:
        return f"「{target_region}（検索キー: {search_key}）」に該当する天気予報データは見つかりませんでした。"

    reports = target_office_data.get("reports", [])
    if not reports:
        return "有効な予報レポートが見つかりませんでした。"

    latest_report = reports[0]
    pub_office = latest_report.get("publishingOffice", "")

    # 現在時刻の基準（JST）
    now_jst = datetime.now(timezone(timedelta(hours=9)))

    # 日付ごとの情報を格納する辞書
    daily_data = {}

    def get_bucket(d_str):
        if d_str not in daily_data:
            daily_data[d_str] = {"weather": [], "pops": [], "temps": []}
        return daily_data[d_str]

    # 現在時刻に最も近いデータを探すための変数
    current_weather = None
    current_temp = None
    min_weather_diff = timedelta(days=99)
    min_temp_diff = timedelta(days=99)

    # 2. timeSeries を走査して、天気・気温・降水確率を抽出
    for ts in latest_report.get("timeSeries", []):
        time_defines = ts.get("timeDefines", [])
        
        for area in ts.get("areas", []):
            area_name = area.get("area", {}).get("name", "")
            
            is_target_area = (
                target_region in area_name or 
                search_key in area_name or 
                area_name in matched_office_name or 
                matched_office_name in area_name
            )
            
            if not is_target_area:
                continue

            # A. 天気データの処理 (weathers / weatherTexts)
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
                        
                        # 現在時刻に一番近い天気を判定
                        try:
                            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                            diff = abs(dt - now_jst)
                            if diff < min_weather_diff:
                                min_weather_diff = diff
                                current_weather = w_clean
                        except:
                            pass

            # B. 降水確率の処理 (pops)
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

            # C. 気温データの処理 (temps, tempsMax, tempsMin)
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
                            
                            # 通常の気温（temps）かつ現在時刻に一番近いものを直近気温の候補にする
                            if temp_key == "temps":
                                try:
                                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                                    diff = abs(dt - now_jst)
                                    if diff < min_temp_diff:
                                        min_temp_diff = diff
                                        current_temp = f"{t}℃"
                                except:
                                    pass

    # フォールバック：もし temps がうまく取れず今日のデータがあれば、今日の最初の気温を使う
    today_str = now_jst.strftime("%Y-%m-%d")
    if not current_temp and today_str in daily_data and daily_data[today_str]["temps"]:
        for t_item in daily_data[today_str]["temps"]:
            if "最高" not in t_item and "最低" not in t_item:
                current_temp = t_item
                break
        if not current_temp:
            current_temp = daily_data[today_str]["temps"][0]

    # --- 3. Discord Embed の生成 ---
    embed = discord.Embed(
        title=f"【{target_region} の天気予報】",
        description=f"発表: {pub_office} (対象エリア: {matched_office_name})",
        color=0x3498db
    )

    # 【追加】現在時刻に最も近い天候と気温を先頭に配置
    current_lines = []
    if current_weather:
        current_lines.append(f"🌤 **天候**: {current_weather}")
    if current_temp:
        current_lines.append(f"🌡 **気温**: {current_temp}")
    
    if current_lines:
        embed.add_field(
            name="🕒 現在の天候・気温（直近）",
            value="\n".join(current_lines),
            inline=False
        )

    labels = ["今日", "明日", "明後日"]
    sorted_dates = sorted([d for d in daily_data.keys() if daily_data[d]["weather"] or daily_data[d]["temps"] or daily_data[d]["pops"]])

    for idx, d_str in enumerate(sorted_dates[:3]):
        info = daily_data[d_str]
        day_label = labels[idx] if idx < len(labels) else d_str

        field_lines = []
        if info["weather"]:
            field_lines.append(f"🌤 **天候**: {' / '.join(info['weather'])}")
        if info["temps"]:
            field_lines.append(f"🌡 **気温**: {' '.join(info['temps'])}")
        if info["pops"]:
            field_lines.append(f"☔ **降水確率**: {' '.join(info['pops'])}")

        val_text = "\n".join(field_lines) if field_lines else "情報なし"
        embed.add_field(
            name=f"📅 {day_label} ({d_str})",
            value=val_text,
            inline=False
        )

    return embed