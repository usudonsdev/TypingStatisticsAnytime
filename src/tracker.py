import os
import time
import json
import threading
from datetime import datetime
from pynput import keyboard
from pynput import mouse

# --- 設定 ---
# ミス判定の許容時間（秒）。これ以上前の入力を消しても「ミス」とはみなさない。
TYPO_THRESHOLD_SECONDS = 3.0

# 仮想バッファの最大サイズ（文字数）。メモリ節約とプライバシーのため直近のみ保持。
MAX_BUFFER_SIZE = 30

# --- パス設定とファイル名の動的生成 (ここを変更しました) ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 起動時の時刻を取得 (例: 20231027_153045)
start_time = datetime.now().strftime('%Y%m%d_%H%M%S')

# ファイル名に日時を付与 (例: key_stats_20231027_153045.json)
DATA_FILE = os.path.join(DATA_DIR, f'key_stats_{start_time}.json')

print(f"現在のセッションのログファイル: {DATA_FILE}")

# --- グローバル変数 ---
default_stats = {
    "late_night": {},
    "morning": {},
    "daytime": {},
    "night": {}
}

# 毎回新しいファイルなので、読み込み処理はスキップして初期化します
stats = default_stats

# --- クラス定義: 仮想入力バッファ ---
class VirtualInputBuffer:
    def __init__(self):
        # 構造: [{"key": "a", "time": 170000000.0}, ...]
        self.buffer = []
        # カーソル位置（バッファの末尾がデフォルト）
        self.cursor_pos = 0

    def add_key(self, key_name):
        """文字キーが押されたらバッファに追加"""
        now = time.time()
        
        # カーソル位置に挿入（矢印で戻って挿入する場合も考慮）
        self.buffer.insert(self.cursor_pos, {"key": key_name, "time": now})
        self.cursor_pos += 1

        # バッファがあふれたら古いものを捨てる
        if len(self.buffer) > MAX_BUFFER_SIZE:
            self.buffer.pop(0)
            self.cursor_pos = max(0, self.cursor_pos - 1)

    def move_cursor(self, direction):
        """矢印キーによるカーソル移動をシミュレート"""
        if direction == "left":
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif direction == "right":
            self.cursor_pos = min(len(self.buffer), self.cursor_pos + 1)

    def process_backspace(self):
        """
        BackSpace時の処理
        戻り値: (消されたキー名, ミスかどうか判定結果)
        """
        if self.cursor_pos == 0 or not self.buffer:
            return None, False

        # 消される対象（カーソル直前の文字）
        target_idx = self.cursor_pos - 1
        target_item = self.buffer[target_idx]
        
        target_key = target_item["key"]
        timestamp = target_item["time"]
        
        # バッファから削除
        self.buffer.pop(target_idx)
        self.cursor_pos -= 1
        
        # --- 時間経過判定 ---
        # 打鍵から現在までの経過時間
        elapsed = time.time() - timestamp
        
        if elapsed <= TYPO_THRESHOLD_SECONDS:
            return target_key, True # タイプミスと判定
        else:
            return target_key, False # 編集作業と判定（時間は経っている）

    def clear(self):
        """コンテキストが変わったらリセット"""
        self.buffer = []
        self.cursor_pos = 0

# バッファのインスタンス化
input_buffer = VirtualInputBuffer()

# --- 関数群 ---

def get_time_slot():
    hour = datetime.now().hour
    if 0 <= hour < 6: return "late_night"
    elif 6 <= hour < 12: return "morning"
    elif 12 <= hour < 18: return "daytime"
    else: return "night"

def save_data():
    while True:
        time.sleep(60)
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 統計データを保存しました")
        except Exception as e:
            print(f"保存エラー: {e}")

def update_stat(slot, key_name, is_miss=False):
    if slot not in stats:
        stats[slot] = {}
    if key_name not in stats[slot]:
        stats[slot][key_name] = {"total": 0, "miss": 0}
    
    if is_miss:
        stats[slot][key_name]["miss"] += 1
    else:
        stats[slot][key_name]["total"] += 1

def on_press(key):
    try:
        slot = get_time_slot()
        key_name = str(key).replace("'", "")
        
        # 1. BackSpaceの場合
        if key == keyboard.Key.backspace:
            # バッファを確認して判定
            target_key, is_miss = input_buffer.process_backspace()
            
            if target_key and is_miss:
                # ミスと判定された場合のみカウント
                update_stat(slot, target_key, is_miss=True)
                # print(f"ミス検知: {target_key} (矢印移動含む)") # デバッグ

        # 2. 矢印キーの場合
        elif key == keyboard.Key.left:
            input_buffer.move_cursor("left")
        
        elif key == keyboard.Key.right:
            input_buffer.move_cursor("right")

        # 3. Enterやクリック等の場合（文脈リセット）
        elif key == keyboard.Key.enter or key == keyboard.Key.esc:
            # Enterを押した時点で「入力」は完了したとみなし、バッファをクリア
            update_stat(slot, "Enter", is_miss=False) # Enter自体の統計は取る
            input_buffer.clear()

        # 4. 通常の文字入力
        else:
            # 特殊キー以外ならバッファに追加
            is_char = False
            try:
                if hasattr(key, 'char') and key.char:
                    is_char = True
            except:
                pass

            if is_char:
                input_buffer.add_key(key_name)
                update_stat(slot, key_name, is_miss=False)
            elif key == keyboard.Key.space:
                input_buffer.add_key("Space")
                update_stat(slot, "Space", is_miss=False)
            
            # Ctrlなどはバッファに入れないが、統計は取るならここで update_stat だけ呼ぶ

    except Exception as e:
        print(f"エラー: {e}")

def on_release(key):
    if key == keyboard.Key.esc:
        print("終了します...")
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        return False

# メイン処理
if __name__ == "__main__":
    print(f"トラッキングを開始します... (Escキーで終了)")
    print(f"設定: {TYPO_THRESHOLD_SECONDS}秒以内の修正のみをミスとしてカウント")
    
    saver_thread = threading.Thread(target=save_data, daemon=True)
    saver_thread.start()

    def on_click(x, y, button, pressed):
        if pressed:
            input_buffer.clear()

    # context manager (with構文) を使う
    with mouse.Listener(on_click=on_click) as m_listener:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as k_listener:
            k_listener.join()