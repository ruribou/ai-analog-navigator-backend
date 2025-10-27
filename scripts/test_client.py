#!/usr/bin/env python3
import sys
import os
# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""
テスト用クライアント
音声ファイルをAPIにアップロードして文字起こし・校正をテストします
"""

import requests
import time
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def test_health():
    """ヘルスチェックテスト"""
    print("=== ヘルスチェック ===")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API正常動作中")
            print(f"   Whisperモデル: {data['whisper_model']}")
            print(f"   LM Studio URL: {data['lm_studio_url']}")
            print(f"   サポート形式: {', '.join(data['supported_formats'])}")
            return True
        else:
            print(f"❌ ヘルスチェック失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API接続エラー: {e}")
        return False

def test_transcription(audio_file_path: str, correct_text: bool = True):
    """音声文字起こしテスト"""
    print(f"\n=== 音声処理テスト ===")
    print(f"ファイル: {audio_file_path}")
    print(f"文章校正: {'有効' if correct_text else '無効'}")
    
    if not os.path.exists(audio_file_path):
        print(f"❌ ファイルが見つかりません: {audio_file_path}")
        return False
    
    try:
        with open(audio_file_path, "rb") as f:
            files = {"audio_file": f}
            data = {"correct_text": correct_text}
            
            print("📤 ファイルアップロード中...")
            start_time = time.time()
            
            response = requests.post(
                f"{API_BASE_URL}/transcribe",
                files=files,
                data=data,
                timeout=120  # 2分のタイムアウト
            )
            
            upload_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 処理成功 (アップロード時間: {upload_time:.2f}秒)")
                print(f"\n📝 文字起こし結果:")
                print(f"   {result['transcribed_text']}")
                
                if result.get('corrected_text'):
                    print(f"\n✏️  校正結果:")
                    print(f"   {result['corrected_text']}")
                
                print(f"\n⏱️  処理時間: {result['processing_time']:.2f}秒")
                return True
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                print(f"❌ 処理失敗: {response.status_code}")
                print(f"   エラー: {error_data.get('error', response.text)}")
                return False
                
    except requests.exceptions.Timeout:
        print("❌ タイムアウトエラー: 処理に時間がかかりすぎています")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    """メイン関数"""
    print("🎤 AI Analog Navigator Backend テストクライアント")
    print("=" * 50)
    
    # ヘルスチェック
    if not test_health():
        print("\n❌ APIが利用できません。サーバーが起動しているか確認してください。")
        sys.exit(1)
    
    # コマンドライン引数から音声ファイルパスを取得
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        # デフォルトのテストファイルを探す
        test_files = [
            "test_audio.mp3",
            "test_audio.wav",
            "sample.mp3",
            "sample.wav"
        ]
        
        audio_file = None
        for test_file in test_files:
            if os.path.exists(test_file):
                audio_file = test_file
                break
        
        if not audio_file:
            print(f"\n📁 テスト用音声ファイルが見つかりません。")
            print(f"   以下のいずれかの方法でテストしてください:")
            print(f"   1. python test_client.py <音声ファイルパス>")
            print(f"   2. test_audio.mp3 または test_audio.wav を配置")
            sys.exit(1)
    
    # 文字起こし + 校正テスト
    success1 = test_transcription(audio_file, correct_text=True)
    
    # 文字起こしのみテスト
    success2 = test_transcription(audio_file, correct_text=False)
    
    print(f"\n{'=' * 50}")
    if success1 and success2:
        print("✅ すべてのテストが成功しました！")
    else:
        print("❌ 一部のテストが失敗しました。")
        sys.exit(1)

if __name__ == "__main__":
    main()
