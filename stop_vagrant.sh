#!/usr/bin/env bash
# ─── 停止所有半導體監控服務 ───

echo "停止服務中..."

pkill -f "uvicorn model_service"  && echo "✅ FastAPI 已停止"     || echo "⚠️  FastAPI 未在執行"
pkill -f "streamlit run"          && echo "✅ Streamlit 已停止"   || echo "⚠️  Streamlit 未在執行"
pkill -f "mqtt_simulator"         && echo "✅ 模擬器已停止"       || echo "⚠️  模擬器未在執行"
sudo systemctl stop mosquitto     && echo "✅ Mosquitto 已停止"   || echo "⚠️  Mosquitto 未在執行"

echo ""
echo "所有服務已停止。"
