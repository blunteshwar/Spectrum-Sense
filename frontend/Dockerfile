# Build stage
FROM node:20-alpine as build

WORKDIR /app

# Copy package files
COPY frontend/package.json ./
COPY frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY frontend/ .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]

