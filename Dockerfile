# ベースイメージとしてPython 3.11を使用
FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# 必要なパッケージをインストール（音声再生のための依存関係含む）
RUN apt-get update && apt-get install -y \
    curl \
    libasound2-dev \
    gcc \
    g++ \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# プロジェクトファイルをコピー
COPY pyproject.toml README.md ./
COPY voicevox_docker_mcp ./voicevox_docker_mcp/

# 依存関係のインストール
RUN pip install --no-cache-dir -e .

# ポートの公開
EXPOSE 50039

# 起動コマンド
CMD ["python", "-m", "voicevox_docker_mcp.main"] 