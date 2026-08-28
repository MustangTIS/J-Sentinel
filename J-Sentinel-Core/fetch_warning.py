from datetime import datetime
import json
from pathlib import Path
import csv
import requests

# 基準ディレクトリとURLの設定
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
WARNING_MAP_URL = "https://www.jma.go.jp/bosai/warning/data/warning/map.json"

def load_dictionaries(base_dir: Path):
    """codemaster フォルダ内の areakisyou.csv から辞書を作成する"""
    area_dict = {}
    
    # codemaster 内のパスを最優先で候補に追加
    candidate_paths = [
        base_dir / "codemaster" / "areakisyou.csv",
        base_dir / "areakisyou.csv",
        base_dir / "database" / "areakisyou.csv",
        Path("codemaster/areakisyou.csv"),
    ]
    
    area_csv = None
    for path in candidate_paths:
        if path.exists():
            area_csv = path
            break
            
    if area_csv and area_csv.exists():
        try:
            with open(area_csv, mode="r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.reader(f)
                for idx, row in enumerate(reader):
                    if idx < 2:
                        continue
                    if len(row) > 1:
                        code = row[0].strip()
                        name = row[1].strip()
                        if code and name and code != "nan" and name != "nan":
                            area_dict[code] = name
                            if len(code) == 7 and code.endswith("0"):
                                area_dict[code[:-1]] = name
            print(f"[INFO] areakisyou.csv を読み込みました（登録件数: {len(area_dict)}件）: {area_csv.name}")
        except Exception as e:
            print(f"[WARN] areakisyou.csv の読み込みに失敗しました: {e}")
    else:
        print("[WARN] codemaster/areakisyou.csv が見つかりません。")

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
                for row in reader:
                    if len(row) >= 2 and row[0].strip():
                        keiho_dict[str(row[0]).strip()] = row[1].strip()
            print(f"[INFO] keiho.csv を読み込みました（登録件数: {len(keiho_dict)}件）: {keiho_csv.name}")
        except Exception as e:
            print(f"[WARN] keiho.csv の読み込みに失敗しました: {e}")

    return area_dict, keiho_dict

def convert_and_save_warning_rt(new_data, base_dir: Path):
    """取得した map.json のコードに辞書を当てて、名称付きの WarningRT.json に整形・保存する"""
    area_dict, keiho_dict = load_dictionaries(base_dir)
    
    converted_reports = []
    
    for report in new_data:
        report_time = report.get("reportDatetime")
        area_types_list = []
        
        for area_type in report.get("areaTypes", []):
            areas_list = []
            for area in area_type.get("areas", []):
                area_code = area.get("code")
                
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
                for warn in area.get("warnings", []):
                    warn_code = warn.get("code")
                    warn_name = keiho_dict.get(warn_code, warn_code)
                    status = warn.get("status")
                    
                    warnings_list.append({
                        "code": warn_code,
                        "name": warn_name,
                        "status": status
                    })
                
                areas_list.append({
                    "code": area_code,
                    "name": area_name,
                    "warnings": warnings_list
                })
            
            area_types_list.append({
                "areas": areas_list
            })
            
        converted_reports.append({
            "reportDatetime": report_time,
            "areaTypes": area_types_list
        })

    rt_data = {
        "updated_at": datetime.now().isoformat(),
        "reports": converted_reports
    }
    
    # 仕様書に合わせた保存先: database/keiho/convert/WarningRT.json
    convert_dir = DATABASE_DIR / "keiho" / "convert"
    convert_dir.mkdir(parents=True, exist_ok=True)
    rt_file = convert_dir / "WarningRT.json"
    
    rt_file.write_text(json.dumps(rt_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] 名称変換済みのリアルタイムデータを更新しました -> keiho/convert/{rt_file.name}")

def fetch_and_store_warning_map():
    print("[INFO] 警報マップデータ (map.json) の取得を開始...")

    # 仕様書に合わせた保存先: database/keiho/base
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