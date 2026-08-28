#warning_parser.py
import json
import os

def get_warning_info(json_path, target_region):
    """
    WarningRT.json の階層構造を正確に辿って、指定された地域（例: 帯広市）の
    警報・注意報状況を検索してテキストで返す
    """
    if not os.path.exists(json_path):
        return "気象データファイルが見つかりませんでした。"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"気象データの読み込みに失敗しました: {e}"

    matched_areas = []

    # JSONの階層構造（reports -> areaTypes -> areas）を正確にループして探す
    reports = data.get("reports", [])
    for report in reports:
        report_time = report.get("reportDatetime", "")
        for area_type in report.get("areaTypes", []):
            for area in area_type.get("areas", []):
                area_name = area.get("name", "")
                # 部分一致（例：「帯広市」と「帯広」のどちらで指定されてもヒットするように）
                if target_region in area_name:
                    matched_areas.append({
                        "report_time": report_time,
                        "area_name": area_name,
                        "warnings": area.get("warnings", [])
                    })

    if not matched_areas:
        return f"「{target_region}」に該当する警報・注意報データは見つかりませんでした。"

    # ヒットしたデータをチャット用のテキストに整形
    output_lines = [f"【{target_region} の気象警報・注意報】"]
    
    for item in matched_areas:
        output_lines.append(f"\n■ 対象地域: {item['area_name']} （発表日時: {item['report_time']}）")
        warnings = item["warnings"]
        if warnings:
            for w in warnings:
                w_name = w.get("name", "不明")
                w_status = w.get("status", "不明")
                output_lines.append(f"・ {w_name}: {w_status}")
        else:
            output_lines.append("・ 現在発表されている警報・注意報はありません。")

    return "\n".join(output_lines)