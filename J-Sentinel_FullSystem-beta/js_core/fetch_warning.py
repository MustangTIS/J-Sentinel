from datetime import datetime
import json
from pathlib import Path
import csv
import requests

# 基準ディレクトリとURLの設定
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
WARNING_MAP_URL = "https://www.jma.go.jp/bosai/warning/data/r8/map.json"

def load_dictionaries(base_dir: Path):
    """codemaster フォルダ内の areakisyou.csv および areakisyou2.csv から辞書を作成する"""
    area_dict = {}
    
    # 読み込むCSVファイルのリスト（areakisyou と areakisyou2）
    csv_filenames = ["areakisyou.csv", "areakisyou2.csv"]
    
    for filename in csv_filenames:
        candidate_paths = [
            base_dir / "codemaster" / filename,
            base_dir / filename,
            base_dir / "database" / filename,
            Path(f"codemaster/{filename}"),
        ]
        
        target_csv = None
        for path in candidate_paths:
            if path.exists():
                target_csv = path
                break
                
        if target_csv and target_csv.exists():
            try:
                with open(target_csv, mode="r", encoding="utf-8-sig", errors="ignore") as f:
                    reader = csv.reader(f)
                    for idx, row in enumerate(reader):
                        if idx < 2:  # ヘッダー行などをスキップ
                            continue
                        if len(row) > 1:
                            code = row[0].strip()
                            name = row[1].strip()
                            if code and name and code != "nan" and name != "nan":
                                area_dict[code] = name
                                if len(code) == 7 and code.endswith("0"):
                                    area_dict[code[:-1]] = name
                print(f"[INFO] {target_csv.name} を読み込みました（累計登録件数: {len(area_dict)}件）")
            except Exception as e:
                print(f"[WARN] {target_csv.name} の読み込みに失敗しました: {e}")
        else:
            print(f"[WARN] codemaster/{filename} が見つかりません。")

    # keiho.csv の読み込み
    keiho_dict = {}
    keiho_csv_candidates = [
        base_dir / "codemaster" / "keiho.csv",
        DATABASE_DIR / "codemaster" / "keiho.csv",
        Path("codemaster/keiho.csv"),
    ]
    
    keiho_csv = None
    for path in keiho_csv_candidates:
        if path.exists():
            keiho_csv = path
            break

    if keiho_csv and keiho_csv.exists():
        try:
            with open(keiho_csv, mode="r", encoding="cp932", errors="ignore") as f:
                reader = csv.reader(f)
                next(reader, None)
                # keiho.csv 読み込み部分をこうしておくと安心です
                for row in reader:
                    if len(row) >= 2 and row[0].strip():
                        # キー側を2桁のゼロ埋め（"3" → "03"）に統一する
                        raw_code = row[0].strip()
                        code_key = raw_code.zfill(2) if raw_code.isdigit() else raw_code
                        keiho_dict[code_key] = row[1].strip()
            print(f"[INFO] keiho.csv を読み込みました（登録件数: {len(keiho_dict)}件）: {keiho_csv.name}")
        except Exception as e:
            print(f"[WARN] keiho.csv の読み込みに失敗しました: {e}")

    return area_dict, keiho_dict

def convert_and_save_warning_rt(new_data, base_dir: Path):
    """取得した map.json の構造を解析し、名称付きの WarningRT.json に整形・保存する"""
    area_dict, keiho_dict = load_dictionaries(base_dir)
    
    converted_reports = []
    reports = new_data if isinstance(new_data, list) else [new_data]
    
    # 新旧すべてのJSON構造（キーがエリアコードになっているパターンや areaCode / code を持つパターン）を再帰的に網羅探索する関数
    def extract_areas(obj):
        found = []
        if isinstance(obj, dict):
            # 1. キー自体がエリアコード（例: "0110000": { ... }）であるケースの判定
            # コードらしい数字のみのキーかつ、値の中に warnings, kinds, areaCode などの要素がある場合
            for k, v in obj.items():
                if isinstance(v, dict) and k.isdigit() and (len(k) == 6 or len(k) == 5 or len(k) == 2 or len(k) == 7):
                    if "warnings" in v or "kinds" in v or "areaCode" in v or any(sub_k.isdigit() for sub_k in v.keys()):
                        # このキー自体をコードとして扱う
                        v_copy = v.copy()
                        if "code" not in v_copy:
                            v_copy["code"] = k
                        found.append(v_copy)
                
                # 通常の再帰探索
                found.extend(extract_areas(v))
                
            # 2. オブジェクト内に直接 code または areaCode が明記されているケース
            area_code = obj.get("code") or obj.get("areaCode")
            warn_sources = obj.get("warnings") or obj.get("kinds")
            if area_code and warn_sources and isinstance(warn_sources, list):
                found.append(obj)
                
        elif isinstance(obj, list):
            for item in obj:
                found.extend(extract_areas(item))
        return found

    for report in reports:
        report_time = report.get("reportDatetime")
        notice_text = report.get("notice")  # ← ①ここで取得する
        area_types_list = []
        
        # レポート内からエリア情報をすべて抽出
        raw_areas = extract_areas(report)
        areas_list = []
        
        seen_codes = set()
        for area in raw_areas:
            area_code = area.get("code") or area.get("areaCode")
            if not area_code or not isinstance(area_code, str):
                continue
            
            # 重複回避
            if area_code in seen_codes:
                continue
            seen_codes.add(area_code)
            
            # 辞書から名称を引く
            area_name = area_dict.get(area_code)
            if not area_name:
                matching_key_padded = area_code + "0"
                area_name = area_dict.get(matching_key_padded)
            if not area_name and len(area_code) == 7:
                area_name = area_dict.get(area_code[:-1])
            if not area_name:
                area_name = area_code
            
            warnings_list = []
            warn_sources = area.get("warnings") or area.get("kinds", [])
                
            for warn in warn_sources:
                if not isinstance(warn, dict):
                    continue
                warn_code = warn.get("code")
                if not warn_code:
                    continue
                    
                warn_name = keiho_dict.get(warn_code, warn_code)
                status = warn.get("status")
                
                warnings_list.append({
                    "code": warn_code,
                    "name": warn_name,
                    "status": status
                })
            
            if warnings_list:
                areas_list.append({
                    "code": area_code,
                    "name": area_name,
                    "warnings": warnings_list
                })
        
        if areas_list:
            area_types_list.append({
                "areas": areas_list
            })
            
        converted_reports.append({
            "reportDatetime": report_time,
            "notice": notice_text,          # ← ここに追加！
            "areaTypes": area_types_list
        })

    rt_data = {
        "updated_at": datetime.now().isoformat(),
        "reports": converted_reports
    }
    
    convert_dir = DATABASE_DIR / "keiho" / "convert"
    convert_dir.mkdir(parents=True, exist_ok=True)
    rt_file = convert_dir / "WarningRT.json"
    
    rt_file.write_text(json.dumps(rt_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] 名称変換済みのリアルタイムデータを更新しました -> keiho/convert/{rt_file.name}")


def fetch_and_store_warning_map():
    print("[INFO] 警報マップデータ (map.json) の取得を開始...")

    target_dir = DATABASE_DIR / "keiho" / "base"
    target_dir.mkdir(parents=True, exist_ok=True)

    latest_file = target_dir / "map_latest.json"
    prev_file = target_dir / "map_previous.json"

    try:
        response = requests.get(WARNING_MAP_URL, timeout=15)
        response.raise_for_status()
        new_data = response.json()

        if latest_file.exists():
            content_old = latest_file.read_text(encoding="utf-8")
            prev_file.write_text(content_old, encoding="utf-8")

        latest_file.write_text(
            json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[SAVED] 警報マップを更新しました -> keiho/base/{latest_file.name}")

        is_changed = True
        if prev_file.exists():
            old_data = json.loads(prev_file.read_text(encoding="utf-8"))
            if old_data == new_data:
                is_changed = False
                print("[INFO] 前回のデータから変更はありません。")
            else:
                print("[INFO] 警報ステータスに変化を検知しました。")

        # WarningRT.json の生成（keiho/convert へ出力）
        convert_and_save_warning_rt(new_data, BASE_DIR)

    except Exception as e:
        print(f"[ERROR] 警報マップの取得・保存に失敗しました: {e}")

if __name__ == "__main__":
    fetch_and_store_warning_map()