# VOICEVOX Docker MCP

VOICEVOX音声合成エンジンをDockerで簡単に利用できるFastAPI + MCP（Model Context Protocol）サーバーの実装です。

## 概要

このプロジェクトは、VOICEVOXのAPIを利用してテキストから音声を合成し、その場で再生するシンプルなAPIを提供します。FastAPI-MCPを使用してModel Context Protocol（MCP）に対応させることで、ClaudeなどのAIアシスタントから直接APIを呼び出せるようになります。

主な機能：
- テキストから音声合成（VOICEVOX APIを利用）
- 合成した音声をその場で再生
- 話者（キャラクター）の一覧取得
- MCP対応によるAIアシスタントとの連携

## システム構成

システムは2つの主要なコンポーネントから構成されています：

1. **VOICEVOXエンジン**: 音声合成の中核機能を提供するDockerコンテナ
2. **FastAPI + MCPサーバー**: VOICEVOXエンジンをラップし、使いやすいAPIとMCPインターフェースを提供

Docker Composeを使用して、これらのコンポーネントを連携させて実行します。

## 事前準備

### 必要環境

- Docker と Docker Compose
- Python 3.11以上（ローカル開発時）

## クイックスタート

### Docker Composeでの起動

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/voicevox-docker-mcp.git
cd voicevox-docker-mcp

# Docker Composeで起動
docker-compose up -d
```

起動後、以下のエンドポイントが利用可能になります：
- API ドキュメント: `http://localhost:50039/docs`
- MCP エンドポイント: `http://localhost:50039/mcp`

### ローカル開発環境での実行

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/voicevox-docker-mcp.git
cd voicevox-docker-mcp

# 仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存パッケージのインストール
pip install -e .
# または
python -m pip install -r requirements.txt

# VOICEVOXエンジンをDockerで起動
docker run --rm -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:cpu-latest

# 別ターミナルでFastAPI+MCPサーバーを起動
python main.py
```

## API使用例

### 話者一覧の取得

```bash
curl -X GET http://localhost:50039/api/speakers
```

### テキストから音声を合成して再生

```bash
curl -X POST http://localhost:50039/api/synthesis \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは、ずんだもんです", "speaker_id": 3}'
```

## MCP使用例

Claude 3などのAIアシスタントに以下のように指示することで、MCP経由で音声合成が可能です：

```
# 話者一覧を取得する場合
話者一覧を取得してください

# 音声を合成して再生する場合
「こんにちは、私はクロードです。今日はいい天気ですね。」というテキストを四国めたんの声で読み上げてください。
```

## テスト実行

テストを実行するには：

```bash
# 依存パッケージのインストール
pip install pytest

# テスト実行
pytest
```

## Docker構成

このプロジェクトは、複数コンテナアプローチを採用しています：

1. **VOICEVOXエンジンコンテナ**: 音声合成の中核機能
2. **FastAPI+MCPアプリケーションコンテナ**: VOICEVOXエンジンと連携するAPI

これにより、各コンポーネントを独立して管理し、必要に応じてスケールできます。

## 注意点

- 音声再生機能はホストマシンのオーディオデバイスを使用します。サーバー環境では動作しない場合があります。
- VOICEVOX音声合成エンジンはCPUリソースを消費します。十分なリソースを確保してください。
- 合成された音声ファイルは常に同じファイル名（output.wav）で上書きされます。

## ライセンス

このプロジェクトは[MITライセンス](LICENSE)の下で公開されています。

## 著者

Your Name

## 謝辞

- [VOICEVOX](https://voicevox.hiroshiba.jp/) - 高品質な音声合成エンジンを提供してくれているプロジェクト
- [FastAPI](https://fastapi.tiangolo.com/) - 高速なAPIフレームワーク
- [FastAPI-MCP](https://github.com/shroominic/fastapi-mcp) - FastAPIをMCP対応にするライブラリ