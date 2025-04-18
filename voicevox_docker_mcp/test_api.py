import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import json
from pathlib import Path
import requests

# テスト対象の各モジュールをインポート
import api
from api import app

# テストクライアントの作成
client = TestClient(app)

# テスト用のダミーデータ
DUMMY_SPEAKERS_DATA = [
    {
        "name": "ずんだもん",
        "speaker_id": 3,
        "styles": [
            {"id": 1, "name": "ノーマル"}
        ]
    },
    {
        "name": "四国めたん",
        "speaker_id": 2,
        "styles": [
            {"id": 0, "name": "ノーマル"},
            {"id": 2, "name": "あまあま"}
        ]
    }
]

# モックの音声データ（バイナリファイル）
DUMMY_AUDIO_DATA = b'DUMMY_AUDIO_CONTENT'

# ====== フィクスチャ ======

@pytest.fixture
def mock_voicevox_api():
    """VOICEVOXエンジンAPIのモック"""
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        # バージョン情報の取得
        version_response = MagicMock()
        version_response.status_code = 200
        version_response.json.return_value = {"version": "0.14.0"}
        
        # 話者一覧の取得
        speakers_response = MagicMock()
        speakers_response.status_code = 200
        speakers_response.json.return_value = DUMMY_SPEAKERS_DATA
        
        # 音声合成クエリの作成
        audio_query_response = MagicMock()
        audio_query_response.status_code = 200
        audio_query_response.json.return_value = {"dummy": "audio_query_data"}
        
        # 音声合成の実行
        synthesis_response = MagicMock()
        synthesis_response.status_code = 200
        synthesis_response.content = DUMMY_AUDIO_DATA
        
        # モックレスポンスの設定
        mock_get.side_effect = lambda url, **kwargs: (
            version_response if '/version' in url else
            speakers_response if '/speakers' in url else
            MagicMock(status_code=404)  # その他のGETリクエスト
        )
        
        mock_post.side_effect = lambda url, **kwargs: (
            audio_query_response if '/audio_query' in url else
            synthesis_response if '/synthesis' in url else
            MagicMock(status_code=404)  # その他のPOSTリクエスト
        )
        
        yield mock_get, mock_post

@pytest.fixture
def mock_playsound():
    """playsound関数のモック"""
    with patch('threading.Thread') as mock_thread:
        yield mock_thread

# ====== テスト関数 ======

def test_health_endpoint(mock_voicevox_api):
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "voicevox_engine_version" in data
    assert data["api_version"] == app.version

def test_get_speakers(mock_voicevox_api):
    """話者一覧取得エンドポイントのテスト"""
    response = client.get("/api/speakers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data == DUMMY_SPEAKERS_DATA

def test_synthesize_speech_success(mock_voicevox_api, mock_playsound):
    """音声合成エンドポイントの成功ケースのテスト"""
    # テスト用の音声ファイルパス
    test_output_path = api.AUDIO_OUTPUT_PATH
    
    # 音声ファイルが既に存在する場合は削除
    if os.path.exists(test_output_path):
        os.remove(test_output_path)
    
    # APIリクエスト
    response = client.post(
        "/api/synthesis",
        json={"text": "テストです", "speaker_id": 3}
    )
    
    # レスポンスの検証
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "テストです" in data["message"]
    assert "3" in data["message"]
    
    # 音声ファイルが生成されたかどうかを確認
    assert os.path.exists(test_output_path)
    
    # 音声再生用のスレッドが起動されたかを確認
    mock_playsound.assert_called_once()

def test_synthesize_speech_with_custom_params(mock_voicevox_api, mock_playsound):
    """カスタムパラメータを指定した場合の音声合成テスト"""
    # モックの設定を修正
    mock_get, mock_post = mock_voicevox_api
    
    # audio_queryのレスポンスを設定
    audio_query_response = MagicMock()
    audio_query_response.status_code = 200
    audio_query_response.json.return_value = {"dummy": "audio_query_data"}
    
    # synthesisのレスポンスを設定
    synthesis_response = MagicMock()
    synthesis_response.status_code = 200
    synthesis_response.content = DUMMY_AUDIO_DATA
    
    def mock_post_side_effect(*args, **kwargs):
        url = args[0]
        if "audio_query" in url:
            return audio_query_response
        elif "synthesis" in url:
            return synthesis_response
        return MagicMock(status_code=404)
    
    # モックのside_effectを設定
    mock_post.side_effect = mock_post_side_effect
    
    response = client.post(
        "/api/synthesis",
        json={
            "text": "テストです",
            "speaker_id": 2,
            "enable_interrogative_upspeak": False
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "2" in data["message"]  # 話者IDが含まれているか確認
    
    # モックの呼び出しを確認
    post_calls = mock_post.call_args_list
    
    # audio_queryへのリクエストでパラメータが正しく渡されているか確認
    audio_query_call = next((call for call in post_calls if 'audio_query' in call[0][0]), None)
    assert audio_query_call is not None
    assert 'params' in audio_query_call[1]
    assert audio_query_call[1]['params']['speaker'] == 2
    assert 'is_enable_interrogative_upspeak' in audio_query_call[1]['params'] 
    assert audio_query_call[1]['params']['is_enable_interrogative_upspeak'] == 'false'

def test_error_handling_voicevox_unreachable():
    """VOICEVOXエンジンに接続できない場合のエラーハンドリングテスト"""
    # VOICEVOXエンジンへの接続が失敗するケースをモックで再現
    with patch('requests.get', side_effect=requests.RequestException("接続エラー")):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "接続エラー" in data["message"]
    
    with patch('requests.get', side_effect=requests.RequestException("接続エラー")):
        response = client.get("/api/speakers")
        assert response.status_code == 503
        assert "接続エラー" in response.json()["detail"]
    
    with patch('requests.post', side_effect=requests.RequestException("接続エラー")):
        response = client.post("/api/synthesis", json={"text": "テスト", "speaker_id": 1})
        assert response.status_code == 503
        assert "接続エラー" in response.json()["detail"]

def test_audio_query_error():
    """音声合成クエリの作成に失敗した場合のテスト"""
    # audio_queryの失敗をモック
    with patch('requests.post') as mock_post:
        def mock_post_side_effect(*args, **kwargs):
            url = args[0]
            if "audio_query" in url:
                error_response = MagicMock()
                error_response.status_code = 400
                error_response.json.return_value = {"error": "Invalid text"}
                return error_response
            return MagicMock(status_code=200)  # その他のリクエストは成功
        
        mock_post.side_effect = mock_post_side_effect
        
        response = client.post("/api/synthesis", json={"text": "", "speaker_id": 1})
        assert response.status_code == 500  # APIの実装に合わせて500を期待
        assert "音声合成クエリの作成に失敗" in response.json()["detail"]

def test_synthesis_error():
    """音声合成に失敗した場合のテスト"""
    # audio_queryは成功するが、synthesisが失敗するケースをモック
    with patch('requests.post') as mock_post:
        # 1回目の呼び出し (audio_query) は成功
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"dummy": "data"}
        
        # 2回目の呼び出し (synthesis) は失敗
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.json.return_value = {"error": "Synthesis error"}
        
        mock_post.side_effect = [success_response, error_response]
        
        response = client.post("/api/synthesis", json={"text": "テスト", "speaker_id": 1})
        assert response.status_code == 500
        assert "音声合成に失敗" in response.json()["detail"] 