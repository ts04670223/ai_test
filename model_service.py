from fastapi import FastAPI
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib # 用於儲存模型
from pydantic import BaseModel

app = FastAPI()

# 模擬半導體數據與預先訓練（實際開發時模型會先存成 .pkl 檔）
def train_init_model():
    # 欄位：溫度, 壓力, 震動頻率, 電流
    X = [[75, 100, 45, 12], [85, 120, 60, 15], [70, 95, 40, 11], [90, 130, 70, 18]]
    y = [0, 1, 0, 1] # 0: 正常, 1: 異常
    clf = RandomForestClassifier(n_estimators=10)
    clf.fit(X, y)
    return clf

model = train_init_model()

class SensorInput(BaseModel):
    temp: float
    pressure: float
    vibration: float
    current: float

@app.post("/predict")
async def predict(data: SensorInput):
    payload = [[data.temp, data.pressure, data.vibration, data.current]]
    res = model.predict(payload)[0]
    prob = model.predict_proba(payload)[0][1]
    return {"prediction": int(res), "confidence": float(prob)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8100)