import os
import json
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. パス設定 ---
# src/visualizer.py の位置を基準に data/key_stats.json を指定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATA_FILE = os.path.join(DATA_DIR, 'key_stats.json')

# 設定
TOP_N = 20  # 表示するキーの上位N個

def load_and_process_data():
    # パス設定で指定した DATA_FILE を確認
    if not os.path.exists(DATA_FILE):
        print(f"エラー: データファイルが見つかりません。\nパス: {DATA_FILE}\nまずは tracker.py を実行してデータを収集してください。")
        return None

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("エラー: JSONファイルが空か、壊れています。")
        return None

    # データが空の場合の対処
    if not data:
        print("データがまだ空です。")
        return None

    # PandasのDataFrameに変換 (行: 時間帯, 列: キー)
    df = pd.DataFrame(data).T.fillna(0) # 転置して、NaNを0で埋める

    # 行（時間帯）の順番を固定
    time_order = ["morning", "daytime", "night", "late_night"]
    # データに存在しない時間帯があってもエラーにならないようにreindex
    df = df.reindex(time_order, fill_value=0)

    # 見やすいように転置しなおす (行: キー, 列: 時間帯)
    df = df.T

    # 合計列を作ってソートし、上位N個を抽出
    df["Total"] = df.sum(axis=1)
    df = df.sort_values("Total", ascending=False).head(TOP_N)
    
    # Total列は描画には不要なので削除
    df = df.drop(columns=["Total"])

    return df

def clean_key_names(index):
    """キー名を見やすく整形する関数"""
    new_index = []
    for key in index:
        # "Key.enter" -> "Enter", "'a'" -> "a" のように整形
        k = str(key).replace("Key.", "").replace("'", "")
        new_index.append(k)
    return new_index

def plot_graph(df):
    # 日本語フォント設定（必要に応じて変更。Windowsなら 'Meiryo', Macなら 'Hiragino Sans' など）
    # plt.rcParams['font.family'] = 'Meiryo' 
    plt.rcParams['figure.figsize'] = (12, 6)
    
    # キー名を整形
    df.index = clean_key_names(df.index)

    # カラー設定（時間帯のイメージ色）
    colors = {
        "morning": "#FFD700",    # 朝: 金色/黄色
        "daytime": "#87CEEB",    # 日中: スカイブルー
        "night": "#FF8C00",      # 夜: オレンジ
        "late_night": "#2F4F4F"  # 深夜: ダークグレー
    }
    # データフレームの列順序に合わせて色リストを作成
    color_list = [colors.get(c, "#333333") for c in df.columns]

    # 積み上げ棒グラフの描画
    ax = df.plot(kind='bar', stacked=True, color=color_list, width=0.8)

    plt.title(f"Top {TOP_N} Keys Usage by Time of Day", fontsize=16)
    plt.xlabel("Keys", fontsize=12)
    plt.ylabel("Count", fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(title="Time Slot", loc='upper right')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # ライブラリがインストールされているか確認
    try:
        import pandas
        import matplotlib
    except ImportError:
        print("エラー: pandas または matplotlib がインストールされていません。")
        print("実行コマンド: pip install pandas matplotlib")
        exit()

    df = load_and_process_data()
    if df is not None:
        print(f"上位 {TOP_N} キーの統計を表示します...")
        print(df) # コンソールにも数値を表示
        plot_graph(df)