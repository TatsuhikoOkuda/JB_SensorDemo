import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="振動センサー監視システム", layout="wide")

# --- 設定：エリアとセンサーの構成 ---
AREAS = [f"エリア {chr(65+i)}" for i in range(13)]
TOTAL_SENSORS = 110
THRESHOLD_X = 0.5
THRESHOLD_Y = 0.5
THRESHOLD_Z = 2.0
THRESHOLD_VOLT_LOW = 2.8

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

if 'table_key' not in st.session_state:
    st.session_state['table_key'] = 0

# --- データ生成関数 ---
def generate_area_data(sensors):
    data = []
    for s in sensors:
        rand_val = np.random.random()
        x = np.random.normal(0.02, 0.05)
        y = np.random.normal(0.02, 0.05)
        z = np.random.normal(1.0, 0.05)
        v = np.random.normal(3.3, 0.02)
        status_list = []
        if rand_val > 0.90:
            if np.random.random() > 0.5:
                x = np.random.uniform(0.6, 0.9)
                status_list.append("X軸")
            if np.random.random() > 0.8:
                y = np.random.uniform(0.6, 0.9)
                status_list.append("Y軸")
            if np.random.random() > 0.9:
                v = np.random.uniform(2.0, 2.7)
                status_list.append("電圧")
        if len(status_list) > 0:
            status_str = "⚠️ 異常 (" + ",".join(status_list) + ")"
        else:
            status_str = "正常"
        data.append({
            "センサーID": s,
            "状態": status_str,
            "X軸 (G)": x,
            "Y軸 (G)": y,
            "Z軸 (G)": z,
            "電圧 (V)": v
        })
    return pd.DataFrame(data)

# ★修正：latest_values引数を追加。ここに辞書を渡すと、グラフの最新値をその値に強制一致させます。
def generate_timeseries_data(points=60, freq='min', latest_values=None):
    now = datetime.now()
    dates = []
    for i in range(points):
        if freq == 'sec':
            d = now - timedelta(seconds=i)
        else:
            d = now - timedelta(minutes=i)
        dates.append(d)
    dates.reverse() # 古い順に並べる
    
    # ベースの乱数生成
    df = pd.DataFrame({
        'timestamp': dates,
        'X軸 (G)': np.random.normal(0, 0.1, points),
        'Y軸 (G)': np.random.normal(0, 0.1, points),
        'Z軸 (G)': np.random.normal(1.0, 0.05, points),
        '電圧 (V)': np.random.normal(3.3, 0.01, points)
    })
    
    # ★重要：最新の値（一番下の行）を、テーブルの値で上書きする
    if latest_values is not None:
        # iloc[-1] は「最後の行（最新日時）」を指します
        df.iloc[-1, df.columns.get_loc('X軸 (G)')] = latest_values['x']
        df.iloc[-1, df.columns.get_loc('Y軸 (G)')] = latest_values['y']
        df.iloc[-1, df.columns.get_loc('Z軸 (G)')] = latest_values['z']
        df.iloc[-1, df.columns.get_loc('電圧 (V)')] = latest_values['v']
        
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
            "X軸異常",
            f"{np.random.uniform(0.6, 1.2):.2f}"
        ])
    return pd.DataFrame(data, columns=["発生日時", "センサーID", "設置エリア", "異常種別", "検測値"])

# --- ポップアップ定義 ---
try:
    dialog_decorator = st.dialog
except AttributeError:
    dialog_decorator = st.experimental_dialog

# ★修正：引数に x, y, z, v を追加して受け取れるようにする
@dialog_decorator("詳細トレンド分析", width="large")
def show_sensor_dialog(sensor_id, status, val_x, val_y, val_z, val_v):
    st.caption(f"選択されたセンサー: {sensor_id}")
    if "異常" in status:
        st.error(f"現在、{status} が発生しています！")
    else:
        st.success("現在の状態は正常です。")
    
    st.subheader("直近1分間の推移 (リアルタイム詳細)")
    
    # ★修正：テーブルの値を「最新値」としてグラフ生成関数に渡す
    latest_params = {'x': val_x, 'y': val_y, 'z': val_z, 'v': val_v}
    ts_data = generate_timeseries_data(points=60, freq='sec', latest_values=latest_params)
    
    st.subheader("振動データ (X, Y, Z)")
    st.line_chart(ts_data[['X軸 (G)', 'Y軸 (G)', 'Z軸 (G)']])
    
    st.subheader("電圧推移")
    st.line_chart(ts_data[['電圧 (V)']], color="#ffaa00")
    
    st.caption("※グラフの右端（最新点）が、一覧表の数値と一致します。")

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
menu = st.sidebar.radio("表示切替", ["リアルタイム監視", "グラフ分析", "異常履歴", "システム設定"])

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
    
    if 'current_area' not in st.session_state or st.session_state['current_area'] != selected_area:
        target_sensors = get_sensors_by_area(selected_area)
        st.session_state['display_df'] = generate_area_data(target_sensors)
        st.session_state['current_area'] = selected_area
        st.session_state['table_key'] += 1 

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

    def highlight_cells(row):
        styles = ['' for _ in row]
        idx_status = row.index.get_loc("状態")
        idx_x = row.index.get_loc("X軸 (G)")
        idx_y = row.index.get_loc("Y軸 (G)")
        idx_z = row.index.get_loc("Z軸 (G)")
        idx_v = row.index.get_loc("電圧 (V)")
        if "異常" in row["状態"]:
            styles[idx_status] = 'color: red; font-weight: bold;'
            if row["X軸 (G)"] >= THRESHOLD_X:
                styles[idx_x] = 'background-color: #ffcccc; color: red; font-weight: bold;'
            if row["Y軸 (G)"] >= THRESHOLD_Y:
                styles[idx_y] = 'background-color: #ffcccc; color: red; font-weight: bold;'
            if row["Z軸 (G)"] >= THRESHOLD_Z:
                styles[idx_z] = 'background-color: #ffcccc; color: red; font-weight: bold;'
            if row["電圧 (V)"] < THRESHOLD_VOLT_LOW:
                styles[idx_v] = 'background-color: #ffcccc; color: red; font-weight: bold;'
        return styles

    table_placeholder = st.empty()
    current_key = f"sensor_table_{st.session_state['table_key']}"
    
    with table_placeholder.container():
        event = st.dataframe(
            df_current.style.apply(highlight_cells, axis=1).format({
                "X軸 (G)": "{:.3f}", "Y軸 (G)": "{:.3f}", "Z軸 (G)": "{:.3f}", "電圧 (V)": "{:.2f}"
            }),
            use_container_width=True,
            hide_index=True,
            height=400,
            on_select="rerun",
            selection_mode="single-row",
            key=current_key
        )

    if len(event.selection.rows) > 0:
        selected_index = event.selection.rows[0]
        # ★修正：選択された行から、4つの数値も取得する
        sel_row = df_current.iloc[selected_index]
        sel_id = sel_row["センサーID"]
        sel_status = sel_row["状態"]
        sel_x = sel_row["X軸 (G)"]
        sel_y = sel_row["Y軸 (G)"]
        sel_z = sel_row["Z軸 (G)"]
        sel_v = sel_row["電圧 (V)"]
        
        st.session_state['table_key'] += 1
        new_key = f"sensor_table_{st.session_state['table_key']}"
        
        with table_placeholder.container():
            st.dataframe(
                df_current.style.apply(highlight_cells, axis=1).format({
                    "X軸 (G)": "{:.3f}", "Y軸 (G)": "{:.3f}", "Z軸 (G)": "{:.3f}", "電圧 (V)": "{:.2f}"
                }),
                use_container_width=True,
                hide_index=True,
                height=400,
                on_select="rerun",
                selection_mode="single-row",
                key=new_key
            )
        
        # 取得した数値を引数として渡す
        show_sensor_dialog(sel_id, sel_status, sel_x, sel_y, sel_z, sel_v)

# --------------------------
# 2. グラフ分析画面
# --------------------------
elif menu == "グラフ分析":
    st.title("📈 グラフ分析")
    col1, col2, col3 = st.columns(3)
    with col1:
        target_area_graph = st.selectbox("エリア選択", AREAS)
        sensors_in_area = get_sensors_by_area(target_area_graph)
    with col2:
        target_sensor = st.selectbox("対象センサー", sensors_in_area)
    with col3:
        period = st.selectbox("表示期間", ["1時間", "24時間", "1週間"])

    st.divider()
    df = generate_timeseries_data(points=100, freq='min')
    st.subheader(f"{target_sensor} - 振動データ(XYZ)")
    st.line_chart(df[['X軸 (G)', 'Y軸 (G)', 'Z軸 (G)']])
    st.subheader(f"{target_sensor} - 電圧データ")
    st.line_chart(df[['電圧 (V)']], color="#ffaa00")

# --------------------------
# 3. 異常履歴画面
# --------------------------
elif menu == "異常履歴":
    st.title("⚠️ 全エリア異常履歴")
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
        c1, c2 = st.columns(2)
        c1.number_input("X/Y軸 異常判定閾値 (G)", value=THRESHOLD_X)
        c2.number_input("Z軸 異常判定閾値 (G)", value=THRESHOLD_Z)