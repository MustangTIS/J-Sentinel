<div align="center">
  <img src="Asset/icon.jpg" alt="J-Sentinel Logo" width="160" height="160">
  <h1>J-Sentinel (v0.9.8-beta)</h1>
  <p><strong>高度防災情報インジェスト・マルチプラットフォーム配信オーケストレーターシステム</strong></p>
</div>

---

## 📥 ダウンロード

最新のフルシステム版パッケージ（コアエンジン、マルチ配信モジュール、GUIマネージャー同梱）は、以下のリンクからダウンロードできます。

👉 **[J-Sentinel_FullSystem_v0.9.8.zip をダウンロード](https://github.com/MustangTIS/J-Sentinel/releases/download/v0.9.8/J-Sentinel_FullSystem_v0.9.8.zip)**

---

## 📋 概要

**J-Sentinel** は、気象庁が公開する公式オープンデータ（地震、津波、気象警報、各種防災情報など）を定期ポーリングによってローカルストレージへインジェスト（取得・蓄積）し、さらに **Discord、Slack、Matrix、Bluesky** などのマルチプラットフォームへ自動配信、対話型ボットによる情報照会を行うための高度防災システムです。

非公式APIに依存せず、気象庁の一次ソースからクリーンかつ安全にデータを取得する「コアエンジン」と、それを拡張・通知する「フルシステム（Discord連携等）」を一つに統合したパッケージとして提供しています。

---

## 📁 ディレクトリ構成

本パッケージには、コアエンジン単体と、マルチ通知・GUI設定マネージャーを含むフルシステム版が同梱されています。

```text
\GitHub\J-Sentinel\
  ┣ Asset/
  ┃  ┗ icon.jpg              # システムアイコン
  ┣ J-Sentinel-Core/          # コア・インジェストシステム単体
  ┃  ┣ codemaster/            # 振り分けルール・地域コード辞書 (CSV)
  ┃  ┣ database/              # 取得したJSONデータや同期時刻ファイル（※実行時に自動生成）
  ┃  ┣ config.json            # コア動作設定ファイル
  ┃  ┣ run_sentinel.py        # メイン・オーケストレーター（常駐ランナー）
  ┃  ┣ run_sentinel.bat       # ランナー起動用バッチ
  ┃  ┣ js_gui_setup.py        # GUI設定管理・マスター編集ツール
  ┃  ┗ setup-gui.bat          # コア用GUI設定起動バッチ
  ┗ J-Sentinel_FullSystem/    # フルシステム版（マルチ配信・GUI・Bot統合）
     ┣ config.json            # システム全体設定（トークン・配信先等）
     ┣ setup-gui.bat          # GUI設定・マルチ配信先マネージャー起動用バッチ
     ┣ J-Sentinel-Boot.bat    # メインシステム (J-Sentinel_main.py) 起動用バッチ
     ┣ Bot-Boot.bat           # Discordコールバックボット (bot.py) 起動用バッチ
     ┣ J-Sentinel_main.py     # メイン・オーケストレーター
     ┣ senders.py             # マルチプラットフォーム配信司令塔 (Discord/Slack/Matrix/Bluesky)
     ┣ bot.py                 # Discord インタラクティブ・コールバックボット
     └─ js_core/              # コアインジェストモジュール群

```

---

## ⚙️ 主な仕様・特徴

* **自動オーケストレーション**: 指定秒数ごとに各フェッチスクリプトを安全に順次実行し、データの取りこぼしを防止。
* **インテリジェントな差分同期**: 初回のみ全件取得（ドカ食い）を行い、2回目以降は前回同期時刻を基準にした高速な差分チェックへ自動移行。
* **堅牢なプロセス管理**: サブプロセス実行時のタイムアウト制御により、ネットワーク遅延や大量データ処理時のデッドロックを回避。
* **マルチプラットフォーム対応**: 検知した災害・気象情報を Discord (Embed/Simple・改行対応)、Slack、Matrix、Bluesky へシームレスにディスパッチ。
* **CustomTkinter製 GUIマネージャー**: `setup-gui.bat` により、巡回間隔、監視対象、各SNS配信先のトークン等を直感的に設定可能。

---

## 🚀 クイックスタート (Full System Edition)

1. **環境の準備**
* Python 3.x がインストールされていることを確認してください（インストーラー実行時は `Add Python to PATH` にチェック）。


2. **初期設定 (GUI)**
* 展開したフォルダ内にある `\J-Sentinel_FullSystem\setup-gui.bat` を実行します。
* 自動で必要ライブラリ（`requests`, `psutil`, `Pillow`, `customtkinter`）が導入され、設定画面が起動します。
* Discord Bot トークンや各配信先、監視対象を設定して「設定を保存」してください。


3. **システムの本格稼働**
* `J-Sentinel-Boot.bat` を実行すると、メインランナーおよびインジェスト基盤が連動して常駐を開始します。


4. **Discord Bot（情報照会）の利用**
* 必要に応じて `Bot-Boot.bat` を起動することで、Discord上からの対話型情報照会が利用可能になります。



---

## 🗺️ 今後の開発予定 (Roadmap)

* [x] **インフラストラクチャの確立**: 気象庁データの安全なインジェストとローカル蓄積基盤の実装。
* [x] **マルチプラットフォーム通知**: Discord、Slack、Matrix、Blueskyへの配信ブリッジ統合。
* [ ] **検知フィルターの高度化**: 蓄積データやリアルタイムデータから、特定の条件（大規模地震、警報発令等）をより柔軟にフィルタリング・検知する仕組みの強化。
* [ ] **ダッシュボード・可視化**: 蓄積されたログや状態を直感的に確認できるUI/UXのブラッシュアップ。

---

## 📄 仕様書・関連リンク

* [開発方針・仕様書 (GitHub)](https://github.com/MustangTIS/J-Sentinel/blob/main/%E9%96%8B%E7%99%BA%E6%96%B9%E9%87%9D%E4%BB%95%E6%A7%98%E6%9B%B8.md)

---

## 📝 履歴 / Version

* **v0.5**: コアシステムおよびオーケストレーターの安定稼働を実現。初回大量データのタイムアウト対策・差分同期フローを確立。
* **v0.6**: `codemaster` フォルダに複数のCSVを追加し、ジャンル切り分けを明確化。
* **v0.7.5**: フルシステム版のメインフレームを統合。コア版とフル版を同梱したパッケージとして展開。
* **v0.9.5-beta**: マルチプラットフォーム配信の本格統合およびGUI設定ツールの刷新。
* **v0.9.8-beta**:
* 監視ガードレールの最適化（大雨特別警報などの重要情報が排他・取りこぼされる不具合の解消）。
* Matrix送信エラーの修正と安定化。
* Discord Simple（`dissimple`）のプレーンテキスト出力における改行対応（可読性の向上）。
* **動作確認状況**: Discord（Embed / 改行版 Simple）、Slack、Matrix における各配信ルートの正常な動作を確認済み。