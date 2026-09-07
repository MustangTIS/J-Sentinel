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
    city_to_local = {} 
    local_codes = set()

    city_csv = os.path.join(codemaster_dir, "areakisyou.csv")
    if os.path.exists(city_csv):
        try:
            df = pd.read_csv(city_csv, header=None, encoding="utf-8", encoding_errors="ignore")
            for idx, row in df.iterrows():
                if idx < 2: continue 
                if len(row) >= 5:
                    city_name = str(row.iloc[2]).strip() 
                    city_code = str(row.iloc[0]).strip() 
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

def get_weather_info(json_path, codemaster_dir, target_region):
    """
    指定された地域名に部分一致するすべてのエリアを検出し、
    最大4件までのEmbedリスト＋必要に応じて警告Embedを返却する
    """
    if not os.path.exists(json_path):
        return ["天気データファイルが見つかりませんでした。"]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"天気データの読み込みに失敗しました: {e}"]

    city_to_local, local_name_map = load_area_hierarchy(codemaster_dir)

    target_local_code = city_to_local.get(target_region)
    target_local_name = local_name_map.get(target_local_code, "") if target_local_code else ""

    offices = data.get("offices", {})
    matched_targets = []  # (office_info, area_name, pub_office) のリスト

    # 1. 部分一致するすべてのオフィス・エリアを全収集
    for office_code, office_info in offices.items():
        for report in office_info.get("reports", []):
            pub_office = report.get("publishingOffice", "")
            for ts in report.get("timeSeries", []):
                for area in ts.get("areas", []):
                    area_name = area.get("area", {}).get("name", "")
                    area_code = area.get("area", {}).get("code", "")
                    
                    is_match = (
                        target_region in area_name or 
                        area_name in target_region or 
                        (target_local_name and target_local_name in area_name) or
                        (target_local_code and area_code == target_local_code)
                    )
                    
                    if is_match:
                        # 重複追加を防ぐ
                        target_item = (office_info, area_name, pub_office)
                        if target_item not in matched_targets:
                            matched_targets.append(target_item)

    # 2. フォールバック（主要地名の救済）
    if not matched_targets:
        keywords = ["十勝", "帯広", "釧路", "東京", "札幌"]
        if any(kw in target_region for kw in keywords):
            for office_code, office_info in offices.items():
                office_name = office_info.get("officeName", "")
                if target_region in office_name or any(kw in office_name for kw in keywords if kw in target_region):
                    for report in office_info.get("reports", []):
                        pub_office = report.get("publishingOffice", "")
                        matched_targets.append((office_info, office_name, pub_office))
                    break

    if not matched_targets:
        return [f"「{target_region}」に該当する天気予報データが見つかりませんでした。"]

    now_jst = datetime.now(timezone(timedelta(hours=9)))
    embeds = []
    
    # ヒットした中から最大4件まで処理（5件以上の大暴走を防ぐため）
    display_targets = matched_targets[:4]

    for office_info, matched_area_name, pub_office in display_targets:
        reports = office_info.get("reports", [])
        if not reports:
            continue
        latest_report = reports[0]

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

                is_area_match = (
                    target_region in area_name or 
                    area_name in target_region or 
                    area_name == matched_area_name or
                    (target_local_name and target_local_name in area_name) or
                    (target_local_code and area_code == target_local_code)
                )

                if not is_area_match and len(daily_data) > 0:
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

        # --- Embed の生成 ---
        embed = discord.Embed(color=0x2b5278)

        header_lines = [f"### 🗾 {matched_area_name}"]
        sub_info = []
        if current_temp:
            sub_info.append(f"**🌡{current_temp}**")
        if current_weather:
            sub_info.append(f"{current_weather}")
        
        if sub_info:
            header_lines.append(" ".join(sub_info))
        
        header_lines.append(f"-_発表: {pub_office}_")
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

        embed.set_footer(text="出典: 気象庁")
        embeds.append(embed)

    # 3. 5件以上ヒットしていた場合の「5枚目警告カード」の付与
    if len(matched_targets) > 4:
        warning_embed = discord.Embed(color=0xe67e22) # オレンジ色の警告カラー
        warning_embed.description = (
            f"⚠️ **「{target_region}」の検索結果が多すぎます**\n\n"
            f"他にあと **{len(matched_targets) - 4}箇所** の該当地域があります。\n"
            "チャンネルのスパムを防ぐため表示を制限しています。\n"
            "より具体的な市町村名（例: 下田市 など）を指定して再検索してください。"
        )
        warning_embed.set_footer(text="出典: 気象庁")
        embeds.append(warning_embed)

    return embeds