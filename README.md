# blind-map-system

360度動画から、視覚障碍者向けの探索・経路訓練用ノードベース空間を生成する研究用MVPです。

## 構成

- frontend: React + TypeScript + Vite
- backend: Python + FastAPI
- data: 動画、ノード、OCR、説明文などの保存先
- docs: 仕様書
- scripts: 補助スクリプト
- prompts: AI生成用プロンプト

## 現在の実装段階

現在は、ダミーデータでUIとAPIの土台を作る段階です。
360度動画処理、OCR、説明文生成、OpenSfM統合はまだ実装しません。