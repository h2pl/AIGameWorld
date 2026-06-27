# SimGameWorld 前端 Dockerfile / Frontend Dockerfile
# === Build Stage / 构建阶段 ===
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install                   # 安装依赖 / Install dependencies
COPY . .
EXPOSE 3000
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "3000"]
