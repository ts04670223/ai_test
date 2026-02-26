#!/usr/bin/env bash
set -e

APP_DIR="/home/vagrant/app"

echo "======================================"
echo " 半導體製程異常預測系統 — Vagrant Provision"
echo "======================================"

# 更新套件列表
echo "[1/5] 更新 apt 套件列表..."
apt-get update -q

# 安裝 Python 3 與工具
echo "[2/5] 安裝 Python 3.10 及相依套件..."
apt-get install -y -q python3 python3-pip python3-venv

# 建立虛擬環境並安裝 Python 套件
echo "[3/5] 建立 Python 虛擬環境並安裝套件..."
python3 -m venv /home/vagrant/venv
chown -R vagrant:vagrant /home/vagrant/venv

sudo -u vagrant /home/vagrant/venv/bin/pip install --upgrade pip -q
sudo -u vagrant /home/vagrant/venv/bin/pip install -r "$APP_DIR/requirements.txt" -q

# 建立 systemd 服務，讓機器重開後自動啟動
echo "[4/5] 建立 systemd 服務..."
cat > /etc/systemd/system/semiconductor-monitor.service <<EOF
[Unit]
Description=半導體製程異常預測系統（FastAPI + Streamlit）
After=network.target

[Service]
Type=forking
User=vagrant
WorkingDirectory=$APP_DIR
Environment="PATH=/home/vagrant/venv/bin"

# 先啟動 FastAPI 後端
ExecStartPre=/home/vagrant/venv/bin/uvicorn model_service:app --host 0.0.0.0 --port 8000 &
# 再啟動 Streamlit 前端
ExecStart=/bin/bash -c '/home/vagrant/venv/bin/uvicorn model_service:app --host 0.0.0.0 --port 8100 & /home/vagrant/venv/bin/streamlit run $APP_DIR/dashboard.py --server.port 8601 --server.address 0.0.0.0'

Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable semiconductor-monitor.service

# 建立便捷啟動腳本
echo "[5/5] 建立便捷啟動腳本 start.sh..."
cat > "$APP_DIR/start_vagrant.sh" <<'STARTSCRIPT'
#!/usr/bin/env bash
# ─── 在 Vagrant VM 內直接執行此腳本即可同時啟動前後端 ───
VENV="/home/vagrant/venv/bin"
APP="/home/vagrant/app"

echo "啟動 FastAPI 後端 (port 8100)..."
"$VENV/uvicorn" model_service:app --host 0.0.0.0 --port 8100 &
FASTAPI_PID=$!

sleep 2
echo "啟動 Streamlit 前端 (port 8601)..."
"$VENV/streamlit" run "$APP/dashboard.py" --server.port 8601 --server.address 0.0.0.0 &
STREAMLIT_PID=$!

echo ""
echo "======================================"
echo " 服務已啟動！"
echo " FastAPI  → http://localhost:8100"
echo " Streamlit → http://localhost:8601"
echo " 按 Ctrl+C 停止全部服務"
echo "======================================"

wait $FASTAPI_PID $STREAMLIT_PID
STARTSCRIPT

chmod +x "$APP_DIR/start_vagrant.sh"
chown vagrant:vagrant "$APP_DIR/start_vagrant.sh"

echo ""
echo "======================================"
echo " Provision 完成！"
echo " 執行 'vagrant ssh' 進入 VM"
echo " 執行 'bash ~/app/start_vagrant.sh' 或"
echo " 執行 'sudo systemctl start semiconductor-monitor' 啟動服務"
echo " FastAPI   → http://localhost:8100/docs"
echo " Streamlit → http://localhost:8601"
echo "======================================"
