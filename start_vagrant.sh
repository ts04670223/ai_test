#!/usr/bin/env bash
# ─── 在 Vagrant VM 內直接執行此腳本即可同時啟動前後端 ───
VENV="/home/vagrant/venv/bin"
APP="/home/vagrant/app"

# ── Step 1：確認 / 自動安裝 Mosquitto ──────────────────────
echo "檢查 Mosquitto MQTT Broker..."
if ! command -v mosquitto &>/dev/null; then
  echo "[Mosquitto] 未安裝，自動安裝中..."
  sudo apt-get update -q
  sudo apt-get install -y -q mosquitto mosquitto-clients
fi

# 寫入最簡設定（覆蓋整個主設定，避免 conf.d 衝突）
sudo tee /etc/mosquitto/mosquitto.conf > /dev/null <<'MQTTCONF'
pid_file /run/mosquitto/mosquitto.pid
persistence true
persistence_location /var/lib/mosquitto/
log_dest file /var/log/mosquitto/mosquitto.log
listener 1883 0.0.0.0
allow_anonymous true
MQTTCONF

# 確保目錄存在且有權限
sudo mkdir -p /var/log/mosquitto /var/lib/mosquitto /run/mosquitto
sudo chown -R mosquitto:mosquitto /var/log/mosquitto /var/lib/mosquitto /run/mosquitto 2>/dev/null || true

sudo systemctl daemon-reload
sudo systemctl enable mosquitto &>/dev/null
sudo systemctl restart mosquitto

if systemctl is-active --quiet mosquitto; then
  echo "[Mosquitto] ✅ 已運行於 port 1883"
else
  echo "[Mosquitto] ❌ 啟動失敗，錯誤訊息："
  sudo journalctl -u mosquitto -n 20 --no-pager
  exit 1
fi

# ── Step 2：確認 / 自動安裝 Python 套件 ────────────────────
echo "檢查 Python 套件..."
if ! "$VENV/python" -c "import paho" &>/dev/null; then
  echo "[pip] paho-mqtt 未安裝，自動安裝中..."
  "$VENV/pip" install --quiet paho-mqtt
fi
if ! "$VENV/python" -c "import fastapi" &>/dev/null; then
  echo "[pip] 套件不完整，重新安裝 requirements.txt..."
  "$VENV/pip" install --quiet -r "$APP/requirements.txt"
fi
echo "[pip] ✅ 套件確認完成"

# ── Step 3：啟動 FastAPI 後端 ───────────────────────────────
echo "啟動 FastAPI 後端 (port 8100)..."
cd "$APP"
"$VENV/uvicorn" model_service:app --host 0.0.0.0 --port 8100 &
FASTAPI_PID=$!

# 等待 FastAPI 真正就緒（最多 30 秒）
echo -n "等待 FastAPI 就緒"
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8100/health > /dev/null 2>&1; then
    echo " OK"
    break
  fi
  echo -n "."
  sleep 1
done

# ── Step 4：啟動 MQTT 虛擬模擬器 ───────────────────────────
echo "啟動 MQTT 虛擬模擬器..."
"$VENV/python" "$APP/mqtt_simulator.py" --interval 2 --anomaly-rate 0.15 &
SIMULATOR_PID=$!

# ── Step 5：啟動 Streamlit 前端 ────────────────────────────
echo "啟動 Streamlit 前端 (port 8601)..."
"$VENV/streamlit" run "$APP/dashboard.py" --server.port 8601 --server.address 0.0.0.0 &
STREAMLIT_PID=$!

echo ""
echo "======================================"
echo " 服務已啟動！"
echo " FastAPI   → http://localhost:8100/docs"
 echo " Streamlit → http://localhost:8601"
 echo " MQTT Topic → factory/semiconductor/sensor"
echo " 按 Ctrl+C 停止全部服務"
echo "======================================"

wait $FASTAPI_PID $SIMULATOR_PID $STREAMLIT_PID
