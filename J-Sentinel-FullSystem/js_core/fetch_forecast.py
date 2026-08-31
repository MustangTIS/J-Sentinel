from datetime import datetime
import json
from pathlib import Path
import csv
import requests

# 基準ディレクトリとURLの設定
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"

def load_office_codes_from_csv(base_dir: Path):
    """
    codemaster フォルダ内の areakisyou.csv / areakisyou2.csv から
    気象庁の天気予報オフィスコード（通常6桁）を動的に抽出する
    """
    office_codes = {}
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
                                if len(code) == 6:
                                    office_codes[code] = name
                print(f"[INFO] {target_csv.name} からオフィスコードを読み込みました（抽出件数: {len(office_codes)}件）")
            except Exception as e:
                print(f"[WARN] {target_csv.name} の読み込みに失敗しました: {e}")
        else:
            print(f"[WARN] codemaster/{filename} が見つかりません。")

    return office_codes

def load_weather_code_map(base_dir: Path):
    """codemaster フォルダやデータベース内から weather.csv を読み込んで辞書化する（列名非依存の堅牢版）"""
    weather_dict = {}
    csv_filenames = ["weather.csv"]
    
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
            for enc in ["cp932", "utf-8", "utf-8-sig"]:
                try:
                    temp_dict = {}
                    with open(target_csv, mode="r", encoding=enc, errors="ignore") as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if not row or len(row) < 2:
                                continue
                            
                            c_candidate = row[0].strip()
                            w_candidate = row[1].strip()
                            
                            # ヘッダー行らしき文字列（「天気コード」や「code」など）はスキップ
                            low_c = c_candidate.lower()
                            if "code" in low_c or "天気" in low_c or "コード" in low_c:
                                continue
                                
                            if c_candidate and w_candidate:
                                temp_dict[c_candidate] = w_candidate
                                
                    if temp_dict:
                        weather_dict = temp_dict
                        print(f"[INFO] {target_csv.name} から天気コードマスターを読み込みました（エンコーディング: {enc}, 件数: {len(weather_dict)}件）")
                        break
                except Exception as e:
                    continue
            
            if weather_dict:
                break
            else:
                print(f"[WARN] {target_csv.name} の中身をうまくパースできませんでした。")
        else:
            print(f"[WARN] codemaster/{filename} が見つかりません。")
                
    return weather_dict

def convert_and_save_weather_rt(all_forecast_data, office_codes_map, weather_code_map, base_dir: Path):
    """取得した各オフィスの天気予報データをパースし、天気名称付きの WeatherRT.json にまとめて保存する"""
    formatted_offices = {}

    for office_code, forecast_list in all_forecast_data.items():
        office_name = office_codes_map.get(office_code, office_code)
        office_reports = []

        for report in forecast_list:
            publishing_office = report.get("publishingOffice")
            report_datetime = report.get("reportDatetime")
            time_series = report.get("timeSeries", [])
            
            # 各時系列ブロック（timeSeries）を走査して weatherTexts を埋め込む
            for ts in time_series:
                for area_data in ts.get("areas", []):
                    if "weatherCodes" in area_data:
                        weather_texts = [
                            weather_code_map.get(code, f"不明({code})") 
                            for code in area_data["weatherCodes"]
                        ]
                        area_data["weatherTexts"] = weather_texts

            office_reports.append({
                "publishingOffice": publishing_office,
                "reportDatetime": report_datetime,
                "timeSeries": time_series
            })

        formatted_offices[office_code] = {
            "officeName": office_name,
            "reports": office_reports
        }

    rt_data = {
        "updated_at": datetime.now().isoformat(),
        "offices": formatted_offices
    }
    
    convert_dir = DATABASE_DIR / "weather" / "convert"
    convert_dir.mkdir(parents=True, exist_ok=True)
    rt_file = convert_dir / "WeatherRT.json"
    
    rt_file.write_text(json.dumps(rt_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] 天気予報リアルタイムデータを更新しました -> weather/convert/{rt_file.name}")


def fetch_and_store_forecast():
    print("[INFO] 天気予報データ (forecast) の取得を開始...")

    base_store_dir = DATABASE_DIR / "weather" / "base"
    base_store_dir.mkdir(parents=True, exist_ok=True)

    # CSVからオフィスコード一覧と天気コードマスターを動的に取得
    office_codes_map = load_office_codes_from_csv(BASE_DIR)
    weather_code_map = load_weather_code_map(BASE_DIR)
    
    if not office_codes_map:
        print("[ERROR] CSVからオフィスコードをロードできませんでした。処理を中止します。")
        return

    all_forecast_data = {}

    for office_code in office_codes_map.keys():
        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{office_code}.json"
        latest_file = base_store_dir / f"{office_code}_latest.json"
        prev_file = base_store_dir / f"{office_code}_previous.json"

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            new_data = response.json()

            if latest_file.exists():
                content_old = latest_file.read_text(encoding="utf-8")
                prev_file.write_text(content_old, encoding="utf-8")

            latest_file.write_text(
                json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            
            all_forecast_data[office_code] = new_data

        except Exception as e:
            # 存在しないオフィスコードやネットワークエラー時はキャッシュからフォールバック
            if latest_file.exists():
                try:
                    all_forecast_data[office_code] = json.loads(latest_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

    if all_forecast_data:
        convert_and_save_weather_rt(all_forecast_data, office_codes_map, weather_code_map, BASE_DIR)
        print(f"[INFO] 合計 {len(all_forecast_data)} 件のオフィス予報データを処理しました。")
    else:
        print("[ERROR] 有効な天気予報データが1件も取得できませんでした。")

if __name__ == "__main__":
    fetch_and_store_forecast()