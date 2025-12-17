import os
import json
import glob
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# --- 設定 ---
MERGE_ALL_LOGS = True 

# --- パス設定 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 日本語フォント設定
try:
    plt.rcParams['font.family'] = 'MS Gothic' 
except:
    pass

def load_data():
    """ ログファイルの読み込み処理 """
    pattern = os.path.join(DATA_DIR, 'key_stats_*.json')
    files = glob.glob(pattern)
    
    if not files:
        print("データファイルが見つかりません。")
        return None

    files.sort()

    if not MERGE_ALL_LOGS:
        target_file = files[-1]
        print(f"最新のログファイルを読み込みます: {os.path.basename(target_file)}")
        with open(target_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print(f"{len(files)} 個のログファイルを合算しています...")
        merged_stats = { "late_night": {}, "morning": {}, "daytime": {}, "night": {} }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for slot, keys_data in data.items():
                        if slot not in merged_stats: merged_stats[slot] = {}
                        for key, counts in keys_data.items():
                            if key not in merged_stats[slot]:
                                merged_stats[slot][key] = {"total": 0, "miss": 0}
                            merged_stats[slot][key]["total"] += counts.get("total", 0)
                            merged_stats[slot][key]["miss"] += counts.get("miss", 0)
            except Exception as e:
                print(f"ファイル読み込みエラー ({file_path}): {e}")
        return merged_stats

def analyze_and_plot(stats):
    if not stats: return

    # 全時間帯合算
    total_key_stats = {}
    for slot in stats:
        for key, val in stats[slot].items():
            if key not in total_key_stats:
                total_key_stats[key] = {"total": 0, "miss": 0}
            total_key_stats[key]["total"] += val["total"]
            total_key_stats[key]["miss"] += val["miss"]

    # プロット用データ作成
    plot_data = []
    for key, val in total_key_stats.items():
        total = val["total"]
        miss = val["miss"]
        if total > 0:
            miss_rate = (miss / total) * 100
            if total >= 5: # 母数が少なすぎるものは除外
                plot_data.append((key, miss_rate, total))

    plot_data.sort(key=lambda x: x[1], reverse=True)
    top_miss_keys = plot_data[:20]

    if not top_miss_keys:
        print("表示できるデータが足りません。")
        return

    # --- グラフ描画 ---
    keys = [x[0] for x in top_miss_keys]
    rates = [x[1] for x in top_miss_keys]
    counts = [x[2] for x in top_miss_keys]

    # フィギュア作成（ここでキーイベントを受け取る準備をする）
    fig = plt.figure(figsize=(12, 6))

    # ★追加: キー入力で閉じる処理
    def on_key(event):
        if event.key in ['escape', 'q']:
            print("グラフを閉じます...")
            plt.close(fig) # ウィンドウを閉じる

    # イベントを登録
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    # 棒グラフ描画
    bars = plt.bar(keys, rates, color='salmon', alpha=0.7)
    
    title_text = f'タイプミス率が高いキー TOP20 ({ "全期間合算" if MERGE_ALL_LOGS else "最新セッション" })'
    plt.xlabel('キー')
    plt.ylabel('ミス率 (%)')
    plt.title(f"{title_text}\n[Esc] または [Q] キーで終了") # タイトルに操作説明を追加
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.ylim(0, max(rates) * 1.2)

    for bar, rate, count in zip(bars, rates, counts):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, height, 
                f'{rate:.1f}%\n(n={count})', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    stats_data = load_data()
    analyze_and_plot(stats_data)