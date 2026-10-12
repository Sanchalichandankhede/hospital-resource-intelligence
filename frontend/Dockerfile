# Stage 1: Build React Application
FROM node:20-slim AS build

WORKDIR /app

# Copy dependency mappings
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

# Inject build time Vite environment arguments
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build assets
RUN npm run build

# Stage 2: Serve React Application via Nginx
FROM nginx:alpine

# Copy built outputs to public folder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy routing rewrite configuration for SPA fallback
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
