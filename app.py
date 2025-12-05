import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="振動センサー監視システム", layout="wide")

# --- CSS: ボタンの色設定 ---
st.markdown("""
    <style>
    /* 設定保存ボタンを水色にする */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #00BFFF !important; /* DeepSkyBlue */
        border-color: #00BFFF !important;
        color: white !important;
        font-weight: bold !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #009ACD !important;
        border-color: #009ACD !important;
        color: white !important;
    }
    div[data-testid="stFormSubmitButton"] > button:active {
        background-color: #00BFFF !important;
        border-color: #00BFFF !important;
        color: white !important;
    }
    /* テスト送信ボタンなども水色にする */
    button[kind="primary"] {
        background-color: #00BFFF !important;
        border-color: #00BFFF !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 設定：エリアとセンサーの構成 ---
AREAS = [f"エリア {chr(65+i)}" for i in range(13)]
TOTAL_SENSORS = 110

DEFAULT_THRESHOLDS = {
    "x": 0.5,
    "y": 0.5,
    "z": 2.0,
    "v": 2.8
}

def get_sensors_by_area(area_name):
    area_index = AREAS.index(area_name)
    avg = TOTAL_SENSORS // len(AREAS)
    start_id = area_index * avg + 1
    if area_index == len(AREAS) - 1:
        end_id = TOTAL_SENSORS
    else:
        end_id = start_id + avg - 1
    return [f"Sensor-{str(i).zfill(3)}" for i in range(start_id, end_id + 1)]

# --- セッション状態 ---
if "auth" in st.query_params and st.query_params["auth"] == "true":
    st.session_state['logged_in'] = True
elif 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if 'table_key' not in st.session_state:
    st.session_state['table_key'] = 0

if 'sensor_configs' not in st.session_state:
    st.session_state['sensor_configs'] = {} 

if 'email_config' not in st.session_state:
    st.session_state['email_config'] = {
        "address": "admin@example.com",
        "enable_alert": True
    }

if 'reset_counts' not in st.session_state:
    st.session_state['reset_counts'] = {}

# --- ヘルパー関数 ---
def get_sensor_thresholds(sensor_id):
    if sensor_id in st.session_state['sensor_configs']:
        return st.session_state['sensor_configs'][sensor_id]
    else:
        return DEFAULT_THRESHOLDS

# --- データ生成関数 ---
def generate_area_data(sensors):
    data = []
    for s in sensors:
        limits = get_sensor_thresholds(s)
        rand_val = np.random.random()
        x = np.random.normal(0.02, 0.05)
        y = np.random.normal(0.02, 0.05)
        z = np.random.normal(1.0, 0.05)
        v = np.random.normal(3.3, 0.02)
        status_list = []

        if rand_val > 0.90:
            if np.random.random() > 0.5:
                x = limits['x'] + np.random.uniform(0.1, 0.5)
                status_list.append("X軸")
            if np.random.random() > 0.8:
                y = limits['y'] + np.random.uniform(0.1, 0.5)
                status_list.append("Y軸")
            if np.random.random() > 0.9:
                v = limits['v'] - np.random.uniform(0.1, 0.5)
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

def generate_timeseries_data(points=60, freq='min', latest_values=None):
    now = datetime.now()
    dates = []
    for i in range(points):
        if freq == 'sec':
            d = now - timedelta(seconds=i)
        else:
            d = now - timedelta(minutes=i)
        dates.append(d)
    dates.reverse()
    
    df = pd.DataFrame({
        'timestamp': dates,
        'X軸 (G)': np.random.normal(0, 0.1, points),
        'Y軸 (G)': np.random.normal(0, 0.1, points),
        'Z軸 (G)': np.random.normal(1.0, 0.05, points),
        '電圧 (V)': np.random.normal(3.3, 0.01, points)
    })
    
    if latest_values is not None:
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

@dialog_decorator("詳細トレンド分析", width="large")
def show_sensor_dialog(sensor_id, status, val_x, val_y, val_z, val_v):
    st.caption(f"選択されたセンサー: {sensor_id}")
    if "異常" in status:
        st.error(f"現在、{status} が発生しています！")
        if st.session_state['email_config']['enable_alert']:
            st.divider()
            st.warning(f"📩 異常検知のため、管理者 ({st.session_state['email_config']['address']}) へ自動通報が行われます。")
    else:
        st.success("現在の状態は正常です。")
    
    st.subheader("直近1分間の推移 (リアルタイム詳細)")
    latest_params = {'x': val_x, 'y': val_y, 'z': val_z, 'v': val_v}
    ts_data = generate_timeseries_data(points=60, freq='sec', latest_values=latest_params)
    
    st.subheader("振動データ (X, Y, Z)")
    st.line_chart(ts_data[['X軸 (G)', 'Y軸 (G)', 'Z軸 (G)']])
    st.subheader("電圧推移")
    st.line_chart(ts_data[['電圧 (V)']], color="#ffaa00")

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
                    st.error("❌ ログイン失敗：IDまたはパスワードが違います")
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
        s_id = row["センサーID"]
        limits = get_sensor_thresholds(s_id)
        idx_status = row.index.get_loc("状態")
        idx_x = row.index.get_loc("X軸 (G)")
        idx_y = row.index.get_loc("Y軸 (G)")
        idx_z = row.index.get_loc("Z軸 (G)")
        idx_v = row.index.get_loc("電圧 (V)")

        if "異常" in row["状態"]:
            styles[idx_status] = 'color: red; font-weight: bold;'
            if row["X軸 (G)"] >= limits['x']:
                styles[idx_x] = 'background-color: #ffcccc; color: red; font-weight: bold;'
            if row["Y軸 (G)"] >= limits['y']:
                styles[idx_y] = 'background-color: #ffcccc; color: red; font-weight: bold;'
            if row["Z軸 (G)"] >= limits['z']:
                styles[idx_z] = 'background-color: #ffcccc; color: red; font-weight: bold;'
            if row["電圧 (V)"] < limits['v']:
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
    st.title("⚙️ システム設定")
    
    tab_mail, tab_threshold = st.tabs(["📩 メール通報設定", "📏 センサー閾値設定"])
    
    # --- タブ1: メール設定 ---
    with tab_mail:
        st.subheader("警報メール通知設定")
        with st.form("email_form"):
            current_email = st.session_state['email_config']['address']
            current_enable = st.session_state['email_config']['enable_alert']
            
            new_email = st.text_input("通報先メールアドレス", value=current_email)
            new_enable = st.checkbox("異常発生時にメールを送信する", value=current_enable)
            
            submitted = st.form_submit_button("設定を保存")
        
        msg_placeholder_mail = st.empty()

        if submitted:
            if not new_email or "@" not in new_email:
                 msg_placeholder_mail.error("❌ 失敗：有効なメールアドレスを入力してください。")
            else:
                st.session_state['email_config']['address'] = new_email
                st.session_state['email_config']['enable_alert'] = new_enable
                msg_placeholder_mail.success("✅ 成功：メール設定を保存しました。")
                time.sleep(2)
                msg_placeholder_mail.empty()
                st.rerun()

        st.divider()
        st.subheader("送信テスト")
        st.write("設定したアドレスにテストメールを送信します（シミュレーション）。")
        if st.button("テストメール送信実行", type="primary"):
            msg_placeholder_test = st.empty()
            if st.session_state['email_config']['enable_alert']:
                with st.spinner("メールサーバーに接続中..."):
                    time.sleep(1.0)
                st.toast(f"送信成功！ {st.session_state['email_config']['address']} にメールを送りました。", icon="📧")
                msg_placeholder_test.success(f"✅ [送信成功] 宛先: {st.session_state['email_config']['address']}")
                time.sleep(3)
                msg_placeholder_test.empty()
            else:
                msg_placeholder_test.error("❌ 失敗：メール通知機能が無効になっています。")

    # --- タブ2: 閾値設定 ---
    with tab_threshold:
        st.subheader("センサー別 閾値詳細設定")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            th_area = st.selectbox("エリア選択", AREAS, key="th_area")
        with col_t2:
            th_sensors = get_sensors_by_area(th_area)
            th_target = st.selectbox("設定するセンサーを選択", th_sensors, key="th_target")
        
        # リセット回数の初期化
        if th_target not in st.session_state['reset_counts']:
            st.session_state['reset_counts'][th_target] = 0
            
        current_limits = get_sensor_thresholds(th_target)
        is_custom = th_target in st.session_state['sensor_configs']
        
        st.markdown(f"**{th_target} の設定状況:** " + ("🛠 個別設定中" if is_custom else "📦 デフォルト値"))

        with st.form("threshold_form"):
            c1, c2, c3, c4 = st.columns(4)
            # リセット回数をKeyに含める
            reset_id = st.session_state['reset_counts'][th_target]
            key_suffix = f"{th_target}_{reset_id}"
            
            with c1:
                new_x = st.number_input("X軸 閾値 (G)", value=float(current_limits['x']), step=0.1, format="%.2f", key=f"x_{key_suffix}")
            with c2:
                new_y = st.number_input("Y軸 閾値 (G)", value=float(current_limits['y']), step=0.1, format="%.2f", key=f"y_{key_suffix}")
            with c3:
                new_z = st.number_input("Z軸 閾値 (G)", value=float(current_limits['z']), step=0.1, format="%.2f", key=f"z_{key_suffix}")
            with c4:
                new_v = st.number_input("電圧 下限値 (V)", value=float(current_limits['v']), step=0.1, format="%.2f", key=f"v_{key_suffix}")
            
            save_col, _ = st.columns([1, 5])
            with save_col:
                submitted_th = st.form_submit_button("設定を保存")
        
        msg_placeholder_th = st.empty()

        if submitted_th:
            if new_x < 0 or new_y < 0 or new_z < 0:
                 msg_placeholder_th.error("❌ 失敗：振動閾値に負の数は設定できません。")
            elif new_v < 0:
                 msg_placeholder_th.error("❌ 失敗：電圧値に負の数は設定できません。")
            else:
                # ★追加ロジック：入力値がデフォルト値と同じかどうかチェックする
                is_default = (
                    new_x == DEFAULT_THRESHOLDS['x'] and
                    new_y == DEFAULT_THRESHOLDS['y'] and
                    new_z == DEFAULT_THRESHOLDS['z'] and
                    new_v == DEFAULT_THRESHOLDS['v']
                )

                if is_default:
                    # デフォルト値と同じなら、個別設定から削除する
                    if th_target in st.session_state['sensor_configs']:
                        del st.session_state['sensor_configs'][th_target]
                    
                    # リセットカウンタを上げて、画面の状態もリフレッシュする
                    st.session_state['reset_counts'][th_target] += 1
                    msg_placeholder_th.success(f"✅ 設定変更：{th_target} の値がデフォルトと同じため、標準設定として扱います。")
                else:
                    # 違う値なら、個別設定として保存
                    st.session_state['sensor_configs'][th_target] = {
                        'x': new_x, 'y': new_y, 'z': new_z, 'v': new_v
                    }
                    msg_placeholder_th.success(f"✅ 成功：{th_target} の個別設定を保存しました。")
                
                time.sleep(1.5)
                msg_placeholder_th.empty()
                st.rerun()

        # デフォルトに戻すボタン
        if is_custom:
            if st.button("デフォルト設定に戻す"):
                del st.session_state['sensor_configs'][th_target]
                st.session_state['reset_counts'][th_target] += 1
                
                msg_placeholder_reset = st.empty()
                msg_placeholder_reset.success(f"✅ 成功：{th_target} をデフォルト設定に戻しました。")
                time.sleep(1.5)
                msg_placeholder_reset.empty()
                st.rerun()

        st.divider()
        st.caption(f"現在のデフォルト値: X={DEFAULT_THRESHOLDS['x']}G, Y={DEFAULT_THRESHOLDS['y']}G, Z={DEFAULT_THRESHOLDS['z']}G, 電圧={DEFAULT_THRESHOLDS['v']}V")