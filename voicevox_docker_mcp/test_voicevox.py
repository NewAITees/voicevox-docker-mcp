#!/usr/bin/env python3
"""
VOICEVOXエンジンを使用して音声合成をテストするスクリプト
使用前にVOICEVOXエンジンが起動していることを確認してください
"""

import requests
import json
import argparse
import os
import subprocess
import platform
import simpleaudio as sa
from typing import Dict, Any, Optional, List

# デフォルト設定
DEFAULT_ENGINE_URL = "http://localhost:50021"
DEFAULT_OUTPUT_DIR = "."
DEFAULT_TEXT = "こんにちは、テストです。"
DEFAULT_SPEAKER_ID = 3  # ずんだもん（ノーマル）

def get_speakers(engine_url: str) -> List[Dict[str, Any]]:
    """利用可能な話者の一覧を取得"""
    try:
        response = requests.get(f"{engine_url}/speakers")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"エラー: 話者一覧の取得に失敗しました: {e}")
        return []

def print_speakers(speakers: List[Dict[str, Any]]) -> None:
    """利用可能な話者を表示"""
    print("\n利用可能な話者の一覧:")
    print("-" * 50)
    for speaker in speakers:
        print(f"名前: {speaker['name']}")
        print(f"話者ID: {speaker['speaker_uuid']}")
        
        print("スタイル:")
        for style in speaker.get('styles', []):
            print(f"  - ID: {style['id']}, 名前: {style['name']}")
        print("-" * 50)

def synthesize_voice(engine_url: str, text: str, speaker_id: int, output_path: str) -> bool:
    """テキストから音声を合成"""
    try:
        # 音声合成用のクエリを作成
        query_params = {
            "text": text,
            "speaker": speaker_id
        }
        
        print(f"音声合成クエリを作成中...")
        audio_query_response = requests.post(
            f"{engine_url}/audio_query",
            params=query_params
        )
        audio_query_response.raise_for_status()
        audio_query = audio_query_response.json()
        
        # 音声合成の実行
        print(f"音声を合成中...")
        synthesis_params = {
            "speaker": speaker_id
        }
        
        synthesis_response = requests.post(
            f"{engine_url}/synthesis",
            headers={"Content-Type": "application/json"},
            params=synthesis_params,
            json=audio_query
        )
        synthesis_response.raise_for_status()
        
        # 音声ファイルの保存
        with open(output_path, "wb") as f:
            f.write(synthesis_response.content)
        
        print(f"音声ファイルを保存しました: {output_path}")
        return True
    
    except requests.RequestException as e:
        print(f"エラー: 音声合成に失敗しました: {e}")
        return False

def play_audio(file_path: str) -> None:
    """音声ファイルを再生"""
    try:
        wave_obj = sa.WaveObject.from_wave_file(file_path)
        play_obj = wave_obj.play()
        print("音声を再生中...")
        play_obj.wait_done()  # 再生が終わるまで待機
    except Exception as e:
        print(f"エラー: 音声の再生に失敗しました: {e}")

def main():
    parser = argparse.ArgumentParser(description='VOICEVOXエンジンを使用して音声合成をテストします')
    parser.add_argument('--url', default=DEFAULT_ENGINE_URL, help='VOICEVOXエンジンのURL')
    parser.add_argument('--text', default=DEFAULT_TEXT, help='合成するテキスト')
    parser.add_argument('--speaker-id', type=int, default=DEFAULT_SPEAKER_ID, help='話者ID')
    parser.add_argument('--output', default=os.path.join(DEFAULT_OUTPUT_DIR, 'output.wav'), help='出力ファイルパス')
    parser.add_argument('--list-speakers', action='store_true', help='利用可能な話者を表示')
    parser.add_argument('--play', action='store_true', help='合成後に音声を再生')
    
    args = parser.parse_args()
    
    # VOICEVOXエンジンの接続確認
    try:
        version_response = requests.get(f"{args.url}/version")
        version_response.raise_for_status()
        version = version_response.json()
        print(f"VOICEVOXエンジン接続確認: 成功（バージョン: {version}）")
    except requests.RequestException:
        print(f"エラー: VOICEVOXエンジンに接続できません。エンジンが起動しているか確認してください。")
        print(f"URL: {args.url}")
        return
    
    # 話者一覧の表示
    speakers = get_speakers(args.url)
    if args.list_speakers:
        if speakers:
            print_speakers(speakers)
        return
    
    # 音声合成
    output_path = os.path.abspath(args.output)
    success = synthesize_voice(args.url, args.text, args.speaker_id, output_path)
    
    if success and args.play:
        play_audio(output_path)

if __name__ == "__main__":
    main() 