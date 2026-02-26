import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="半導體設備即時監控", layout="wide")

st.title("🛡️ 半導體製程異常預測系統")
st.write("底層架構：Random Forest + FastAPI | 回應速度 < 100ms")

# 側邊欄：模擬數據輸入
st.sidebar.header("實時感測器數值")
temp = st.sidebar.slider("反應爐溫度 (°C)", 60, 100, 75)
press = st.sidebar.slider("腔體壓力 (psi)", 80, 140, 100)
vib = st.sidebar.slider("機台震動頻率 (Hz)", 30, 80, 45)
curr = st.sidebar.slider("馬達電流 (A)", 10, 25, 12)

if st.sidebar.button("即時分析"):
    # 發送請求到 FastAPI
    payload = {"temp": temp, "pressure": press, "vibration": vib, "current": curr}
    
    start_time = time.time()
    response = requests.post("http://127.0.0.1:8100/predict", json=payload).json()
    latency = (time.time() - start_time) * 1000 # 毫秒
    
    # 顯示結果
    col1, col2 = st.columns(2)
    with col1:
        if response["prediction"] == 1:
            st.error(f"⚠️ 偵測到異常風險！ (機率: {response['confidence']*100:.1f}%)")
        else:
            st.success(f"✅ 設備運行穩定 (機率: {response['confidence']*100:.1f}%)")
    
    with col2:
        st.metric("API 延遲", f"{latency:.2f} ms")

# 下方顯示趨勢模擬圖
st.subheader("歷史參數趨勢")
chart_data = pd.DataFrame(np.random.randn(20, 3), columns=['溫度', '壓力', '震動'])
st.line_chart(chart_data)
if st.sidebar.button("即時分析"):
    # 呼叫 API (假設 response 已取得)
    # ...
    
    st.divider()
    
    # 新增：模型解釋性區塊
    st.subheader("🔍 AI 決策依據 (Explainable AI)")
    
    # 模擬從模型取得的特徵重要性 (實際開發可從 API 回傳)
    # 這代表模型認為各個感測器對「故障判斷」的貢獻度
    features = ['溫度', '壓力', '震動頻率', '電流']
    importances = [0.15, 0.45, 0.30, 0.10] # 假設壓力最重要
    
    feat_df = pd.DataFrame({'感測器': features, '貢獻度': importances})
    feat_df = feat_df.sort_values(by='貢獻度', ascending=False)

    # 使用 Bar Chart 顯示
    st.bar_chart(data=feat_df, x='感測器', y='貢獻度')
    
    st.info("💡 診斷報告：當前預測主要基於 **壓力** 與 **震動** 的異常偏移。建議優先檢查腔體密封性。")