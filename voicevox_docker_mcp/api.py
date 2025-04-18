from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
import os
import time
import simpleaudio as sa
import threading
import json

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

class TextToSpeechRequest(BaseModel):
    text: str
    speaker_id: int = 3  # デフォルトはずんだもん（ノーマル）

# 音声再生用の関数
def play_audio(file_path):
    """音声ファイルを再生する"""
    try:
        # 音声ファイルを読み込む
        wave_obj = sa.WaveObject.from_wave_file(file_path)
        # 再生を開始
        play_obj = wave_obj.play()
        # 再生が終了するまで待機
        play_obj.wait_done()
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

@app.post("/synthesize")
async def synthesize_voice(request: TextToSpeechRequest):
    try:
        # VOICEVOXエンジンのURL
        engine_url = "http://voicevox:50021"
        
        # 音声合成用のクエリを作成
        query_params = {
            "text": request.text,
            "speaker": request.speaker_id
        }
        
        # 音声合成クエリの作成
        audio_query_response = requests.post(
            f"{engine_url}/audio_query",
            params=query_params
        )
        audio_query_response.raise_for_status()
        audio_query = audio_query_response.json()
        
        # 音声合成の実行
        synthesis_params = {
            "speaker": request.speaker_id
        }
        
        synthesis_response = requests.post(
            f"{engine_url}/synthesis",
            headers={"Content-Type": "application/json"},
            params=synthesis_params,
            json=audio_query
        )
        synthesis_response.raise_for_status()
        
        return {"audio": synthesis_response.content}
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"音声合成に失敗しました: {str(e)}") 