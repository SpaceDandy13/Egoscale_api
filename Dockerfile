FROM python:3.11-slim

RUN mkdir -p /bot/data

WORKDIR /bot
COPY requirements.txt .

# 安装依赖
RUN python -m pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置环境变量
ENV ENVIRONMENT=production

# 暴露端口
EXPOSE 8080

# 创建启动脚本
RUN echo '#!/bin/bash\n\
python web_server.py &\n\
python bot.py' > /bot/start.sh && chmod +x /bot/start.sh

ENTRYPOINT ["/bot/start.sh"]