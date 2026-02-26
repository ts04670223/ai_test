"""
mqtt_simulator.py
虛擬感測器模擬器 — 每隔指定秒數發布一筆模擬感測器數據到 MQTT Broker

執行方式（VM 內）：
    python /home/vagrant/app/mqtt_simulator.py

預設連接：localhost:1883
Topic  ：factory/semiconductor/sensor
"""

import json
import random
import time
import argparse
import math
import paho.mqtt.client as mqtt

# ── MQTT 設定 ──────────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC       = "factory/semiconductor/sensor"

# ── 感測器正常範圍 ──────────────────────────────────────────
NORMAL_RANGE = {
    "temp":      (70, 80),    # °C
    "pressure":  (95, 110),   # psi
    "vibration": (40, 55),    # Hz
    "current":   (11, 14),    # A
}

# ── 異常範圍（偶發觸發） ────────────────────────────────────
ANOMALY_RANGE = {
    "temp":      (88, 95),
    "pressure":  (125, 135),
    "vibration": (65, 75),
    "current":   (17, 20),
}


def generate_sensor_data(step: int, anomaly: bool = False) -> dict:
    """產生一筆感測器讀值，加入正弦漂移模擬真實設備"""
    drift = math.sin(step * 0.3) * 2  # 週期性緩慢漂移

    ranges = ANOMALY_RANGE if anomaly else NORMAL_RANGE

    data = {
        "temp":      round(random.uniform(*ranges["temp"])      + drift, 2),
        "pressure":  round(random.uniform(*ranges["pressure"])  + drift, 2),
        "vibration": round(random.uniform(*ranges["vibration"]) + drift * 0.5, 2),
        "current":   round(random.uniform(*ranges["current"])   + drift * 0.1, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "is_simulated_anomaly": anomaly,
    }
    return data


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] 已連線到 Broker {BROKER_HOST}:{BROKER_PORT}")
    else:
        print(f"[MQTT] 連線失敗，錯誤碼：{rc}")


def run(interval: float = 2.0, anomaly_rate: float = 0.15):
    """
    持續發布感測器數據。
    :param interval:     發布間隔（秒），預設 2 秒
    :param anomaly_rate: 觸發模擬異常的機率（0~1），預設 15%
    """
    client = mqtt.Client(client_id="virtual-sensor-01")
    client.on_connect = on_connect
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    print(f"[模擬器] 啟動，發布間隔={interval}s，異常機率={anomaly_rate*100:.0f}%")
    print(f"[模擬器] Topic：{TOPIC}")
    print("[模擬器] 按 Ctrl+C 停止\n")

    step = 0
    try:
        while True:
            anomaly = random.random() < anomaly_rate
            payload = generate_sensor_data(step, anomaly)
            msg     = json.dumps(payload, ensure_ascii=False)

            result = client.publish(TOPIC, msg, qos=1)
            status = "⚠️ 異常" if anomaly else "✅ 正常"
            print(
                f"[{payload['timestamp']}] {status} | "
                f"temp={payload['temp']}°C  "
                f"pressure={payload['pressure']}psi  "
                f"vib={payload['vibration']}Hz  "
                f"curr={payload['current']}A"
            )

            step += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[模擬器] 已停止。")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="半導體感測器 MQTT 虛擬模擬器")
    parser.add_argument("--interval",     type=float, default=2.0,  help="發布間隔（秒），預設 2")
    parser.add_argument("--anomaly-rate", type=float, default=0.15, help="模擬異常機率 0~1，預設 0.15")
    parser.add_argument("--host",         type=str,   default=BROKER_HOST, help="MQTT Broker host")
    parser.add_argument("--port",         type=int,   default=BROKER_PORT, help="MQTT Broker port")
    args = parser.parse_args()

    BROKER_HOST = args.host
    BROKER_PORT = args.port

    run(interval=args.interval, anomaly_rate=args.anomaly_rate)
