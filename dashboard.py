import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="半導體設備即時監控", layout="wide")
st.title("🛡️ 半導體製程異常預測系統")
st.write("底層架構：Random Forest + FastAPI + MQTT | 回應速度 < 100ms")

API_BASE = "http://127.0.0.1:8100"

# ── 側邊欄：模式切換 ────────────────────────────────────────
st.sidebar.header("⚙️ 控制面板")
mode = st.sidebar.radio("資料來源", ["🔴 MQTT 即時監控", "🔧 手動輸入測試"])
refresh_interval = st.sidebar.slider("自動刷新間隔（秒）", 1, 10, 3,
                                     disabled=(mode != "🔴 MQTT 即時監控"))

# ── 歷史紀錄（session state） ───────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []

# ── 主畫面佔位元件 ──────────────────────────────────────────
status_placeholder  = st.empty()
metrics_placeholder = st.empty()
chart_placeholder   = st.empty()
xai_placeholder     = st.empty()


def render_result(sensor: dict, result: dict, latency_ms: float = None):
    pred       = result.get("prediction", -1)
    confidence = result.get("confidence", 0)
    ts         = sensor.get("timestamp", "—")

    with status_placeholder.container():
        col_status, col_latency, col_time = st.columns(3)
        with col_status:
            if pred == 1:
                st.error(f"⚠️ 偵測到異常風險！(機率: {confidence*100:.1f}%)")
            else:
                st.success(f"✅ 設備運行穩定 (機率: {confidence*100:.1f}%)")
        with col_latency:
            if latency_ms is not None:
                st.metric("API 延遲", f"{latency_ms:.1f} ms")
        with col_time:
            st.metric("資料時間", ts)

    with metrics_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡 溫度",     f"{sensor.get('temp', '—')} °C")
        c2.metric("💨 壓力",     f"{sensor.get('pressure', '—')} psi")
        c3.metric("📳 震動頻率", f"{sensor.get('vibration', '—')} Hz")
        c4.metric("⚡ 電流",     f"{sensor.get('current', '—')} A")

    # 追加歷史紀錄（最多保留 50 筆）
    st.session_state.history.append({
        "時間":   ts,
        "溫度":   sensor.get("temp"),
        "壓力":   sensor.get("pressure"),
        "震動":   sensor.get("vibration"),
        "電流":   sensor.get("current"),
        "預測":   "異常" if pred == 1 else "正常",
        "信心度": round(confidence * 100, 1),
    })
    st.session_state.history = st.session_state.history[-50:]

    with chart_placeholder.container():
        st.subheader("📈 歷史趨勢（最近 50 筆）")
        hist_df = pd.DataFrame(st.session_state.history)
        if len(hist_df) > 1:
            st.line_chart(hist_df.set_index("時間")[["溫度", "壓力", "震動", "電流"]])

    with xai_placeholder.container():
        st.subheader("🔍 AI 決策依據（特徵重要性）")
        feat_df = pd.DataFrame({
            "感測器": ["壓力", "震動頻率", "溫度", "電流"],
            "貢獻度": [0.45,   0.30,       0.15,   0.10],
        })
        st.bar_chart(data=feat_df, x="感測器", y="貢獻度")
        st.info("💡 當前模型最倚重 **壓力** 與 **震動** 指標，建議優先確認腔體密封性。")


# ══════════════════════════════════════════════════════════════
# 模式 A：MQTT 即時監控（自動輪詢 /latest）
# ══════════════════════════════════════════════════════════════
if mode == "🔴 MQTT 即時監控":
    st.sidebar.info(f"每 {refresh_interval} 秒向 FastAPI 拉取最新 MQTT 數據")
    if st.sidebar.button("🗑️ 清除歷史紀錄"):
        st.session_state.history = []

    try:
        t0       = time.time()
        response = requests.get(f"{API_BASE}/latest", timeout=5)
        latency  = (time.time() - t0) * 1000

        if response.status_code == 200:
            data   = response.json()
            render_result(data["sensor"], data["prediction"], latency)
        elif response.status_code == 503:
            st.warning("⏳ 尚未收到 MQTT 數據，請確認模擬器已啟動：\n```\npython ~/app/mqtt_simulator.py\n```")
        else:
            st.error(f"後端錯誤：{response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error("❌ 無法連線到 FastAPI 後端（port 8100）。\n請執行：`bash ~/app/start_vagrant.sh`")
    except requests.exceptions.Timeout:
        st.warning("⏱️ 後端回應逾時，請確認服務是否正常運作。")
    except Exception as e:
        st.error(f"未預期錯誤：{e}")

    time.sleep(refresh_interval)
    st.rerun()


# ══════════════════════════════════════════════════════════════
# 模式 B：手動輸入（滑桿測試）
# ══════════════════════════════════════════════════════════════
else:
    st.sidebar.header("🔧 感測器數值")
    temp  = st.sidebar.slider("反應爐溫度 (°C)",  60,  100, 75)
    press = st.sidebar.slider("腔體壓力 (psi)",    80,  140, 100)
    vib   = st.sidebar.slider("機台震動頻率 (Hz)", 30,  80,  45)
    curr  = st.sidebar.slider("馬達電流 (A)",       10,  25,  12)

    if st.sidebar.button("▶️ 即時分析", key="btn_predict"):
        payload = {"temp": temp, "pressure": press, "vibration": vib, "current": curr}
        try:
            t0       = time.time()
            response = requests.post(f"{API_BASE}/predict", json=payload, timeout=5).json()
            latency  = (time.time() - t0) * 1000
            sensor_mock = {**payload, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
            render_result(sensor_mock, response, latency)
        except requests.exceptions.ConnectionError:
            st.error("❌ 無法連線到 FastAPI 後端（port 8100）。請先啟動後端服務：\n`uvicorn model_service:app --host 0.0.0.0 --port 8100`")
        except requests.exceptions.Timeout:
            st.warning("⏱️ 請求逾時，FastAPI 回應過慢，請確認後端是否正常運作。")
        except Exception as e:
            st.error(f"未預期錯誤：{e}")