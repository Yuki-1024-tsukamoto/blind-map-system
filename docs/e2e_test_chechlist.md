# End-to-End Test Checklist

このチェックリストは、360度動画を入力し、ノードベース探索MVPが一通り動くか確認するためのものです。

---

## 0. 前提

- backend が起動できる
- frontend が起動できる
- `.env` がプロジェクト直下に存在する
- `data/projects/demo/` が存在する
- Gemini APIを使う場合、`GEMINI_API_KEY` が設定されている

---

## 1. backend 起動

```powershell
cd C:\Users\yt200\Downloads\blind-map-system\backend
.venv\Scripts\activate
python -m uvicorn main:app --reload
```

確認URL:

```text
http://127.0.0.1:8000/docs
```

成功条件:

- `/docs` が開く
- `/projects` が 200 OK で返る

---

## 2. frontend 起動

```powershell
cd C:\Users\yt200\Downloads\blind-map-system\frontend
npm run dev
```

確認URL:

```text
http://localhost:5173/
```

成功条件:

- 画面が表示される
- プロジェクト一覧に `Museum Demo / ready` が出る

---

## 3. 動画アップロード

frontend の「アップロード」タブで、短い360度動画を選択してアップロードする。

成功条件:

- `status: uploaded`
- `job_id: job_xxxxxxxxxxxx`
- `filename: ...`
- `message: Video uploaded successfully`

メモ:

```text
使用した job_id:
```

---

## 4. 前処理

アップロード画面で「前処理を開始」を押す。

成功条件:

- `status: preprocessed`
- `keyframe_count` が 1以上
- `ocr_master_path` が表示される
- `slam_erp_path` が表示される

ファイル確認:

```powershell
dir data\projects\demo\captures\<job_id>\frames\keyframes
```

期待:

- `frame_000001.jpg` が存在する

---

## 5. 仮グラフ生成

アップロード画面で「仮グラフを生成」を押す。

成功条件:

- `status: graph_generated`
- `node_count` が `keyframe_count` と一致する
- `edge_count` が `node_count - 1` になる

ファイル確認:

```powershell
dir data\projects\demo\captures\<job_id>\graph
```

期待:

- `graph.json`
- `nodes.json`
- `edges.json`

---

## 6. active job 確認

```powershell
Get-Content data\projects\demo\active_job.json -Encoding utf8
```

成功条件:

- `active_job_id` が今回の `job_id` になっている

---

## 7. sector画像生成

`/docs` または frontend から以下を実行する。

```text
POST /projects/{project_id}/jobs/{job_id}/generate-sector-images
```

成功条件:

- `status: sector_images_generated`
- `sector_image_count = node_count × 8`

ファイル確認:

```powershell
dir data\projects\demo\captures\<job_id>\sectors\N0001
```

期待:

- `front.jpg`
- `front_right.jpg`
- `right.jpg`
- `back_right.jpg`
- `back.jpg`
- `back_left.jpg`
- `left.jpg`
- `front_left.jpg`

---

## 8. Dummy OCR

```text
POST /projects/{project_id}/jobs/{job_id}/run-dummy-ocr
```

成功条件:

- `status: dummy_ocr_completed`
- `ocr_result_count` が 1以上

確認URL:

```text
http://127.0.0.1:8000/projects/demo/nodes/N0001/ocr
```

期待:

- `案内`
- `SHOP`
- `入口`

のいずれかが表示される

---

## 9. 8方向説明生成

```text
POST /projects/{project_id}/jobs/{job_id}/generate-dummy-descriptions
```

成功条件:

- `status: dummy_descriptions_generated`
- `sector_description_count = node_count × 8`

確認URL:

```text
http://127.0.0.1:8000/projects/demo/nodes/N0001/descriptions
```

期待:

- `front`
- `right`
- `left`

などの説明が返る

---

## 10. 探索画面

frontend の「プロジェクト一覧」から「地図データを読み込んで探索画面へ」を押す。

成功条件:

- `graph_type: dummy_keyframe_graph`
- `node_count` が表示される
- 現在ノードが `N0001`
- keyframe画像が表示される

---

## 11. ノード移動

探索画面で隣接ノードへ移動する。

成功条件:

- `N0001 → N0002`
- `N0002 → N0003`
- 現在ノード表示が変わる
- keyframe画像が切り替わる

---

## 12. 8方向説明表示

現在ノードで「このノードの8方向説明を表示」を押す。

成功条件:

以下の方向ボタンが出る。

- `前`
- `右前`
- `右`
- `右後`
- `後`
- `左後`
- `左`
- `左前`

各方向を押したときに以下が表示される。

- sector画像
- 説明文
- OCR結果

---

## 13. Gemini説明生成

探索画面で「このノードの8方向をGemini生成」を押す。

成功条件:

- `updated_count` が 1以上
- 理想は `updated_count: 8`
- `failed_count: 0` が理想
- 各方向の説明がGemini生成文に変わる
- `review_required: true`

注意:

- この処理は Gemini API を最大8回呼ぶ
- 無料枠を使う場合は短時間に何度も押さない

---

## 14. 検索

検索タブで以下を検索する。

```text
N0001
```

成功条件:

- `N0001` がヒットする

次に以下を検索する。

```text
SHOP
```

成功条件:

- OCR由来の検索結果が出る

---

## 15. 経路訓練

経路訓練タブで以下を入力する。

```text
出発ノード: N0001
目的ノード: N0005
```

成功条件:

以下のような経路が出る。

```text
N0001 → N0002 → N0003 → N0004 → N0005
```

---

## 16. レビュー

レビュータブで「レビュー対象を読み込む」を押す。

成功条件:

- `review_required=true` の説明が表示される
- 「承認する」で承認できる
- 「編集する」で編集欄が開く
- 「編集して保存」で保存できる

確認URL:

```text
http://127.0.0.1:8000/projects/demo/nodes/N0001/descriptions
```

期待:

- `approval_status`
- `edited_by`
- `version`

が更新される

---

## 17. ログ確認

ログタブで「最新ログを読み込む」を押す。

成功条件:

以下のイベントが確認できる。

- `move_node`
- `view_node_descriptions`
- `select_sector`
- `search`
- `route_calculate`
- `generate_gemini_descriptions`
- `review_approve`
- `review_edit`

ファイル確認:

```powershell
Get-Content data\projects\demo\logs\events.jsonl -Encoding utf8 -Tail 20
```

---

## 18. job / capture 単位の保存確認

PowerShellで以下を確認する。

```powershell
dir data\projects\demo\captures
```

成功条件:

- 今回の `job_id` に対応するフォルダがある

例:

```text
job_xxxxxxxxxxxx
```

さらに以下を確認する。

```powershell
dir data\projects\demo\captures\<job_id>
```

期待:

- `raw`
- `derived`
- `frames`
- `graph`
- `sectors`
- `ocr`
- `descriptions`

一部が無い場合:

- `sectors` が無い → sector画像生成が未実行
- `ocr` が無い → Dummy OCRが未実行
- `descriptions` が無い → 8方向説明生成が未実行

---

## 19. active job の確認

```powershell
Get-Content data\projects\demo\active_job.json -Encoding utf8
```

成功条件:

```json
{
  "project_id": "demo",
  "active_job_id": "今回のjob_id",
  "updated_at": "..."
}
```

---

## 20. 直接API確認

map:

```text
http://127.0.0.1:8000/projects/demo/map
```

descriptions:

```text
http://127.0.0.1:8000/projects/demo/nodes/N0001/descriptions
```

sector images:

```text
http://127.0.0.1:8000/projects/demo/nodes/N0001/sector-images
```

OCR:

```text
http://127.0.0.1:8000/projects/demo/nodes/N0001/ocr
```

logs:

```text
http://127.0.0.1:8000/projects/demo/logs?limit=20
```

---

## 21. 画像直接確認

keyframe:

```text
http://127.0.0.1:8000/data/demo/captures/<job_id>/frames/keyframes/frame_000001.jpg
```

sector image:

```text
http://127.0.0.1:8000/data/demo/captures/<job_id>/sectors/N0001/front.jpg
```

注意:

現在の静的配信URLが job/capture 対応前のままの場合、以下の旧URLになる場合がある。

```text
http://127.0.0.1:8000/data/demo/frames/keyframes/frame_000001.jpg
http://127.0.0.1:8000/data/demo/sectors/N0001/front.jpg
```

job/capture 単位に統一する場合は、backend の `image_url` 生成処理も capture パスに合わせる必要がある。

---

## 22. エラー時の切り分け

### backendが起動しない

確認:

```powershell
cd C:\Users\yt200\Downloads\blind-map-system\backend
.venv\Scripts\activate
python -m uvicorn main:app --reload
```

よくある原因:

- import漏れ
- 関数のインデント崩れ
- `main.py` の `def` の引数部分に処理を書いてしまっている
- 必要なパッケージが入っていない

---

### frontendが白画面

確認:

```powershell
cd C:\Users\yt200\Downloads\blind-map-system\frontend
npm run dev
```

よくある原因:

- TypeScriptエラー
- JSXタグの閉じ忘れ
- 関数の重複
- `null` 可能性のある値に直接アクセスしている

---

### sector画像が無い

確認:

```powershell
dir data\projects\demo\captures\<job_id>\sectors
```

無い場合:

```text
POST /projects/{project_id}/jobs/{job_id}/generate-sector-images
```

を実行する

---

### OCR結果が無い

確認:

```powershell
dir data\projects\demo\captures\<job_id>\ocr
```

無い場合:

```text
POST /projects/{project_id}/jobs/{job_id}/run-dummy-ocr
```

を実行する

---

### 説明文が無い

確認:

```powershell
dir data\projects\demo\captures\<job_id>\descriptions
```

無い場合:

```text
POST /projects/{project_id}/jobs/{job_id}/generate-dummy-descriptions
```

を実行する

---

### Gemini生成が失敗する

確認:

- `.env` がプロジェクト直下にあるか
- `GEMINI_API_KEY` が設定されているか
- `GEMINI_DESCRIPTION_MODEL` が正しいか
- sector画像が存在するか
- 無料枠やレート制限に当たっていないか

`.env` 例:

```env
DESCRIPTION_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_DESCRIPTION_MODEL=gemini-2.5-flash
```

---

## 23. Git確認

コードを変更した場合は保存する。

```powershell
git status
git add .
git commit -m "Update e2e test checklist"
git push
```

生成データだけ変わった場合、基本的にcommit不要。

---

## 24. 成功判定

以下がすべて通れば、現時点のMVPは成功。

- 360度動画をアップロードできる
- 前処理できる
- keyframeが抽出される
- 仮ノードグラフが生成される
- active job が設定される
- 探索画面で現在ノードを表示できる
- ノード移動できる
- keyframe画像が切り替わる
- sector画像を表示できる
- OCR結果を表示できる
- Gemini説明生成ができる
- 検索できる
- 経路訓練できる
- レビューできる
- ログが保存される

---

## 25. 次の大きな改善候補

- 実験用UIの整理
- active job 表示UI
- job/capture単位の状態表示
- Google Cloud Vision OCR連携
- Gemini説明生成の対象範囲制御
- landmark schema の保存
- OCR・説明・landmark統合検索
- 経路訓練UIの改善
- VoiceOver / PWA対応
- OpenSfM / SLAM によるposeベースノード生成