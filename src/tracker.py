import os
import time
import json
import threading
from datetime import datetime
from pynput import keyboard

# --- 1. パス設定（ここが重要！） ---
# 現在のファイル（src/tracker.py）のある場所を基準に、親フォルダの data/ を指定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATA_FILE = os.path.join(DATA_DIR, 'key_stats.json')

# dataフォルダが存在しない場合は自動作成
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- 2. データの初期化と読み込み ---
# デフォルトのデータ構造
default_stats = {
    "late_night": {},
    "morning": {},
    "daytime": {},
    "night": {}
}

# 起動時に既存のファイルがあれば読み込む（これがないと再起動でデータが消えます）
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            stats = json.load(f)
        print("既存のデータを読み込みました。")
    except Exception as e:
        print(f"データ読み込みエラー（新規作成します）: {e}")
        stats = default_stats
else:
    stats = default_stats

# --- 3. ロジック部分 ---

def get_time_slot():
    """現在の時刻から時間帯キーを返す"""
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return "late_night"
    elif 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "daytime"
    else:
        return "night"

def save_data():
    """定期的に統計データをファイルに保存する"""
    while True:
        time.sleep(60)  # 1分ごとに保存
        try:
            # ファイル書き込み中は一時的にデータをコピーしてエラーを防ぐ
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 統計データを保存しました")
        except Exception as e:
            print(f"保存エラー: {e}")

def on_press(key):
    """キーが押された時の処理"""
    try:
        # キー名を文字列化
        key_name = str(key).replace("'", "")
        
        # 現在の時間帯を取得
        slot = get_time_slot()
        
        # 該当する時間帯・キーのカウントを増やす
        # もし読み込んだデータに新しい時間帯キーがなくても対応できるように安全策
        if slot not in stats:
            stats[slot] = {}
            
        if key_name not in stats[slot]:
            stats[slot][key_name] = 0
        stats[slot][key_name] += 1

    except Exception as e:
        print(f"エラー: {e}")

def on_release(key):
    """Escキーで終了するための処理"""
    if key == keyboard.Key.esc:
        print("終了します...")
        # 終了時にも保存
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        return False

# メイン処理
if __name__ == "__main__":
    print(f"保存先: {DATA_FILE}")
    print("トラッキングを開始します... (Escキーで終了)")
    
    # 保存用スレッド開始
    saver_thread = threading.Thread(target=save_data, daemon=True)
    saver_thread.start()

    # キーボードリスナー開始
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()