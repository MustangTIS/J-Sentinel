# info_parser.py

def parse_info_json(data, mode="full"):
    """
    気象庁などのJSON (info系) から必要最小限の情報を抽出する
    mode: "full" (全文) または "limit" (概要のみ)
    """
    # detail配下から取得（存在しない場合は最上位を参照するフォールバック付き）
    detail = data.get("detail") or data

    control_title = detail.get("controlTitle", "気象情報")
    head_title = detail.get("headTitle", "防災気象情報")
    headline = detail.get("headlineText", "").strip()
    comment_text = detail.get("commentText", "").replace("<br>", "\n").strip()

    # URLの取得（最上位階層から参照）
    jma_web_url = data.get("jma_web_url") or data.get("jma_url", "")

    # タイトル
    title = f"【{control_title}】{head_title}"

    # 本文の組み立て
    description_parts = []
    
    if headline:
        description_parts.append(f"【概要】\n{headline}")

    # mode が "full" の場合のみ【詳細】を含める
    if mode == "full" and comment_text:
        description_parts.append(f"【詳細】\n{comment_text}")

    # 出典およびURLの付与
    footer = "（出典: 気象庁発表データ）"
    if jma_web_url:
        footer += f"\n{jma_web_url}"
    description_parts.append(footer)

    description = "\n\n".join(description_parts)

    # カラー判定 (Discord Embed等用)
    color = 0x3498DB  # デフォルト: 青
    
    if "特別警報" in head_title or "特別警報" in control_title:
        color = 0xFF0000  # 赤
    elif "熱中症" in head_title or "熱中症" in control_title:
        color = 0xE67E22  # オレンジ
    elif "警報" in head_title or "台風" in head_title:
        color = 0xF1C40F  # 黄色 / 橙色

    return {
        "title": title,
        "description": description,
        "color": color,
        "url": jma_web_url  # 必要に応じてEmbedのリンク用等にも使えるよう返却値に保持
    }