# 前端构建
FROM docker.1ms.run/node:20-alpine AS frontend

WORKDIR /app

# 安装依赖
COPY package.json package-lock.json* ./
RUN npm install --registry=https://registry.npmmirror.com

# 复制源码
COPY . .

# 构建
RUN npm run build

# 生产环境
FROM docker.1ms.run/nginx:alpine
COPY --from=frontend /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
