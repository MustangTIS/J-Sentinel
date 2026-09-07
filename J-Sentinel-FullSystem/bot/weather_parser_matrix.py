import os
import json
import pandas as pd
from datetime import datetime, timezone, timedelta

def load_area_hierarchy(codemaster_dir):
    """
    areakisyou.csv と areakisyou2.csv から、市町村名 -> 属する地域名・コードのマップを作る
    """
    city_to_local = {} 
    city_csv = os.path.join(codemaster_dir, "areakisyou.csv")
    if os.path.exists(city_csv):
        try:
            df = pd.read_csv(city_csv, header=None, encoding="utf-8", encoding_errors="ignore")
            for idx, row in df.iterrows():
                if idx < 2: continue 
                if len(row) >= 5:
                    city_name = str(row.iloc[2]).strip() 
                    local_code = str(row.iloc[4]).strip() 
                    if city_name and local_code and local_code != "nan":
                        city_to_local[city_name] = local_code
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

def parse_area_forecasts(latest_report, target_region, target_local_name, target_local_code, pub_office):
    """
    1つのレポートの中から、target_region に一致するすべてのエリアの予報データを抽出してテキストブロックのリストとして返す
    """
    now_jst = datetime.now(timezone(timedelta(hours=9)))
    matched_blocks = []

    for ts in latest_report.get("timeSeries", []):
        time_defines = ts.get("timeDefines", [])
        
        for area in ts.get("areas", []):
            area_name = area.get("area", {}).get("name", "")
            area_code = area.get("area", {}).get("code", "")

            # 該当エリアかどうかの判定
            is_match = (
                target_region in area_name or 
                area_name in target_region or 
                (target_local_name and target_local_name in area_name) or
                (target_local_code and area_code == target_local_code)
            )

            if not is_match:
                continue

            daily_data = {}
            def get_bucket(d_str):
                if d_str not in daily_data:
                    daily_data[d_str] = {"weather": [], "pops": [], "temps": []}
                return daily_data[d_str]

            current_weather = None
            current_temp = None
            min_weather_diff = timedelta(days=99)
            min_temp_diff = timedelta(days=99)

            # 天気
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

            # 降水確率
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

            # 気温
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

            # 1エリア分のテキスト構築
            lines = []
            sub_info = []
            if current_temp:
                sub_info.append(f"🌡**{current_temp}**")
            if current_weather:
                sub_info.append(current_weather)
            
            sub_text = " ".join(sub_info) if sub_info else ""
            lines.append(f"🗺️ **{area_name}** {sub_text}")
            lines.append(f"_発表: {pub_office}_")
            lines.append("-----------------------------------")

            labels = ["今日", "明日", "明後日"]
            sorted_dates = sorted([d for d in daily_data.keys() if daily_data[d]["weather"] or daily_data[d]["temps"] or daily_data[d]["pops"]])

            for idx, d_str in enumerate(sorted_dates[:3]):
                info = daily_data[d_str]
                day_label = labels[idx] if idx < len(labels) else d_str

                lines.append(f"📅 **{day_label} ({d_str})**")
                if info["weather"]:
                    lines.append(f"  天候🌦: {' / '.join(info['weather'])}")
                if info["temps"]:
                    lines.append(f"  気温🌡: {' '.join(info['temps'])}")
                if info["pops"]:
                    lines.append(f"  降水確率☔: {' '.join(info['pops'])}")
                lines.append("")

            matched_blocks.append("\n".join(lines).strip())

    return matched_blocks

def get_weather_text(json_path, codemaster_dir, target_region):
    """
    複数件ヒットした場合にすべてまとめて一覧（区切り線挟み）で返す関数
    """
    if not os.path.exists(json_path):
        return "天気データファイルが見つかりませんでした。"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"天気データの読み込みに失敗しました: {e}"

    city_to_local, local_name_map = load_area_hierarchy(codemaster_dir)

    target_local_code = city_to_local.get(target_region)
    target_local_name = local_name_map.get(target_local_code, "") if target_local_code else ""

    offices = data.get("offices", {})
    all_matched_blocks = []

    # 全オフィス・全レポートを走査して、マッチするエリアをすべて回収する
    for office_code, office_info in offices.items():
        pub_office = office_info.get("officeName", "")
        for report in office_info.get("reports", []):
            if "publishingOffice" in report:
                pub_office = report.get("publishingOffice")
            
            blocks = parse_area_forecasts(report, target_region, target_local_name, target_local_code, pub_office)
            for b in blocks:
                if b not in all_matched_blocks:
                    all_matched_blocks.append(b)

    # 万が一通常ヒットしない場合のキーワードフォールバック（広域オフィス名一致）
    if not all_matched_blocks:
        keywords = ["十勝", "帯広", "釧路", "東京", "札幌"]
        if any(kw in target_region for kw in keywords):
            for office_code, office_info in offices.items():
                office_name = office_info.get("officeName", "")
                if target_region in office_name or any(kw in office_name for kw in keywords if kw in target_region):
                    for report in office_info.get("reports", []):
                        pub_office = report.get("publishingOffice", office_name)
                        blocks = parse_area_forecasts(report, target_region, target_local_name, target_local_code, pub_office)
                        for b in blocks:
                            if b not in all_matched_blocks:
                                all_matched_blocks.append(b)

    if not all_matched_blocks:
        return f"「{target_region}」に該当する天気予報データが見つかりませんでした。"

    # 複数件ヒットしたものを区切り線で繋げて返す
    result_text = "\n\n".join(all_matched_blocks)
    result_text += "\n-----------------------------------\n（出典: 気象庁）"

    return result_text