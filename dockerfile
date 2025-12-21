FROM python:3.9.23

# 1. 环境变量（防止 pyc、缓冲）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 2. 工作目录
WORKDIR /app

# 3. 先拷贝依赖（利用缓存）
COPY requirements.txt .

RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt


# 4. 再拷贝项目代码
COPY . .

# 5. 暴露端口（只是说明）
EXPOSE 8000

# 6. 启动命令
CMD ["python","-m","app.main"]



# docker build -t signin-backend:1.0 .
#docker run -d --name signin-api -p 8000:8000 -v D:\:/app/app/logs signin-backend:1.0
# docker save -o signin-backend-1.0.tar signin-backend:1.0
