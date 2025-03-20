FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 下载中心偏置文件
RUN wget https://github.com/matthias-k/DeepGaze/releases/download/v1.0.0/centerbias_mit1003.npy

# 复制应用代码
COPY . .

# 创建上传和结果目录
RUN mkdir -p uploads results

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
