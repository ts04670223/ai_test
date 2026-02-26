# 使用輕量級 Python 映像檔
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製專案檔案
COPY . /app

# 安裝依賴 (建議將 pip list 寫在 requirements.txt)
RUN pip install --no-cache-dir fastapi uvicorn scikit-learn pandas streamlit requests

# 暴露 FastAPI (8100) 與 Streamlit (8601) 埠位
EXPOSE 8100
EXPOSE 8601

# 建立一個啟動腳本，同時跑後端與前端
RUN echo '#!/bin/bash\n \
uvicorn model_service:app --host 0.0.0.0 --port 8100 & \n \
streamlit run dashboard.py --server.port 8601 --server.address 0.0.0.0' > start.sh

RUN chmod +x start.sh

# 執行啟動腳本
CMD ["./start.sh"]