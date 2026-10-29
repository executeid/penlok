# Stage 1: Build static production assets
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency specifications and install cleanly
COPY package*.json ./
RUN npm ci

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Lightweight production web server using Nginx alpine
FROM nginx:alpine

# Copy custom Nginx configuration with SPA routing and health check
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
