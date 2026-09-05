import json
import os

def get_warning_info(json_path, target_region):
    """
    WarningRT.json から指定された地域を検索し、
    ・地域自体が存在しない場合は「見つかりませんでした」
    ・地域はあるが有効な警報がない場合は「現在警報はありません」
    ・有効な警報がある場合は解除を除外してレベル別に整理して返す
    """
    if not os.path.exists(json_path):
        return "気象データファイルが見つかりませんでした。"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"気象データの読み込みに失敗しました: {e}"

    reports = data.get("reports", [])
    if not reports:
        return "有効な気象レポートが見つかりませんでした。"

    region_exists = False  # そもそもJSON内に該当地域が存在したかどうかのフラグ
    matched_areas = {}

    for report in reports:
        report_time = report.get("reportDatetime", "")
        notice_text = report.get("notice", None)
        
        for area_type in report.get("areaTypes", []):
            for area in area_type.get("areas", []):
                area_name = area.get("name", "")
                
                if target_region in area_name:
                    if "気象台" in area_name or "測候所" in area_name:
                        continue
                    
                    # 少なくとも組織名以外で部分一致するエリアが存在した！
                    region_exists = True
                        
                    area_warnings = area.get("warnings", [])
                    active_warnings = [w for w in area_warnings if w.get("status") != "解除"]
                    
                    if active_warnings:
                        if area_name not in matched_areas:
                            matched_areas[area_name] = {
                                "report_time": report_time,
                                "notice": notice_text,
                                "warnings": []
                            }
                        
                        if report_time >= matched_areas[area_name]["report_time"]:
                            matched_areas[area_name]["report_time"] = report_time
                            if notice_text:
                                matched_areas[area_name]["notice"] = notice_text
                        
                        for w in active_warnings:
                            if w not in matched_areas[area_name]["warnings"]:
                                matched_areas[area_name]["warnings"].append(w)

    # 1. そもそもJSON内に該当する地域名が一切存在しなかった場合（誤字や存在しないワード）
    if not region_exists:
        return f"「{target_region}」に該当する警報・注意報データは見つかりませんでした。"

    output_lines = [f"【{target_region} の気象警報・注意報】"]

    # 2. 地域は存在するが、有効な（解除されていない）警報・注意報が現在出ていない場合
    if not matched_areas:
        output_lines.append("\n・ 現在発表されている警報・注意報はありません。")
    else:
        # 3. 有効な警報・注意報がある場合
        for area_name, info in matched_areas.items():
            output_lines.append(f"\n■ 対象地域: {area_name} （発表日時: {info['report_time']}）")
            
            if info.get("notice"):
                output_lines.append(f"⚠️ お知らせ: {info['notice']}")
                
            warnings = info["warnings"]
            level_groups = {}
            for w in warnings:
                w_name = w.get("name", "不明")
                kikenlv = w.get("kikenlv", 2)
                line = f"・ {w_name}"
                
                if kikenlv not in level_groups:
                    level_groups[kikenlv] = []
                if line not in level_groups[kikenlv]:
                    level_groups[kikenlv].append(line)
            
            for lv in sorted(level_groups.keys(), reverse=True):
                lines = level_groups[lv]
                if lines:
                    output_lines.append(f"  ＜レベル{lv}＞")
                    output_lines.extend([f"  {l}" for l in lines])

    output_lines.append("\n（出典: 気象庁）")
    
    result_text = "\n".join(output_lines)

    if len(result_text) > 1900:
        return f"⚠️ 「{target_region}」の情報はデータ量が多すぎるため送信できません。より細かい地域を指定してください。"

    return result_text