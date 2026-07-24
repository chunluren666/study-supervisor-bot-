FROM python:3.11-slim

WORKDIR /app

# 只装核心依赖（跳过torch/tensorflow等重包）
COPY requirements_prod.txt .
RUN pip install --no-cache-dir -r requirements_prod.txt

# 复制源码（不包含node_modules和本地数据）
COPY *.py .
COPY wechat_gateway/ wechat_gateway/
COPY templates/ templates/
COPY tests/ tests/

# 创建数据目录
RUN mkdir -p data logs backups

EXPOSE 8000

CMD ["python", "main.py", "--web"]
