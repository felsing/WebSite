# 使用 Python 3.10 作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制 Flask Web 应用和 HTML 文件
COPY app.py /app/
COPY templates /app/templates

# 安装 Flask 和其他依赖
#RUN pip install Flask requests

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露应用运行的端口（例如将端口改为 5100）
EXPOSE 5100

# 设置容器启动时运行 Flask Web 应用
CMD ["python", "app.py"]
