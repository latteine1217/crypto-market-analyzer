FROM python:3.11-slim

WORKDIR /workspace

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# 複製requirements並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 設定Jupyter配置
RUN jupyter lab --generate-config && \
    echo "c.ServerApp.ip = '0.0.0.0'" >> ~/.jupyter/jupyter_lab_config.py && \
    echo "c.ServerApp.allow_root = True" >> ~/.jupyter/jupyter_lab_config.py

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
