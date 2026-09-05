import json
import os

def get_warning_info(json_path, target_region):
    """
    WarningRT.json から指定された地域の最新かつ有効な警報・注意報を検索し、
    解除情報を除外、重複をまとめて「レベル○」形式で整理してテキストで返す
    """
    if not os.path.exists(json_path):
        return "気象データファイルが見つかりませんでした。"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"気象データの読み込みに失敗しました: {e}"

    reports = data.get("reports", [])
    
    all_valid_warnings = []
    latest_report_time = ""
    latest_notice = None
    matched_area_name = target_region  # 正確なエリア名を保持用
    
    for report in reports:
        report_time = report.get("reportDatetime", "")
        notice_text = report.get("notice", None)
        
        for area_type in report.get("areaTypes", []):
            for area in area_type.get("areas", []):
                area_name = area.get("name", "")
                
                if target_region in area_name:
                    area_warnings = area.get("warnings", [])
                    active_warnings = [w for w in area_warnings if w.get("status") != "解除"]
                    
                    if active_warnings:
                        if not latest_report_time or report_time > latest_report_time:
                            latest_report_time = report_time
                            matched_area_name = area_name  # JSONから取れた正式な地域名を採用
                        if notice_text:
                            latest_notice = notice_text
                            
                        for w in active_warnings:
                            if w not in all_valid_warnings:
                                all_valid_warnings.append(w)

    output_lines = [f"【{target_region} の気象警報・注意報】"]
    
    if latest_report_time:
        # 余計な「北海道」のハードコードを外し、取得した地域名をそのまま使う
        output_lines.append(f"\n■ 対象地域: {matched_area_name} （発表日時: {latest_report_time}）")
    else:
        fallback_time = reports[0].get("reportDatetime", "") if reports else ""
        output_lines.append(f"\n■ 対象地域: {target_region} （確認日時: {fallback_time}）")

    if latest_notice:
        output_lines.append(f"⚠️ お知らせ: {latest_notice}")

    if all_valid_warnings:
        level_groups = {}
        
        for w in all_valid_warnings:
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
    else:
        output_lines.append("・ 現在発表されている警報・注意報はありません。")

    return "\n".join(output_lines)