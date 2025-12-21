FROM python:3.9.23

# 基础环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装系统依赖（如你用到了 mysqlclient / cryptography）
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝 requirements，最大化利用缓存
COPY requirements.txt .

RUN pip install \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# 再拷贝代码（这一步只在代码变更时触发）
COPY app ./app

EXPOSE 8000

CMD ["python", "-m", "app.main"]



# docker build -t signin-backend:1.0 .
#docker run -d --name signin-api -p 8000:8000 -v D:\:/app/app/logs signin-backend:1.0
# docker save -o signin-backend-1.0.tar signin-backend:1.0
