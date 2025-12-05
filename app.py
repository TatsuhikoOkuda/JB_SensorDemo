import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="振動センサー監視システム", layout="wide")

# --- 設定：エリアとセンサーの構成定義 ---
# 13エリアに110個のセンサーを割り振る（デモ用ロジック）
AREAS = [f"エリア {chr(65+i)}" for i in range(13)] # エリアA ~ エリアM
TOTAL_SENSORS = 110

def get_sensors_by_area(area_name):
    """エリア名を受け取り、そのエリアに所属するセンサーリストを返す"""
    area_index = AREAS.index(area_name)
    
    # センサーを均等に割り振る計算
    avg = TOTAL_SENSORS // len(AREAS)
    start_id = area_index * avg + 1
    # 最後のエリアだけ残りを全部入れる
    if area_index == len(AREAS) - 1:
        end_id = TOTAL_SENSORS
    else:
        end_id = start_id + avg - 1
        
    sensors = [f"Sensor-{str(i).zfill(3)}" for i in range(start_id, end_id + 1)]
    return sensors

# --- セッション状態の初期化（ログイン維持） ---
if "auth" in st.query_params and st.query_params["auth"] == "true":
    st.session_state['logged_in'] = True
elif 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- データ生成関数 ---
def generate_area_data(sensors):
    """指定されたセンサーリストの現在値を生成する"""
    data = []
    for s in sensors:
        # デモ用にランダム値生成（たまに異常値を混ぜる）
        is_alert = np.random.random() > 0.95 # 5%の確率で異常
        
        if is_alert:
            x = np.random.uniform(0.5, 0.8) # 閾値超え
            status = "⚠️ 警報"
        else:
            x = np.random.normal(0.02, 0.05)
            status = "正常"
            
        data.append({
            "センサーID": s,
            "状態": status,
            "X軸 (G)": x,
            "Y軸 (G)": np.random.normal(0.01, 0.05),
            "Z軸 (G)": np.random.normal(0.98, 0.05),
            "電圧 (V)": np.random.normal(3.3, 0.02)
        })
    return pd.DataFrame(data)

def generate_timeseries_data():
    now = datetime.now()
    dates = [now - timedelta(minutes=i) for i in range(60)]
    dates.reverse()
    df = pd.DataFrame({
        'timestamp': dates,
        'X軸 (G)': np.random.normal(0, 0.1, 60),
        'Y軸 (G)': np.random.normal(0, 0.1, 60),
        'Z軸 (G)': np.random.normal(1.0, 0.05, 60),
        '電圧 (V)': np.random.normal(3.3, 0.01, 60)
    })
    return df.set_index('timestamp')

def generate_mock_history():
    data = []
    now = datetime.now()
    for i in range(10):
        t = now - timedelta(hours=i*2)
        data.append([
            t.strftime('%Y-%m-%d %H:%M:%S'),
            f"Sensor-{str(np.random.randint(1,110)).zfill(3)}",
            np.random.choice(AREAS),
            "X軸振動超過",
            f"{np.random.uniform(0.6, 1.2):.2f}"
        ])
    return pd.DataFrame(data, columns=["発生日時", "センサーID", "設置エリア", "警報種別", "検測値"])

# --- 1. ログイン画面 ---
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 システムログイン")
        with st.form("login_form"):
            username = st.text_input("ユーザーID", placeholder="admin")
            password = st.text_input("パスワード", type="password", placeholder="admin")
            submit = st.form_submit_button("ログイン")
            if submit:
                if username == "admin" and password == "admin":
                    st.session_state['logged_in'] = True
                    st.query_params["auth"] = "true"
                    st.rerun()
                else:
                    st.error("IDまたはパスワードが違います")
    st.stop()

# --- ログイン後のメイン画面 ---

st.sidebar.title("メニュー")
st.sidebar.info(f"監視対象: {len(AREAS)}エリア / 計{TOTAL_SENSORS}センサー")

menu = st.sidebar.radio(
    "表示切替",
    ["リアルタイム監視", "警報履歴", "システム設定"]
)

if st.sidebar.button("ログアウト"):
    st.session_state['logged_in'] = False
    st.query_params.clear()
    st.rerun()

# --- コンテンツ表示 ---

if menu == "リアルタイム監視":
    st.title("📊 リアルタイム監視モニター")
    
    # 1. エリア選択
    col_sel1, col_sel2 = st.columns([1, 3])
    with col_sel1:
        selected_area = st.selectbox("監視エリアを選択", AREAS)
    
    # 対象エリアのセンサー一覧を取得してデータを生成
    target_sensors = get_sensors_by_area(selected_area)
    df_current = generate_area_data(target_sensors)
    
    st.markdown(f"**{selected_area}** のセンサー一覧 (設置数: {len(target_sensors)}台)")
    
    # 2. 数値一覧表示（スタイリング付き）
    # 警報が出ている行を目立たせるハイライト関数
    def highlight_alert(row):
        return ['background-color: #ffcccc' if row['状態'] != '正常' else '' for _ in row]

    st.dataframe(
        df_current.style.apply(highlight_alert, axis=1).format({
            "X軸 (G)": "{:.3f}", "Y軸 (G)": "{:.3f}", "Z軸 (G)": "{:.3f}", "電圧 (V)": "{:.2f}"
        }),
        use_container_width=True,
        hide_index=True,
        height=300 # 高さを固定してスクロールさせる
    )
    
    st.divider() # 区切り線
    
    # 3. トレンドグラフ表示（センサー選択式）
    st.subheader("📈 詳細トレンド分析")
    
    col_g1, col_g2 = st.columns([1, 3])
    with col_g1:
        # 上記のエリア内にあるセンサーから1つ選ぶ
        selected_sensor_graph = st.selectbox("グラフを表示するセンサー", target_sensors)
        
    with col_g2:
        # グラフ描画
        ts_data = generate_timeseries_data()
        st.caption(f"{selected_sensor_graph} の直近1時間の推移")
        st.line_chart(ts_data[['X軸 (G)', 'Y軸 (G)', 'Z軸 (G)']])

elif menu == "警報履歴":
    st.title("⚠️ 全エリア警報履歴")
    
    # フィルタ
    col1, col2, col3 = st.columns(3)
    with col1: st.selectbox("エリア絞り込み", ["全エリア"] + AREAS)
    with col2: st.date_input("開始日")
    with col3: st.date_input("終了日")

    history_df = generate_mock_history()
    st.dataframe(history_df, use_container_width=True, hide_index=True)

elif menu == "システム設定":
    st.title("⚙️ 設定画面")
    st.info("デモ画面のため、設定値は保存されません。")
    
    tab1, tab2 = st.tabs(["エリア・センサー管理", "一括閾値設定"])
    
    with tab1:
        st.subheader("センサー登録状況")
        st.table(pd.DataFrame({
            "エリア名": AREAS,
            "割当センサー数": [len(get_sensors_by_area(a)) for a in AREAS]
        }))
        
    with tab2:
        st.subheader("共通閾値設定")
        c1, c2 = st.columns(2)
        c1.number_input("X/Y軸 警報閾値 (G)", value=0.5)
        c2.number_input("Z軸 警報閾値 (G)", value=1.5)