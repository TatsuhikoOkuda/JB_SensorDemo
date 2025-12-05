import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="振動センサー監視システム", layout="wide")

# --- 設定：エリアとセンサーの構成定義 ---
AREAS = [f"エリア {chr(65+i)}" for i in range(13)]
TOTAL_SENSORS = 110

def get_sensors_by_area(area_name):
    area_index = AREAS.index(area_name)
    avg = TOTAL_SENSORS // len(AREAS)
    start_id = area_index * avg + 1
    if area_index == len(AREAS) - 1:
        end_id = TOTAL_SENSORS
    else:
        end_id = start_id + avg - 1
    return [f"Sensor-{str(i).zfill(3)}" for i in range(start_id, end_id + 1)]

# --- セッションと認証 ---
if "auth" in st.query_params and st.query_params["auth"] == "true":
    st.session_state['logged_in'] = True
elif 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- データ生成関数 ---
def generate_area_data(sensors):
    data = []
    for s in sensors:
        is_alert = np.random.random() > 0.95
        if is_alert:
            x = np.random.uniform(0.5, 0.8)
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

def generate_timeseries_data(points=60):
    now = datetime.now()
    dates = [now - timedelta(minutes=i) for i in range(points)]
    dates.reverse()
    df = pd.DataFrame({
        'timestamp': dates,
        'X軸 (G)': np.random.normal(0, 0.1, points),
        'Y軸 (G)': np.random.normal(0, 0.1, points),
        'Z軸 (G)': np.random.normal(1.0, 0.05, points),
        '電圧 (V)': np.random.normal(3.3, 0.01, points)
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

# --- ポップアップ（ダイアログ）定義 ---
try:
    dialog_decorator = st.dialog
except AttributeError:
    dialog_decorator = st.experimental_dialog

@dialog_decorator("詳細トレンド分析", width="large")
def show_sensor_dialog(sensor_id, status):
    st.caption(f"選択されたセンサー: {sensor_id}")
    if status != "正常":
        st.error(f"現在、{status} が発生しています！")
    else:
        st.success("現在の状態は正常です。")
    st.subheader("直近1時間の推移")
    ts_data = generate_timeseries_data()
    st.line_chart(ts_data[['X軸 (G)', 'Y軸 (G)', 'Z軸 (G)']])
    st.subheader("電圧推移")
    st.area_chart(ts_data[['電圧 (V)']], color="#ffaa00")

# --- ログイン画面 ---
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 システムログイン")
        with st.form("login_form"):
            username = st.text_input("ユーザーID", placeholder="admin")
            password = st.text_input("パスワード", type="password", placeholder="admin")
            if st.form_submit_button("ログイン"):
                if username == "admin" and password == "admin":
                    st.session_state['logged_in'] = True
                    st.query_params["auth"] = "true"
                    st.rerun()
                else:
                    st.error("IDまたはパスワードが違います")
    st.stop()

# --- メイン画面 ---
st.sidebar.title("メニュー")
st.sidebar.info(f"監視対象: {len(AREAS)}エリア / 計{TOTAL_SENSORS}センサー")

# メニューに「グラフ分析」を戻しました
menu = st.sidebar.radio(
    "表示切替", 
    ["リアルタイム監視", "グラフ分析", "警報履歴", "システム設定"]
)

if st.sidebar.button("ログアウト"):
    st.session_state['logged_in'] = False
    st.query_params.clear()
    st.rerun()

# --------------------------
# 1. リアルタイム監視画面
# --------------------------
if menu == "リアルタイム監視":
    st.title("📊 リアルタイム監視モニター")
    
    col_sel1, col_sel2 = st.columns([1, 3])
    with col_sel1:
        selected_area = st.selectbox("監視エリアを選択", AREAS)
    
    # データ固定化ロジック
    if 'current_area' not in st.session_state or st.session_state['current_area'] != selected_area:
        target_sensors = get_sensors_by_area(selected_area)
        st.session_state['display_df'] = generate_area_data(target_sensors)
        st.session_state['current_area'] = selected_area

    with col_sel2:
        st.write("") 
        st.write("")
        if st.button("🔄 最新データ取得"):
            target_sensors = get_sensors_by_area(selected_area)
            st.session_state['display_df'] = generate_area_data(target_sensors)
            st.rerun()

    df_current = st.session_state['display_df']
    st.markdown(f"**{selected_area}** のセンサー一覧")
    st.caption("行をクリックすると詳細グラフがポップアップします。")

    def highlight_alert(row):
        return ['background-color: #ffcccc' if row['状態'] != '正常' else '' for _ in row]

    event = st.dataframe(
        df_current.style.apply(highlight_alert, axis=1).format({
            "X軸 (G)": "{:.3f}", "Y軸 (G)": "{:.3f}", "Z軸 (G)": "{:.3f}", "電圧 (V)": "{:.2f}"
        }),
        use_container_width=True,
        hide_index=True,
        height=400,
        on_select="rerun",
        selection_mode="single-row"
    )

    if len(event.selection.rows) > 0:
        selected_index = event.selection.rows[0]
        selected_sensor_id = df_current.iloc[selected_index]["センサーID"]
        selected_status = df_current.iloc[selected_index]["状態"]
        show_sensor_dialog(selected_sensor_id, selected_status)

# --------------------------
# 2. グラフ分析画面 (復活)
# --------------------------
elif menu == "グラフ分析":
    st.title("📈 グラフ分析")
    
    # エリア -> センサー の2段階選択にする
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # エリア選択
        target_area_graph = st.selectbox("エリア選択", AREAS)
        # そのエリアのセンサーリストを取得
        sensors_in_area = get_sensors_by_area(target_area_graph)
        
    with col2:
        # センサー選択
        target_sensor = st.selectbox("対象センサー", sensors_in_area)
        
    with col3:
        # 期間選択
        period = st.selectbox("表示期間", ["1時間", "24時間", "1週間"])

    st.divider()

    # グラフ描画
    df = generate_timeseries_data(points=100) # グラフ用にデータ点を増やす
    
    st.subheader(f"{target_sensor} - 振動データ(XYZ)")
    st.line_chart(df[['X軸 (G)', 'Y軸 (G)', 'Z軸 (G)']])

    st.subheader(f"{target_sensor} - 電圧データ")
    st.area_chart(df[['電圧 (V)']], color="#ffaa00")

# --------------------------
# 3. 警報履歴画面
# --------------------------
elif menu == "警報履歴":
    st.title("⚠️ 全エリア警報履歴")
    history_df = generate_mock_history()
    st.dataframe(history_df, use_container_width=True, hide_index=True)

# --------------------------
# 4. システム設定画面
# --------------------------
elif menu == "システム設定":
    st.title("⚙️ 設定画面")
    st.info("設定画面です（デモ）")
    
    tab1, tab2 = st.tabs(["エリア情報", "閾値設定"])
    with tab1:
        st.table(pd.DataFrame({
            "エリア名": AREAS,
            "割当センサー数": [len(get_sensors_by_area(a)) for a in AREAS]
        }))
    with tab2:
        st.write("全センサー共通設定")
        st.number_input("X軸 警報閾値 (G)", value=0.5)