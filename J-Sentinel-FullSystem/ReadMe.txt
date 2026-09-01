======================================================================
 J-Sentinel ～ 高度防災システム (Full System Edition) v0.30.5
======================================================================

【概要】
J-Sentinel は、気象庁が公開する公式オープンデータ（地震、津波、気象警報、
防災情報など）を定期ポーリングによってローカルストレージへインジェストし、
Discord、Slack、Matrix、Bluesky などのマルチプラットフォームへ自動配信、
および Discord / Matrix ボットによる対話型の気象・警報・天気情報照会を
行うための高度なスタンドアロン型防災システムです。


【ディレクトリ構造 & 主要ファイル】
\J-Sentinel-FullSystem\
 │  config.json               # システム全体設定（トークン・配信先・監視対象）
 │  setup-gui.bat             # 【Step 1】GUI設定管理ツール起動用バッチ
 │  J-sentinel.bat            # 【Step 2】メイン・プッシュ通知システム起動用バッチ
 │  bot.bat                   # 【参考】対話型チャットボット (Discord/Matrix) 起動用バッチ
 │
 │  J-Sentinel_main.py        # メイン・オーケストレーター（新着検知・ディスパッチ）
 │  js_main_gui_setup.py      # GUI設定・マルチ配信先マネージャー (CustomTkinter製)
 │
 ├─ system/                   # システム中核モジュール群
 │      config_manager.py     # 設定ファイル読み込み・環境検証
 │      log_monitor.py        # 監視ディレクトリの非同期ファイルウォッチャー
 │      info_parser.py        # 気象情報・特別警報等の汎用パーサ
 │      quake_parser.py       # 地震・津波・遠地地震情報 パーサ＆震度ソート
 │      senders.py            # マルチプラットフォーム配信司令塔
 │
 ├─ bot/                      # 対話型ボットモジュール群
 │      discord_bot.py        # Discord インタラクティブ・コールバックボット
 │      matrix_bot.py         # Matrix インタラクティブ・コールバックボット
 │      warning_parser.py     # 気象警報・注意報JSON パーサ＆地域検索
 │      weather_parser.py     # 天気予報JSON パーサ (Discord Embed用)
 │      weather_parser_matrix.py # 天気予報JSON パーサ (Matrix Markdown用)
 │
 └─ js_core/                  # コア・インジェストモジュール群
     │  run_sentinel.py       # 気象庁データ定期ポーリング・インジェスト実行
     ├─ codemaster/           # 振り分けルール・地域コード辞書 (CSV)
     └─ database/             # 取得データの保存先ルート
         ├─ info/             # 総合情報・気象警報系
         ├─ keiho/            # 警報変換データ (WarningRT.json 等)
         └─ quake/            # 地震系 (japan / tsunami / world / etc)


【クイックスタート手順】

1. 環境の準備
   - Python 3.x がインストールされていることを確認してください
     （インストーラー実行時は 'Add Python to PATH' にチェックを入れてください）。

2. 初期設定 (GUI)
   - `setup-gui.bat` を実行します。
   - 自動的に Python 環境の確認と、不足しているライブラリ
     （psutil, requests, Pillow, customtkinter, discord.py, nio, pandas 等）の導入が行われます。
   - GUI画面が起動したら、以下を設定してください：
     ・ Discord / Matrix Bot 共通設定（Token 等）
     ・ 1. 監視対象の選択（CSVに紐づくインジェストフォルダの有効化）
     ・ 2. 配信先・SNS連携設定（Discord Webhook、Slack、Matrix、Bluesky 等）
   - 「設定を保存」ボタンを押すと `config.json` に反映されます。

3. メイン・プッシュ通知システムの本格稼働
   - `J-sentinel.bat` を実行します。
   - メインランナー (`J-Sentinel_main.py`) が起動し、裏でコアインジェスト (`run_sentinel.py`) と連動します。
   - 新着防災イベントを検知次第、指定されたマルチプラットフォームへ自動でプッシュ通知が飛びます。

4. 対話型チャットボット（情報照会機能）の併用
   - チャットから「帯広市の気象情報は？」や「帯広の天気は？」とメンション・問い合せて即座に情報を引き出したい場合は、
     別途 `bot.bat` を起動することで、DiscordやMatrix上の対話機能が利用可能になります。
	    ※現在の対応しているコマンド
		     天気系   ○○の天気は   天気/○○※スラッシュは全角半角両対応
			 気象系   ○○の気象情報は   気象/○○※スラッシュは全角半角両対応
	 

【対応配信プラットフォーム】
- Discord (Embed形式 / Simple形式 ＆ チャット応答)
- Slack (Webhook連携によるプッシュ通知)
- Matrix (ルーム送受信 ＆ 対話応答)
- Bluesky (AT Protocol による画像付きポスティング)
======================================================================