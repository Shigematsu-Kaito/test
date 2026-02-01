import streamlit as st
import folium
from streamlit_folium import st_folium
import os
import math
from dotenv import load_dotenv

from mapbox_api import Mapboxapi
from openweather_api import Weatherapi
from db_handler import DBHandler

# 環境変数
load_dotenv()
MAPBOX_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# インスタンス化
mapbox = Mapboxapi(MAPBOX_TOKEN)
weather = Weatherapi(WEATHER_API_KEY)
db = DBHandler()

# --- 共通関数 ---
def haversine_distance(coord1, coord2):
    R = 6371
    lon1, lat1 = map(math.radians, coord1)
    lon2, lat2 = map(math.radians, coord2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

# 履歴ボタン用コールバック（エラー回避用）
def set_search_params(start, end):
    st.session_state["start_input"] = start
    st.session_state["end_input"] = end
    st.session_state["trigger_search"] = True

# --- Google Maps風スタイル適用関数（UIは見やすいまま維持） ---
def apply_custom_style():
    st.markdown("""
        <style>
            /* 全体の背景色 */
            .stApp { background-color: #f0f2f5; }
            
            /* メインエリア（地図）の余白を削除して画面いっぱいに */
            .block-container {
                padding-top: 0rem !important;
                padding-bottom: 0rem !important;
                padding-left: 0rem !important;
                padding-right: 0rem !important;
                max-width: 100% !important;
            }

            /* サイドバーを「浮いているカード」風にする */
            [data-testid="stSidebar"] {
                background-color: rgba(255, 255, 255, 0.95) !important;
                box-shadow: 5px 0 15px rgba(0,0,0,0.1);
                border-right: none !important;
                padding-top: 1rem;
                width: 350px !important;
                z-index: 99999;
            }
            
            /* サイドバー内の文字色調整 */
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div {
                color: #202124 !important;
            }

            /* ボタンのデザイン（Google Blue） */
            .stButton button {
                background-color: #1a73e8 !important;
                color: white !important;
                border-radius: 24px !important;
                border: none !important;
                font-weight: bold !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            }
            
            /* ヘッダーの装飾バーを消す */
            header[data-testid="stHeader"] { display: none; }
        </style>
    """, unsafe_allow_html=True)

# --- 画面1: ログイン・登録画面 ---
def login_screen():
    st.title("🔐 ルート天気マップ - ログイン")
    
    tab1, tab2 = st.tabs(["ログイン", "新規登録"])

    with tab1:
        st.subheader("ログイン")
        l_user = st.text_input("ユーザー名", key="login_user")
        l_pass = st.text_input("パスワード", type="password", key="login_pass")
        if st.button("ログインする"):
            user_id = db.login_user(l_user, l_pass)
            if user_id:
                st.session_state["user_id"] = user_id
                st.session_state["username"] = l_user
                st.success("ログイン成功！")
                st.rerun()
            else:
                st.error("ユーザー名かパスワードが間違っています")

    with tab2:
        st.subheader("新規登録")
        r_user = st.text_input("ユーザー名", key="reg_user")
        r_pass = st.text_input("パスワード", type="password", key="reg_pass")
        if st.button("登録する"):
            if r_user and r_pass:
                if db.register_user(r_user, r_pass):
                    st.success("登録完了！ログインタブからログインしてください。")
                else:
                    st.error("そのユーザー名は既に使用されています。")
            else:
                st.warning("全ての項目を入力してください。")

# --- 画面2: メインアプリ画面 ---
def app_screen():
    # スタイルを適用
    apply_custom_style()

    # --- サイドバー：操作パネル ---
    with st.sidebar:
        st.title("🚗 天気マップ")
        st.caption(f"Login: **{st.session_state['username']}**")
        
        if st.button("ログアウト", key="logout_btn"):
            st.session_state.clear()
            st.rerun()
        st.markdown("---")

        st.header("検索条件")
        # ここでキーを設定しておくと session_state["start_input"] が自動生成されます
        st.text_input("出発地", value="東京駅", key="start_input")
        st.text_input("目的地", value="大阪駅", key="end_input")
        interval_km = st.number_input("天気表示間隔 (km)", min_value=10, value=30, step=10)
        search_btn = st.button("ルート検索", use_container_width=True)

        # 履歴機能
        st.markdown("---")
        with st.expander("📜 検索履歴を開く"):
            history_df = db.get_history(st.session_state["user_id"])
            if not history_df.empty:
                for index, row in history_df.iterrows():
                    # 履歴ボタン（エラー回避のためcallback使用）
                    st.button(
                        f"{row['start_place']} → {row['end_place']}", 
                        key=f"hist_btn_{row['id']}",
                        on_click=set_search_params,
                        args=(row['start_place'], row['end_place'])
                    )
            else:
                st.caption("履歴はありません")

    # セッション初期化
    if "folium_map" not in st.session_state:
        st.session_state["folium_map"] = None
    if "search_info" not in st.session_state:
        st.session_state["search_info"] = ""
    if "trigger_search" not in st.session_state:
        st.session_state["trigger_search"] = False

    # --- メインロジック（検索実行） ---
    if search_btn or st.session_state["trigger_search"]:
        if st.session_state["trigger_search"]:
            st.session_state["trigger_search"] = False
        
        current_start = st.session_state["start_input"]
        current_end = st.session_state["end_input"]

        if current_start and current_end:
            with st.spinner("ルートと天気を取得中..."):
                start_coords = mapbox.get_coordinates(current_start)
                end_coords = mapbox.get_coordinates(current_end)

                if not start_coords or not end_coords:
                    st.sidebar.error("場所が見つかりませんでした。")
                else:
                    route_data = mapbox.get_route(start_coords, end_coords)
                    
                    if route_data:
                        route_line_mapbox = route_data["geometry"]["coordinates"]
                        route_line_folium = [[p[1], p[0]] for p in route_line_mapbox]
                        
                        dist_km_val = round(route_data['distance'] / 1000, 1)
                        db.add_route(st.session_state["user_id"], current_start, current_end, dist_km_val)

                        # --- 地点抽出ロジック ---
                        checkpoints = []
                        acc_dist = 0
                        next_target = interval_km
                        for i in range(len(route_line_mapbox) - 1):
                            p1 = route_line_mapbox[i]
                            p2 = route_line_mapbox[i+1]
                            dist = haversine_distance(p1, p2)
                            acc_dist += dist
                            if acc_dist >= next_target:
                                checkpoints.append(p2)
                                next_target += interval_km

                        # --- 地図作成（ご指定の設定に変更） ---
                        center_lat = (start_coords[1] + end_coords[1]) / 2
                        center_lon = (start_coords[0] + end_coords[0]) / 2
                        
                        # ★ ご希望の設定 ★
                        m = folium.Map(location=[center_lat, center_lon], zoom_start=7)
                        folium.PolyLine(locations=route_line_folium, color="blue", weight=5, opacity=0.7).add_to(m)

                        # --- マーカー追加関数 ---
                        def add_marker(coords, name, is_main=False):
                            lat, lon = coords[1], coords[0]
                            w = weather.get_weather(lat, lon)
                            if w:
                                emoji = w.get('emoji', '❓')
                                description = w['description']
                                temp = w['temp']
                                popup_html = f"""<div style="font-family:sans-serif;text-align:center;">
                                                <div style="font-size:30px;">{emoji}</div>
                                                <b>{name}</b><br>{description}<br>{temp}℃</div>"""
                                icon_size = 40 if is_main else 30
                                icon = folium.DivIcon(
                                    html=f"""<div style="font-size:{icon_size}px;text-align:center;text-shadow:2px 2px 2px white;">{emoji}</div>""",
                                    icon_size=(icon_size, icon_size),
                                    icon_anchor=(icon_size//2, icon_size//2)
                                )
                                folium.Marker(
                                    location=[lat, lon], 
                                    icon=icon, 
                                    popup=folium.Popup(popup_html, max_width=200)
                                ).add_to(m)

                        # マーカー配置
                        add_marker(start_coords, "出発地", True)
                        
                        progress = st.sidebar.progress(0)
                        for i, cp in enumerate(checkpoints):
                            add_marker(cp, f"{i+1}地点")
                            progress.progress((i+1)/len(checkpoints))
                        progress.empty()
                        
                        add_marker(end_coords, "目的地", True)

                        st.session_state["folium_map"] = m
                        st.session_state["search_info"] = f"総距離: {dist_km_val} km / 天気ポイント: {len(checkpoints)}箇所"
                        st.sidebar.success(st.session_state["search_info"])
                    else:
                        st.sidebar.error("ルートが見つかりませんでした。")

    # --- 地図表示エリア（画面全体） ---
    if st.session_state["folium_map"] is not None:
        st_folium(
            st.session_state["folium_map"], 
            width=2000,   # 画面幅いっぱいに
            height=900,   # 高さも十分に
            returned_objects=[]
        )
    else:
        # 地図がない時のプレビュー用（デフォルト設定に合わせる）
        m_default = folium.Map(location=[35.6812, 139.7671], zoom_start=5)
        st_folium(m_default, width=2000, height=900, returned_objects=[])

# --- メイン制御 ---
def main():
    # ページ設定
    st.set_page_config(
        page_title="ルート天気マップ", 
        layout="wide", 
        initial_sidebar_state="expanded"
    )
    
    # APIキーチェック
    if not MAPBOX_TOKEN or not WEATHER_API_KEY:
        st.error("APIキー設定エラー")
        return

    # ログイン状態の管理
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None

    # ログインしていればアプリ画面、していなければログイン画面
    if st.session_state["user_id"] is None:
        login_screen()
    else:
        app_screen()

if __name__ == "__main__":
    main()