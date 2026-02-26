# 半導體製程異常預測系統

| 項目 | 內容 |
|------|------|
| 專案代號 | semiconductor-monitor |
| 負責人 | （請填入） |
| 狀態 | 進行中 |
| 建立日期 | 2026-02-26 |

---

## 專案目的

模擬一套工廠設備即時健康監控平台，透過 AI 模型分析感測器數值，即時判斷機台是否出現異常，協助工程師在設備故障前提早介入，降低非計畫停機風險。

---

## 系統架構

```
+---------------------------+
|  Streamlit 前端 (port 8601)|
|  dashboard.py             |
+------------+--------------+
             | HTTP POST /predict
             v
+---------------------------+
|  FastAPI 後端 (port 8100) |
|  model_service.py         |
+------------+--------------+
             |
             v
+---------------------------+
|  Random Forest 模型       |
|  scikit-learn             |
+---------------------------+
```

**執行環境：** Vagrant + Ubuntu 22.04 VM（VirtualBox）

---

## 功能說明

### 後端 API（model_service.py）

- 框架：**FastAPI**
- 啟動時自動訓練 Random Forest 分類模型
- 暴露 `POST /predict` 端點
- 輸入 4 項感測器數值，回傳預測結果與信心機率

**請求範例：**

```json
POST http://127.0.0.1:8100/predict
Content-Type: application/json

{
  "temp": 85,
  "pressure": 120,
  "vibration": 60,
  "current": 15
}
```

**回應範例：**

```json
{
  "prediction": 1,
  "confidence": 0.87
}
```

| 欄位 | 說明 |
|------|------|
| `prediction` | 0 = 正常，1 = 異常 |
| `confidence` | 模型對「異常」的信心機率（0.0 ~ 1.0） |

### 前端介面（dashboard.py）

- 框架：**Streamlit**
- 側邊欄滑桿模擬即時感測器數值
- 「即時分析」按鈕呼叫後端 API，顯示判斷結果與 API 延遲
- 歷史參數趨勢折線圖（模擬資料）
- 「AI 決策分析」按鈕顯示特徵重要性長條圖（XAI）

---

## 感測器輸入特徵

| 感測器 | 單位 | 範圍 | 模型重要性 |
|--------|------|------|-----------|
| 腔體壓力 | psi | 80 – 140 | **45%**（最關鍵） |
| 機台震動頻率 | Hz | 30 – 80 | 30% |
| 反應爐溫度 | °C | 60 – 100 | 15% |
| 馬達電流 | A | 10 – 25 | 10% |

---

## 環境需求

| 項目 | 版本／規格 |
|------|-----------|
| OS | Ubuntu 22.04 LTS（Vagrant Box: ubuntu/jammy64） |
| Python | 3.10 |
| 虛擬化 | VirtualBox + Vagrant |
| VM 記憶體 | 2 GB |
| VM CPU | 2 核心 |

**Python 套件（requirements.txt）：**

```
fastapi
uvicorn[standard]
scikit-learn
pandas
streamlit
requests
joblib
```

---

## 部署方式

### 使用 Vagrant（推薦）

```bash
# 1. 啟動並自動 Provision VM
vagrant up

# 2. SSH 進入 VM
vagrant ssh

# 3. 啟動服務
bash ~/app/start_vagrant.sh
```

### 服務存取

| 服務 | URL |
|------|-----|
| Streamlit 前端 | http://localhost:8601 |
| FastAPI Swagger UI | http://localhost:8100/docs |
| FastAPI ReDoc | http://localhost:8100/redoc |

### 使用 Docker（備用）

```bash
docker build -t semiconductor-monitor .
docker run -p 8100:8100 -p 8601:8601 semiconductor-monitor
```

---

## 檔案結構

```
fastapi/
├── model_service.py      # FastAPI 後端 + ML 模型
├── dashboard.py          # Streamlit 前端
├── requirements.txt      # Python 套件清單
├── Vagrantfile           # Vagrant VM 設定
├── provision.sh          # VM 自動安裝腳本
├── start_vagrant.sh      # 服務啟動腳本（VM 內使用）
└── Dockerfile            # Docker 容器設定
```

---

## 串接真實資料說明

目前系統使用 4 筆硬編碼模擬數據，以下說明如何改為串接真實資料。

### Step 1：準備真實訓練資料並儲存模型

將 `model_service.py` 的訓練方式改為從 CSV 載入真實歷史數據，並將模型存成 `.pkl`：

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

# 載入真實歷史數據（欄位需包含 temp, pressure, vibration, current, label）
df = pd.read_csv("sensor_history.csv")
X = df[["temp", "pressure", "vibration", "current"]]
y = df["label"]  # 0 = 正常, 1 = 異常

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# 儲存模型
joblib.dump(clf, "model.pkl")
print(f"Accuracy: {clf.score(X_test, y_test):.2%}")
```

### Step 2：API 啟動時載入模型檔

修改 `model_service.py` 開頭，改從 `.pkl` 載入而非重新訓練：

```python
import joblib

# 啟動時載入訓練好的模型
model = joblib.load("model.pkl")
```

### Step 3：前端改為自動輪詢即時感測器（選擇一種串接方式）

#### 方式 A：資料庫輪詢（最常見）

適用於 MES / SCADA 系統已將數據寫入 DB 的場景：

```python
# 需安裝：pip install pymysql  或  psycopg2
import pymysql
import pandas as pd

def get_latest_sensor_data():
    conn = pymysql.connect(host="db-host", user="user", password="pw", database="scada_db")
    df = pd.read_sql("SELECT temp, pressure, vibration, current FROM sensor_log ORDER BY created_at DESC LIMIT 1", conn)
    conn.close()
    return df.iloc[0].to_dict()
```

#### 方式 B：MQTT 即時訂閱

適用於設備直接透過 MQTT Broker 推送數據的場景：

```python
# 需安裝：pip install paho-mqtt
import paho.mqtt.client as mqtt
import json

latest_data = {}

def on_message(client, userdata, msg):
    global latest_data
    latest_data = json.loads(msg.payload)

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt-broker-host", 1883)
client.subscribe("factory/equipment/sensor")
client.loop_start()  # 背景執行
```

#### 方式 C：OPC-UA 工業協議

適用於 Siemens、Beckhoff 等 PLC 設備：

```python
# 需安裝：pip install opcua
from opcua import Client

client = Client("opc.tcp://plc-host:4840")
client.connect()

node_temp      = client.get_node("ns=2;i=1001")
node_pressure  = client.get_node("ns=2;i=1002")
node_vibration = client.get_node("ns=2;i=1003")
node_current   = client.get_node("ns=2;i=1004")

def get_latest_sensor_data():
    return {
        "temp":      node_temp.get_value(),
        "pressure":  node_pressure.get_value(),
        "vibration": node_vibration.get_value(),
        "current":   node_current.get_value(),
    }
```

### Step 4：Streamlit 自動刷新顯示即時數據

在 `dashboard.py` 加入自動輪詢，不需要手動按按鈕：

```python
import streamlit as st
import requests
import time

# 每 5 秒自動刷新
st.set_page_config(page_title="即時監控", layout="wide")

placeholder = st.empty()

while True:
    # 從後端取得最新感測器數值（後端自己從 DB/MQTT 取）
    response = requests.get("http://127.0.0.1:8100/latest").json()

    with placeholder.container():
        if response["prediction"] == 1:
            st.error(f"⚠️ 偵測到異常！信心度：{response['confidence']*100:.1f}%")
        else:
            st.success(f"✅ 設備正常。信心度：{response['confidence']*100:.1f}%")

        st.metric("溫度", f"{response['temp']} °C")
        st.metric("壓力", f"{response['pressure']} psi")

    time.sleep(5)
    st.rerun()
```

### 串接方式比較

| 方式 | 適用場景 | 複雜度 | 即時性 |
|------|---------|--------|--------|
| CSV 批次載入 | 離線再訓練模型 | 低 | 無 |
| 資料庫輪詢 | MES/SCADA 已有 DB | 低 | 秒級 |
| MQTT 訂閱 | IoT 設備直接推送 | 中 | 毫秒級 |
| OPC-UA | 工業 PLC 設備 | 高 | 毫秒級 |

---

## 已知限制與後續規劃

### 已知限制

- 訓練資料為 4 筆硬編碼模擬數據，模型準確度僅供展示用途
- 前端趨勢圖為隨機模擬數據，非真實歷史數據

### 後續規劃

1. 串接真實 MES / SCADA 歷史數據重新訓練模型
2. 將訓練好的模型存為 `.pkl` 檔，API 啟動時載入
3. 新增 MQTT / OPC-UA 即時資料流串接
4. 新增告警通知機制（Email / LINE Notify）
5. 補充單元測試與 API 整合測試

---

## 問題回報

請在本專案建立 Issue，並填寫以下欄位：

- **類型：** Bug / 功能需求 / 改善
- **優先度：** 低 / 一般 / 高 / 緊急
- **重現步驟：**（Bug 必填）
- **預期結果：**
- **實際結果：**
- **環境資訊：** OS、Vagrant 版本、VirtualBox 版本
