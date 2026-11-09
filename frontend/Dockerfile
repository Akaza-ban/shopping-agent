# Giao diện React: build bằng Vite rồi phục vụ file tĩnh bằng Nginx.
# VITE_API_BASE_URL (địa chỉ backend) được gắn vào bản build: đổi địa chỉ backend thì phải build lại.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
# Ảnh nginx thay ${PORT} trong file mẫu lúc khởi động (Railway cấp cổng qua biến PORT)
ENV PORT=8080
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
