import datetime

# 警戒レベルやステータスに応じたEmbedカラーマップ
STATUS_COLOR_MAP = {
    "5": 0xFF0000,  # 避難 / 赤
    "4": 0xE67E22,  # 避難準備 / オレンジ
    "3": 0xE67E22,  # 入山規制 / オレンジ
    "2": 0xF1C40F,  # 火口周辺規制 / 黄
    "1": 0x2ECC71,  # 活火山であることに留意 / 緑
}

def parse_volcano_json(json_data, mode="full"):
    """
    火山情報JSONをパースし、Discord Embed等で利用可能な辞書オブジェクトを返す
    mode: "full" (詳細・防災対応リスト含む) または "limit" (要約・対象地域のみ)
    """
    if not json_data or not isinstance(json_data, dict):
        return None

    # 基本情報の取得
    volcano_name = json_data.get("volcanoName", "不明な火山")
    status = json_data.get("status", "情報なし")
    report_datetime_str = json_data.get("reportDatetime", "")
    target_cities = json_data.get("targetCities", [])
    
    # URLの取得 (フォールバック付き)
    jma_web_url = json_data.get("jma_web_url") or json_data.get("jma_url", "")

    # 日時のフォーマット整形 (Python 3.7+ 互換対応)
    formatted_time = "不明"
    if report_datetime_str:
        try:
            # +09:00 表記を fromisoformat で扱えるよう処理
            clean_time_str = report_datetime_str.replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(clean_time_str)
            formatted_time = dt.strftime("%Y/%m/%d %H:%M")
        except ValueError:
            formatted_time = report_datetime_str

    # カラー判定
    color = 0x3498DB  # デフォルト青
    if "レベル５" in status or "噴火発生" in status or "避難" in status:
        color = 0xFF0000  # 赤
    elif "レベル４" in status or "レベル３" in status or "入山規制" in status or "周辺海域警戒" in status:
        color = 0xE67E22  # オレンジ
    elif "レベル２" in status or "火口周辺規制" in status or "火口周辺危険" in status:
        color = 0xF1C40F  # 黄
    elif "レベル１" in status or "留意" in status or "解除" in status:
        color = 0x2ECC71  # 緑

    # 本文（description）の構築
    lines = [
        f"発表時刻：{formatted_time}",
        f"対象火山：{volcano_name}",
        f"現在の状況：{status}",
        "----------------"
    ]

    # rawデータの詳細展開
    raw = json_data.get("raw", {})
    volcano_infos = raw.get("volcanoInfos", [])

    action_summary = []
    for info in volcano_infos:
        info_type = info.get("type", "")
        # 「対象市町村の防災対応」または「対象市町村の防災対応等」に柔軟にマッチ
        if "防災対応" in info_type:
            for item in info.get("items", []):
                item_name = item.get("name", "")
                condition = item.get("condition", "")
                areas = [a.get("name") for a in item.get("areas", []) if a.get("name")]
                
                cond_str = f"（{condition}）" if condition else ""
                if areas:
                    action_summary.append(f"■ {item_name}{cond_str}")
                    action_summary.append(f"  {', '.join(areas)}")

    # mode に応じた記述の展開
    if mode == "full" and action_summary:
        lines.append("【対象市町村の防災対応】")
        lines.extend(action_summary)
        lines.append("----------------")

    # 対象市町村の一覧（mode=="limit" の場合、または防災対応情報がない場合のフォールバック）
    if target_cities and (mode == "limit" or not action_summary):
        lines.append("【対象市町村】")
        lines.append("・" + "、".join(target_cities))
        lines.append("----------------")

    # フッターおよび生URLの付与
    footer = "（出典: 気象庁発表データ）"
    if jma_web_url:
        footer += f"\n{jma_web_url}"
    lines.append(footer)

    full_description = "\n".join(lines)

    # Discord Embed の文字数制限（2000文字）セーフティカット
    if len(full_description) > 1950:
        full_description = full_description[:1900] + "\n...\n(文字数制限のため省略)\n----------------\n" + footer

    return {
        "title": f"【火山噴火警報・予報】{volcano_name}",
        "description": full_description,
        "color": color,
        "url": jma_web_url,
        "volcano_name": volcano_name,
        "status": status
    }