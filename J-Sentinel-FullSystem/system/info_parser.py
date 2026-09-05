def parse_info_json(data):
    """
    気象庁などのJSONから必要最小限のプレーンな情報を抽出する
    """
    control_title = data.get("controlTitle", "気象情報")
    head_title = data.get("headTitle", "防災気象情報")
    headline = data.get("headlineText", "")
    comment_text = data.get("commentText", "").replace("<br>", "\n")
    
    # タイトル（必要に応じてここで「(気象庁発表)」などを添えることも可能）
    title = f"【{control_title}】{head_title}"
    
    # 本文（概要と詳細の結合）
    description_parts = []
    if headline:
        description_parts.append(f"【概要】\n{headline}")
    if comment_text:
        description_parts.append(f"【詳細】\n{comment_text}")
    
    # 💡 クレジット（出典明記）の追加
    description_parts.append("（出典: 気象庁発表データ）")
    
    description = "\n\n".join(description_parts)

    # カラー判定
    color = 0x3498DB
    if "特別警報" in head_title:
        color = 0xFF0000
    elif "警報" in head_title or "台風" in head_title:
        color = 0xE67E22

    return {
        "title": title,
        "description": description,
        "color": color
    }