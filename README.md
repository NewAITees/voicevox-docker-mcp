# voicevox-docker-mcp


# VOICEVOX音声合成API - FastAPIとMCPの実装計画

## 1. 概要

このプロジェクトでは、VOICEVOXのAPIを利用してテキストから音声を合成し、その場で再生するシンプルなAPIを作成します。FastAPI-MCPを使用してModel Context Protocol（MCP）に対応させることで、ClaudeなどのAIアシスタントから直接APIを呼び出せるようになります。音声ファイルは上書き形式で保存され、常に最新の合成音声のみが保持されます。

## 2. アーキテクチャ

システムの構成は以下のようになります：

1. **FastAPI API**: 音声合成のエンドポイントを提供
2. **MCP対応**: FastAPI-MCPを使用してMCPサーバー化
3. **音声合成エンジン**: VOICEVOXエンジンへのAPI呼び出し
4. **音声再生**: 合成された音声をその場で再生

## 3. 事前準備

### VOICEVOXのセットアップ

VOICEVOXエンジンをセットアップします。Dockerを使用した起動例:

voicevoxのドッカーのインストールは人間が担当します

VOICEVOXエンジンは通常、ポート50021でAPIを公開します。

### 必要なPythonパッケージ

```bash
# uv（推奨）を使用する場合
uv pip install fastapi fastapi-mcp uvicorn requests python-multipart playsound

poetry add fastapi fastapi-mcp uvicorn requests python-multipart playsound
```

## 4. API設計

### エンドポイント一覧

| エンドポイント | メソッド | 説明 | 対応するVOICEVOX API |
|-------------|--------|------|------------------|
| `/api/speakers` | GET | 利用可能な話者（キャラクター）の一覧を取得 | `/speakers` |
| `/api/synthesis` | POST | テキストから音声を合成して再生 | `/audio_query` + `/synthesis` |
| `/api/health` | GET | APIの稼働状態を確認 | - |

### データモデル

```
SynthesisRequest:
  - text: string
  - speaker_id: int
  - enable_interrogative_upspeak: bool (optional, default: true)

SynthesisResponse:
  - status: string
  - message: string
```

## 5. FastAPIアプリケーションの実装

### api.py

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
import os
import time
from playsound import playsound
import threading

# 設定
VOICEVOX_API_URL = "http://localhost:50021"
AUDIO_OUTPUT_PATH = "./output.wav"  # 常に同じファイル名で上書き

# FastAPIアプリの初期化
app = FastAPI(
    title="VOICEVOX Speech Synthesis API",
    description="VOICEVOXを使用してテキストから音声を合成し、その場で再生するAPIです",
    version="1.0.0"
)

# データモデル
class SynthesisRequest(BaseModel):
    text: str
    speaker_id: Optional[int] = 1  # デフォルトはずんだもん(1)
    enable_interrogative_upspeak: Optional[bool] = True

class SynthesisResponse(BaseModel):
    status: str = "success"
    message: str = "音声を合成して再生しました"

# 音声再生用の関数
def play_audio(file_path):
    """音声ファイルを再生する"""
    try:
        playsound(file_path)
    except Exception as e:
        print(f"音声再生エラー: {str(e)}")

# ヘルスチェックエンドポイント
@app.get("/api/health", operation_id="health_check", tags=["System"])
async def health_check():
    """
    APIの稼働状態を確認します。
    """
    try:
        # VOICEVOXエンジンのヘルスチェック
        response = requests.get(f"{VOICEVOX_API_URL}/version")
        if response.status_code == 200:
            voicevox_version = response.json()
            return {
                "status": "healthy",
                "voicevox_engine_version": voicevox_version,
                "api_version": app.version
            }
        else:
            return {
                "status": "degraded",
                "message": "VOICEVOXエンジンに接続できません",
                "api_version": app.version
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": str(e),
            "api_version": app.version
        }

# 利用可能な話者の一覧を取得
@app.get("/api/speakers", operation_id="get_speakers", response_model=List[Any], tags=["Voice"])
async def get_speakers():
    """
    利用可能な話者（キャラクター）の一覧を取得します。
    """
    try:
        response = requests.get(f"{VOICEVOX_API_URL}/speakers")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="VOICEVOXエンジンからの応答エラー")
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"VOICEVOXエンジンへの接続エラー: {str(e)}")

# テキストから音声を合成して再生
@app.post("/api/synthesis", operation_id="synthesize_and_play", response_model=SynthesisResponse, tags=["Voice"])
async def synthesize_and_play(request: SynthesisRequest):
    """
    テキストから音声を合成し、その場で再生します。
    
    - **text**: 音声合成するテキスト
    - **speaker_id**: 話者ID (省略可能、デフォルトはずんだもん(1))
    - **enable_interrogative_upspeak**: 疑問文の語尾を自動的に上げるかどうか (省略可能、デフォルトはtrue)
    """
    try:
        # 音声合成用のクエリを作成
        query_params = {
            "text": request.text,
            "speaker": request.speaker_id
        }
        
        if request.enable_interrogative_upspeak is not None:
            query_params["is_enable_interrogative_upspeak"] = str(request.enable_interrogative_upspeak).lower()
        
        audio_query_response = requests.post(
            f"{VOICEVOX_API_URL}/audio_query",
            params=query_params
        )
        
        if audio_query_response.status_code != 200:
            raise HTTPException(
                status_code=audio_query_response.status_code, 
                detail="音声合成クエリの作成に失敗しました"
            )
        
        audio_query = audio_query_response.json()
        
        # 音声合成の実行
        synthesis_params = {
            "speaker": request.speaker_id
        }
        
        synthesis_response = requests.post(
            f"{VOICEVOX_API_URL}/synthesis",
            headers={"Content-Type": "application/json"},
            params=synthesis_params,
            json=audio_query
        )
        
        if synthesis_response.status_code != 200:
            raise HTTPException(
                status_code=synthesis_response.status_code, 
                detail="音声合成に失敗しました"
            )
        
        # 常に同じファイル名で上書き保存
        with open(AUDIO_OUTPUT_PATH, "wb") as f:
            f.write(synthesis_response.content)
        
        # 別スレッドで音声を再生（APIレスポンスをブロックしないため）
        threading.Thread(target=play_audio, args=(AUDIO_OUTPUT_PATH,)).start()
        
        return SynthesisResponse(
            status="success", 
            message=f"「{request.text}」を話者ID {request.speaker_id} の声で再生中"
        )
        
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"VOICEVOXエンジンへの接続エラー: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部サーバーエラー: {str(e)}")
```

## 6. MCPサーバー化の実装

### main.py

```python
from fastapi_mcp import FastApiMCP
import api  # 先ほど作成したapiモジュールをインポート

# MCPサーバーの初期化
mcp = FastApiMCP(
    api.app,  # 既存のFastAPIアプリを指定
    name="VOICEVOX Speech Synthesis MCP",
    description="VOICEVOXを使用して、テキストから音声を合成するMCPサーバー",
    base_url="http://localhost:8000",  # ベースURLを指定（重要）
)

# MCPサーバーをFastAPIアプリに直接マウント
mcp.mount()

# サーバー起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api.app, host="0.0.0.0", port=8000)
```

## 7. フォルダ構造

プロジェクトのフォルダ構造は以下のようになります：

```
voicevox-fastapi-mcp-api/
├── api.py              # FastAPIアプリケーションの定義
├── main.py             # MCPサーバー化と起動
└── requirements.txt    # 依存パッケージのリスト
```

## 8. 起動と使用方法

### 起動手順

1. VOICEVOXエンジンを起動する
```bash
# Docker使用の場合
docker run --rm -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:cpu-latest
```

2. FastAPI+MCPアプリケーションを起動する
```bash
python main.py
```

3. API エンドポイントとMCPエンドポイントが利用可能になる
   - API ドキュメント: `http://localhost:8000/docs`
   - MCP エンドポイント: `http://localhost:8000/mcp`

### API利用例

```bash
# 利用可能な話者一覧を取得
curl -X GET http://localhost:8000/api/speakers

# テキストから音声を合成して再生
curl -X POST http://localhost:8000/api/synthesis \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは、ずんだもんです", "speaker_id": 3}'
```

5. FastAPIアプリケーションの実装
api.py
pythonfrom fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
import os
import time
from playsound import playsound
import threading

# 設定
VOICEVOX_API_URL = "http://localhost:50021"
AUDIO_OUTPUT_PATH = "./output.wav"  # 常に同じファイル名で上書き

# FastAPIアプリの初期化
app = FastAPI(
    title="VOICEVOX Speech Synthesis API",
    description="VOICEVOXを使用してテキストから音声を合成し、その場で再生するAPIです",
    version="1.0.0"
)

# データモデル
class SynthesisRequest(BaseModel):
    text: str
    speaker_id: Optional[int] = 1  # デフォルトはずんだもん(1)
    enable_interrogative_upspeak: Optional[bool] = True

class SynthesisResponse(BaseModel):
    status: str = "success"
    message: str = "音声を合成して再生しました"

# 音声再生用の関数
def play_audio(file_path):
    """音声ファイルを再生する"""
    try:
        playsound(file_path)
    except Exception as e:
        print(f"音声再生エラー: {str(e)}")

# ヘルスチェックエンドポイント
@app.get("/api/health", operation_id="health_check", tags=["System"])
async def health_check():
    """
    APIの稼働状態を確認します。
    """
    try:
        # VOICEVOXエンジンのヘルスチェック
        response = requests.get(f"{VOICEVOX_API_URL}/version")
        if response.status_code == 200:
            voicevox_version = response.json()
            return {
                "status": "healthy",
                "voicevox_engine_version": voicevox_version,
                "api_version": app.version
            }
        else:
            return {
                "status": "degraded",
                "message": "VOICEVOXエンジンに接続できません",
                "api_version": app.version
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": str(e),
            "api_version": app.version
        }

# 利用可能な話者の一覧を取得
@app.get("/api/speakers", operation_id="get_speakers", response_model=List[Any], tags=["Voice"])
async def get_speakers():
    """
    利用可能な話者（キャラクター）の一覧を取得します。
    """
    try:
        response = requests.get(f"{VOICEVOX_API_URL}/speakers")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="VOICEVOXエンジンからの応答エラー")
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"VOICEVOXエンジンへの接続エラー: {str(e)}")

# テキストから音声を合成して再生
@app.post("/api/synthesis", operation_id="synthesize_and_play", response_model=SynthesisResponse, tags=["Voice"])
async def synthesize_and_play(request: SynthesisRequest):
    """
    テキストから音声を合成し、その場で再生します。
    
    - **text**: 音声合成するテキスト
    - **speaker_id**: 話者ID (省略可能、デフォルトはずんだもん(1))
    - **enable_interrogative_upspeak**: 疑問文の語尾を自動的に上げるかどうか (省略可能、デフォルトはtrue)
    """
    try:
        # 音声合成用のクエリを作成
        query_params = {
            "text": request.text,
            "speaker": request.speaker_id
        }
        
        if request.enable_interrogative_upspeak is not None:
            query_params["is_enable_interrogative_upspeak"] = str(request.enable_interrogative_upspeak).lower()
        
        audio_query_response = requests.post(
            f"{VOICEVOX_API_URL}/audio_query",
            params=query_params
        )
        
        if audio_query_response.status_code != 200:
            raise HTTPException(
                status_code=audio_query_response.status_code, 
                detail="音声合成クエリの作成に失敗しました"
            )
        
        audio_query = audio_query_response.json()
        
        # 音声合成の実行
        synthesis_params = {
            "speaker": request.speaker_id
        }
        
        synthesis_response = requests.post(
            f"{VOICEVOX_API_URL}/synthesis",
            headers={"Content-Type": "application/json"},
            params=synthesis_params,
            json=audio_query
        )
        
        if synthesis_response.status_code != 200:
            raise HTTPException(
                status_code=synthesis_response.status_code, 
                detail="音声合成に失敗しました"
            )
        
        # 常に同じファイル名で上書き保存
        with open(AUDIO_OUTPUT_PATH, "wb") as f:
            f.write(synthesis_response.content)
        
        # 別スレッドで音声を再生（APIレスポンスをブロックしないため）
        threading.Thread(target=play_audio, args=(AUDIO_OUTPUT_PATH,)).start()
        
        return SynthesisResponse(
            status="success", 
            message=f"「{request.text}」を話者ID {request.speaker_id} の声で再生中"
        )
        
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"VOICEVOXエンジンへの接続エラー: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部サーバーエラー: {str(e)}")
6. MCPサーバー化の実装
main.py
pythonfrom fastapi_mcp import FastApiMCP
import api  # 先ほど作成したapiモジュールをインポート

# MCPサーバーの初期化
mcp = FastApiMCP(
    api.app,  # 既存のFastAPIアプリを指定
    name="VOICEVOX Speech Synthesis MCP",
    description="VOICEVOXを使用して、テキストから音声を合成するMCPサーバー",
    base_url="http://localhost:8000",  # ベースURLを指定（重要）
)

# MCPサーバーをFastAPIアプリに直接マウント
mcp.mount()

# サーバー起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api.app, host="0.0.0.0", port=8000)
7. フォルダ構造
プロジェクトのフォルダ構造は以下のようになります：
voicevox-fastapi-mcp-api/
├── api.py              # FastAPIアプリケーションの定義
├── main.py             # MCPサーバー化と起動
└── requirements.txt    # 依存パッケージのリスト
8. 起動と使用方法
起動手順

VOICEVOXエンジンを起動する

bash# Docker使用の場合
docker run --rm -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:cpu-latest

FastAPI+MCPアプリケーションを起動する

bashpython main.py

API エンドポイントとMCPエンドポイントが利用可能になる

API ドキュメント: http://localhost:8000/docs
MCP エンドポイント: http://localhost:8000/mcp



API利用例
bash# 利用可能な話者一覧を取得
curl -X GET http://localhost:8000/api/speakers

# テキストから音声を合成して再生
curl -X POST http://localhost:8000/api/synthesis \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは、ずんだもんです", "speaker_id": 3}'
9. MCPツールの使用例
Claude経由でMCPツールを使用する例：

話者一覧を取得する：

話者一覧を取得したいです

音声を合成して再生する：

「こんにちは、私はクロードです。今日はいい天気ですね。」というテキストを四国めたんの声で読み上げてください。
10. 注意点と考慮事項

エラーハンドリング:

VOICEVOXエンジンが利用できない場合の適切なエラー処理
不正なリクエストパラメータに対するバリデーション
音声再生に関するエラー処理（システム環境によってはplaysoundが動作しない場合がある）


音声再生の仕組み:

playsoundライブラリは環境によって依存関係が異なる場合があります
macOSではpyobjcが必要
Linuxではgstreamerまたはffplayが必要
Windowsではwinsoundを使用


セキュリティ対策:

サーバー環境で使用する場合、音声再生機能が期待通りに動作しない可能性がある
アクセス制限（必要に応じてAPI Key認証などを追加）


パフォーマンス考慮事項:

長いテキストの場合、音声合成と再生に時間がかかる可能性がある
スレッドプールの考慮（多数の同時リクエストがある場合）


話者IDの取得と指定:

使用したい話者のIDを事前に確認する必要がある
/api/speakersエンドポイントで話者一覧を取得して適切なIDを見つける



11. 今後の拡張案

音声ファイルの保存オプション:

必要に応じて音声ファイルを一定期間保存する機能


パラメータカスタマイズ:

音声合成の詳細なパラメータ（ピッチ、速度など）を調整できるオプションの追加


再生デバイスの選択:

複数のオーディオデバイスがある場合に再生デバイスを選択できる機能


ウェブインターフェースの追加:

必要に応じてシンプルなウェブUIを追加（テスト用）


リモート環境対応:

サーバー環境でも使いやすいように、音声ファイルの再生を選択的に無効化する設定オプション


