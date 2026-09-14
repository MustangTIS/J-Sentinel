import requests
import json
import os
import time
import re
import unicodedata

# --- 1. テキスト切り詰めの共通ヘルパー (文字数 & 行数) ---
def truncate_text(text, max_chars=500, max_lines=15, web_url=None):
    """
    指定された文字数または行数でテキストを安全にカットし、
    カットされた場合は Web 案内メッセージを付与する
    """
    lines = text.splitlines()
    is_truncated = False
    
    # A. 行数制限のチェック
    if len(lines) > max_lines:
        text = "\n".join(lines[:max_lines])
        is_truncated = True

    # B. 文字数制限のチェック
    if len(text) > max_chars:
        text = text[:max_chars]
        is_truncated = True

    # 切り上げが発生した場合のフッター処理
    if is_truncated:
        text = text.rstrip() + "\n\n... (以降省略)"
        # 本文中にまだ web_url が入っていない場合のみ案内を追加
        if web_url and (web_url not in text):
            text += f"\n👉 全文を確認: {web_url}"
            
    return text

# --- 2. Bluesky用 Facet (リンク化) 自動生成ヘルパー ---
def build_bluesky_facets(text):
    facets = []
    url_regex = r'https?://[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|/))'
    
    for match in re.finditer(url_regex, text):
        url = match.group(0)
        # match.start()/end() の文字インデックスから正確なUTF-8バイト位置を算出 (重複URL対応)
        start_byte = len(text[:match.start()].encode('utf-8'))
        end_byte = len(text[:match.end()].encode('utf-8'))
        
        facets.append({
            "index": {
                "byteStart": start_byte,
                "byteEnd": end_byte
            },
            "features": [{
                "$type": "app.bsky.richtext.facet#link",
                "uri": url
            }]
        })
    return facets

# --- 3. ペイロード構築ロジック ---
def build_payload(style, title, description, color, bot_name, current_version, timestamp, web_url=None, is_short=False):
    bold_title = f"📢 **{title}**"
    style_lower = style.lower()
    
    # 【変更点】特定サービスの強制短縮を排除！
    # 明示的に is_short が True か、style 名に _short / _compact がついている場合のみ短縮する
    should_truncate = (
        is_short or 
        ("_short" in style_lower) or 
        ("_compact" in style_lower)
    )
    
    # テキスト加工 (短縮版なら 500文字 / 15行 で切り上げ)
    if should_truncate:
        target_desc = truncate_text(description, max_chars=500, max_lines=15, web_url=web_url)
    else:
        target_desc = description

    # フル版用の末尾URL (すでに本文内に同じURLが含まれていない場合のみ付与)
    url_footer = ""
    if web_url and not should_truncate:
        if web_url not in target_desc:
            url_footer = f"\n詳細: {web_url}"

    # A. Discord Simple
    if "dissimple" in style_lower:
        full_text = f"{bold_title} / 送信時 {timestamp}\n{target_desc}{url_footer}"
        safe_content = full_text[:1900].strip()
        return {"content": safe_content, "username": bot_name}

    # B. Discord Embed
    elif "disembed" in style_lower:
        embed_desc = f"{target_desc}{url_footer}"
        safe_desc = embed_desc[:3500] if len(embed_desc) > 3500 else embed_desc

        embed_obj = {
            "title": f"📢 {title}",
            "description": f"送信時 {timestamp}\n\n{safe_desc}",
            "color": color,
            "image": {"url": "attachment://image.png"},
            "footer": {"text": f"J-Sentinel ~ 高度防災システム v{current_version}"}
        }
        if web_url:
            embed_obj["url"] = web_url

        return {
            "username": bot_name,
            "embeds": [embed_obj]
        }

    # C. Slack
    elif "slack" in style_lower:
        body = f"{bold_title} / 送信時 {timestamp}\n{target_desc}{url_footer}\n───────────"
        return {"text": body, "username": bot_name}

    # D. Matrix
    elif "matrix" in style_lower:
        body = f"{bold_title} / 送信時 {timestamp}\n{target_desc}{url_footer}\n───────────"
        return {"msgtype": "m.text", "body": body}

    # E. Bluesky (※プロトコル仕様の300バイト制限枠内へ収める処理)
    elif "bluesky" in style_lower:
        header = f"📢 {title}"
        
        # リンク用URLの処理（web_urlが存在し、まだ本文に含まれていない場合）
        link_str = ""
        if web_url and (web_url not in target_desc):
            link_str = f"\n🔗 {web_url}"
            
        timestamp_str = f"\n({timestamp} 送信)"
        
        # 固定パーツ（ヘッダー、タイムスタンプ、URL）のバイト数を正確に計算
        # 余白の改行なども含めて計算する
        fixed_parts = f"{header}\n\n{link_str}{timestamp_str}"
        fixed_bytes = len(fixed_parts.encode('utf-8'))
        
        # Blueskyの上限（300バイト）から固定パーツ分を引いた残りを本文に割り当てる
        # 安全のため少しマージン（5バイト程度）を引いておく
        max_desc_bytes = 295 - fixed_bytes
        
        clean_desc = target_desc.strip()
        encoded_desc = clean_desc.encode('utf-8')
        
        if len(encoded_desc) > max_desc_bytes and max_desc_bytes > 0:
            # 枠内に収まるようにスライス
            short_desc = (
                encoded_desc[: max_desc_bytes - 3]
                .decode('utf-8', errors='ignore')
                + "..."
            )
        elif max_desc_bytes <= 0:
            # 万が一固定文言だけでいっぱいのときのフォールバック
            short_desc = "..."
        else:
            short_desc = clean_desc

        # 最終的なテキストの組み立て
        full_text = f"{header}\n\n{short_desc}"
        if link_str:
            full_text += f"{link_str}"
        full_text += f"{timestamp_str}"

        return {"text": full_text, "facets": build_bluesky_facets(full_text)}

# --- 4. 各送信実務 ---

def send_to_discord(payload, image_path, url):
    try:
        if "embeds" in payload and image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                response = requests.post(
                    url, 
                    data={"payload_json": json.dumps(payload)}, 
                    files={"file": ("image.png", f, "image/png")}, 
                    timeout=10
                )
        else:
            response = requests.post(url, json=payload, timeout=5)
        return response
    except Exception as e:
        return e

def send_to_slack(payload, url):
    try:
        return requests.post(url, json=payload, timeout=5)
    except Exception as e:
        return e

def send_to_matrix(payload, url, token, room_id):
    try:
        txid = int(time.time() * 1000)
        base_url = url.rstrip('/')
        api_url = f"{base_url}/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txid}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        return requests.put(api_url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        return e

def send_to_bluesky(payload, handle, password, image_path=None, pds_url="https://bsky.social"):
    try:
        session_res = requests.post(
            f"{pds_url}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password}, timeout=10
        )
        session_res.raise_for_status()
        session = session_res.json()
        headers = {"Authorization": f"Bearer {session['accessJwt']}"}

        embed = None
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_data = f.read()
            
            blob_res = requests.post(
                f"{pds_url}/xrpc/com.atproto.repo.uploadBlob",
                headers={**headers, "Content-Type": "image/png"},
                data=img_data, timeout=15
            )
            if blob_res.status_code == 200:
                blob = blob_res.json().get("blob")
                embed = {
                    "$type": "app.bsky.embed.images",
                    "images": [{"alt": "Disaster Report Image", "image": blob}]
                }

        record = {
            "$type": "app.bsky.feed.post",
            "text": payload["text"],
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        if payload.get("facets"):
            record["facets"] = payload["facets"]

        if embed:
            record["embed"] = embed

        post_payload = {
            "repo": session["did"],
            "collection": "app.bsky.feed.post",
            "record": record
        }

        res = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord", 
            headers=headers, json=post_payload, timeout=10
        )
        return res
    except Exception as e:
        return e

# --- 5. 司令塔 (ディスパッチャ) ---

def dispatch(style, title, description, color, image_path, url, bot_name, current_version, timestamp, 
             matrix_token=None, matrix_room=None, shared_image_url=None, web_url=None,
             handle=None, password=None, is_short=False, mode=None, **kwargs):
    
    actual_handle = handle or kwargs.get("bsky_handle")
    actual_password = password or kwargs.get("bsky_pass")
    
    # 判定の優先順位: 
    # 1. mode="limit" が明示されているか
    # 2. is_short / short 引数が True か
    mode_val = (mode or kwargs.get("mode", "")).lower()
    short_flag = (mode_val == "limit") or is_short or kwargs.get("short", False) or kwargs.get("is_short", False)
    
    style_key = style.lower()

    current_description = description
    if ("slack" in style_key or "matrix" in style_key) and shared_image_url:
        current_description += f"\n画像: {shared_image_url}"

    payload = build_payload(
        style_key, title, current_description, color, bot_name, current_version, timestamp, 
        web_url=web_url, is_short=short_flag
    )

    if "disembed" in style_key or "dissimple" in style_key:
        return send_to_discord(payload, image_path, url)

    elif "slack" in style_key:
        return send_to_slack(payload, url)

    elif "matrix" in style_key:
        if not matrix_token or not matrix_room:
            return Exception("Matrix: TokenまたはRoom IDが設定されていません")
        return send_to_matrix(payload, url, matrix_token, matrix_room)

    elif "bluesky" in style_key:
        if not actual_handle or not actual_password: 
            return Exception("Bluesky: HandleまたはApp Passwordが設定されていません")
        
        pds = url if (url and url.startswith("http")) else "https://bsky.social"
        return send_to_bluesky(payload, actual_handle, actual_password, image_path, pds)

    return Exception(f"未対応の送信スタイル: {style}")