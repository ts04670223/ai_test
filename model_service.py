from fastapi import FastAPI, HTTPException
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import json
import threading
from datetime import datetime
from pydantic import BaseModel
import paho.mqtt.client as mqtt

app = FastAPI(title="半導體製程異常預測 API")

# ── MQTT 設定 ──────────────────────────────────────────────
MQTT_BROKER = "localhost"
MQTT_PORT   = 1883
MQTT_TOPIC  = "factory/semiconductor/sensor"

# ── 共享狀態（MQTT 背景執行緒更新） ────────────────────────
latest_reading: dict = {}
latest_result:  dict = {}

# ── 模型初始化 ──────────────────────────────────────────────
def train_init_model():
    # 欄位：溫度, 壓力, 震動頻率, 電流
    X = [[75, 100, 45, 12], [85, 120, 60, 15], [70, 95, 40, 11], [90, 130, 70, 18]]
    y = [0, 1, 0, 1]  # 0: 正常, 1: 異常
    clf = RandomForestClassifier(n_estimators=10, random_state=42)
    clf.fit(X, y)
    return clf

try:
    model = joblib.load("model.pkl")
    print("[模型] 已從 model.pkl 載入")
except FileNotFoundError:
    model = train_init_model()
    print("[模型] 使用內建示範模型（未找到 model.pkl）")


def run_predict(data: dict) -> dict:
    payload = [[data["temp"], data["pressure"], data["vibration"], data["current"]]]
    res  = model.predict(payload)[0]
    prob = model.predict_proba(payload)[0][1]
    return {"prediction": int(res), "confidence": round(float(prob), 4)}


# ── MQTT 背景訂閱 ───────────────────────────────────────────
def on_mqtt_message(client, userdata, msg):
    global latest_reading, latest_result
    try:
        data = json.loads(msg.payload)
        latest_reading = data
        result = run_predict(data)
        latest_result = {**result, "timestamp": data.get("timestamp", datetime.now().isoformat())}
    except Exception as e:
        print(f"[MQTT] 解析訊息失敗：{e}")


def start_mqtt_listener():
    client = mqtt.Client(client_id="model-service-subscriber")
    client.on_message = on_mqtt_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.subscribe(MQTT_TOPIC, qos=1)
        print(f"[MQTT] 已訂閱 {MQTT_TOPIC}")
        client.loop_forever()
    except Exception as e:
        print(f"[MQTT] 無法連線到 Broker：{e}（手動 /predict 模式仍可用）")


# FastAPI 啟動時在背景執行 MQTT 訂閱
mqtt_thread = threading.Thread(target=start_mqtt_listener, daemon=True)
mqtt_thread.start()


# ── API Schema ──────────────────────────────────────────────
class SensorInput(BaseModel):
    temp:      float
    pressure:  float
    vibration: float
    current:   float


# ── 端點 ───────────────────────────────────────────────────
@app.post("/predict", summary="手動輸入感測器數值進行預測")
async def predict(data: SensorInput):
    payload = {"temp": data.temp, "pressure": data.pressure,
               "vibration": data.vibration, "current": data.current}
    return run_predict(payload)


@app.get("/latest", summary="取得最新一筆 MQTT 感測器數據與預測結果")
async def get_latest():
    if not latest_reading:
        raise HTTPException(status_code=503, detail="尚未收到任何 MQTT 感測器數據，請確認模擬器是否啟動。")
    return {
        "sensor":     latest_reading,
        "prediction": latest_result,
    }


@app.get("/health", summary="健康檢查")
async def health():
    return {"status": "ok", "mqtt_connected": bool(latest_reading)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
