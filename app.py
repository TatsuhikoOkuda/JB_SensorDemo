import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="振動センサー監視システム", layout="wide")

# --- セッション状態の初期化（ログイン状態管理） ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- ダミーデータ生成関数 ---
def generate_mock_history():
    # 過去の警報履歴ダミー
    data = []
    now = datetime.now()
    for i in range(5):
        t = now - timedelta(hours=i*5)
        data.append([
            t.strftime('%Y-%m-%d %H:%M:%S'),
            f"センサー No.{np.random.randint(1,4)}",
            np.random.choice(["X軸振動超過", "電圧低下"]),
            f"{np.random.uniform(2.0, 5.0):.2f}"
        ])
    return pd.DataFrame(data, columns=["発生日時", "センサー名", "警報種別", "検測値"])

def generate_timeseries_data():
    # グラフ用時系列データダミー (1時間分)
    now = datetime.now()
    dates = [now - timedelta(minutes=i) for i in range(60)]
    dates.reverse()
    
    df = pd.DataFrame({
        'timestamp': dates,
        'X軸 (G)': np.random.normal(0, 0.1, 60),
        'Y軸 (G)': np.random.normal(0, 0.1, 60),
        'Z軸 (G)': np.random.normal(1.0, 0.05, 60), # 重力加速度想定
        '電圧 (V)': np.random.normal(3.3, 0.01, 60)
    })
    return df.set_index('timestamp')

# --- 1. ログイン画面 ---
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 システムログイン")
        st.write("振動センサー監視システムへようこそ")
        
        with st.form("login_form"):
            username = st.text_input("ユーザーID", placeholder="admin")
            password = st.text_input("パスワード", type="password", placeholder="admin")
            submit = st.form_submit_button("ログイン")
            
            if submit:
                # デモ用なので admin/admin で通す
                if username == "admin" and password == "admin":
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("IDまたはパスワードが違います (admin/admin)")
    st.stop() # ログインしていない場合はここで処理を止める

# --- ログイン後のメイン画面 ---

# サイドバー（メニュー画面相当）
st.sidebar.title("メニュー")
st.sidebar.write(f"User: admin")
menu = st.sidebar.radio(
    "表示切替",
    ["リアルタイム監視", "グラフ分析", "警報履歴", "システム設定"]
)

if st.sidebar.button("ログアウト"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 画面ごとのコンテンツ ---

if menu == "リアルタイム監視":
    st.title("📊 リアルタイム数値表示")
    st.markdown("各センサーからの最新データを表示しています。（5秒更新）")

    # センサー選択
    sensor_select = st.selectbox("監視対象センサー選択", ["センサー No.1 (モーターA)", "センサー No.2 (ファンB)", "センサー No.3 (ポンプC)"])

    col1, col2, col3, col4 = st.columns(4)
    
    # リアルタイム感を出すために乱数生成
    mock_x = np.random.normal(0.02, 0.05)
    mock_y = np.random.normal(0.01, 0.05)
    mock_z = np.random.normal(0.98, 0.05)
    mock_v = np.random.normal(3.29, 0.02)

    # メトリクス表示
    col1.metric("X軸 加速度", f"{mock_x:.3f} G", "0.01 G")
    col2.metric("Y軸 加速度", f"{mock_y:.3f} G", "-0.02 G")
    col3.metric("Z軸 加速度", f"{mock_z:.3f} G", "0.05 G")
    col4.metric("バッテリー電圧", f"{mock_v:.2f} V", "正常")

    st.info("※ デモのため、リロードするたびに数値が変動します。")
    
    # 簡易グラフ
    st.subheader("直近1分のトレンド")
    chart_data = pd.DataFrame(
        np.random.randn(20, 3) * 0.1 + [0, 0, 1], # Z軸は1G付近
        columns=['X', 'Y', 'Z']
    )
    st.line_chart(chart_data)


elif menu == "グラフ分析":
    st.title("📈 数値グラフ化表示")
    
    col1, col2 = st.columns(2)
    with col1:
        target_sensor = st.selectbox("対象センサー", ["センサー No.1", "センサー No.2"])
    with col2:
        period = st.selectbox("表示期間", ["1時間", "24時間", "1週間"])

    df = generate_timeseries_data()

    st.subheader(f"{target_sensor} - 振動データ(XYZ)")
    st.line_chart(df[['X軸 (G)', 'Y軸 (G)', 'Z軸 (G)']])

    st.subheader(f"{target_sensor} - 電圧データ")
    st.area_chart(df[['電圧 (V)']], color="#ffaa00")


elif menu == "警報履歴":
    st.title("⚠️ 警報履歴画面")
    st.markdown("閾値を超過し、警報が出力された履歴です。")

    # フィルタ機能（デモ用の飾り）
    with st.expander("検索フィルター"):
        col1, col2 = st.columns(2)
        col1.date_input("開始日")
        col2.date_input("終了日")

    history_df = generate_mock_history()
    
    # データフレーム表示（テーブル）
    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True
    )
    
    st.download_button(
        label="CSVダウンロード",
        data=history_df.to_csv().encode('utf-8'),
        file_name='alarm_history.csv',
        mime='text/csv',
    )


elif menu == "システム設定":
    st.title("⚙️ 設定画面")
    
    tab1, tab2 = st.tabs(["閾値設定", "通知設定"])
    
    with tab1:
        st.subheader("センサー閾値設定")
        sensor_setting = st.selectbox("設定対象", ["センサー No.1", "センサー No.2"])
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.number_input("X軸 警報閾値 (G)", value=0.5, step=0.1)
        with col_b:
            st.number_input("Y軸 警報閾値 (G)", value=0.5, step=0.1)
        with col_c:
            st.number_input("Z軸 警報閾値 (G)", value=1.5, step=0.1)
            
        st.number_input("電圧低下 警報閾値 (V)", value=2.8, step=0.1)
        
        if st.button("閾値を保存"):
            st.success(f"{sensor_setting} の設定を更新しました。")

    with tab2:
        st.subheader("警報メール設定")
        email = st.text_input("送信先メールアドレス", "admin@example.com")
        st.checkbox("警報時に即時送信する", value=True)
        st.checkbox("復帰時にも通知する", value=False)
        
        if st.button("メール設定を保存"):
            st.success("メール通知設定を保存しました。")