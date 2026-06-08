# 后端构建
FROM docker.1ms.run/python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 复制配置文件
COPY .env.example ./.env.example

# 创建数据目录并设置权限
RUN mkdir -p /app/data/milvus /app/data/knowledge_base /app/data/logs

# 创建非 root 用户并授权
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# 暴露端口
EXPOSE 8000

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
