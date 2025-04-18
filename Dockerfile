# ベースイメージとしてPython 3.11を使用
FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# 必要なパッケージをインストール（音声再生のための依存関係含む）
RUN apt-get update && apt-get install -y \
    curl \
    libasound2-dev \
    alsa-utils \
    alsa-base \
    alsa-oss \
    gcc \
    g++ \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# プロジェクトファイルをコピー
COPY . .

# ALSA設定の作成（ファイルが存在しない場合に作成）
RUN if [ ! -f /etc/asound.conf ]; then \
    echo '# ALSA configuration file for Docker container' > /etc/asound.conf && \
    echo 'pcm.!default { type hw; card 0; }' >> /etc/asound.conf && \
    echo 'ctl.!default { type hw; card 0; }' >> /etc/asound.conf; \
    fi

# 依存関係のインストール
RUN pip install --no-cache-dir -e .

# ポートの公開
EXPOSE 50039

# 起動コマンド
CMD ["python", "-m", "voicevox_docker_mcp.main"] 