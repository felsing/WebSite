# 使用 Python 3.10 作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制 Flask Web 应用和 HTML 文件
COPY app.py /app/
COPY templates /app/templates

# 安装 Flask 和其他依赖
RUN pip install Flask requests

# 设置容器启动时运行 Flask Web 应用
CMD ["python", "app.py"]
