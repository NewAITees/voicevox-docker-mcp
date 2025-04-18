#!/bin/bash
# FastAPI+MCPアプリケーションをDockerで起動するスクリプト

# スクリプトをより堅牢に
set -e

# バナー表示
echo "========================================"
echo "  FastAPI+MCP 起動スクリプト  "
echo "========================================"

# Dockerが利用可能か確認
if ! command -v docker &> /dev/null; then
    echo "エラー: Dockerがインストールされていません。"
    echo "https://docs.docker.com/get-docker/ からインストールしてください。"
    exit 1
fi

# Docker Composeが利用可能か確認
if ! command -v docker compose &> /dev/null; then
    echo "エラー: Docker Composeがインストールされていません。"
    echo "https://docs.docker.com/compose/install/ からインストールしてください。"
    exit 1
fi

# ALSAデバイスの確認
if [ ! -d "/dev/snd" ]; then
    echo "警告: ALSAデバイスが見つかりません。音声再生が機能しない可能性があります。"
fi

# 音声再生設定の確認
if [ "$1" == "--no-audio" ]; then
    echo "音声再生機能を無効にして起動します..."
    export ENABLE_AUDIO_PLAYBACK=false
else
    echo "音声再生機能を有効にして起動します..."
    export ENABLE_AUDIO_PLAYBACK=true
fi

# Docker Composeビルド
echo "コンテナをビルドしています..."
docker compose build

# Docker Compose起動
echo "コンテナを起動しています..."
docker compose up -d

# 起動確認
echo "サービスの起動を確認しています..."
sleep 10  # サービスが起動するまで少し待つ

# FastAPI+MCPアプリの確認
if curl -s http://localhost:50039/api/health &> /dev/null; then
    echo "FastAPI+MCPアプリケーションが正常に起動しています。"
else
    echo "警告: FastAPI+MCPアプリケーションが応答していません。ログを確認してください。"
    docker compose logs fastapi-mcp
fi

# ALSAデバイスの確認
echo "ALSAデバイスの状態を確認しています..."
docker compose exec fastapi-mcp aplay -l

echo ""
echo "利用可能なエンドポイント:"
echo "- APIドキュメント: http://localhost:50039/docs"
echo "- MCPエンドポイント: http://localhost:50039/mcp"
echo ""
echo "停止するには 'docker compose down' を実行してください。" 