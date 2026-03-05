# Use Node.js as the base image for building the app
FROM node:20-alpine AS builder

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application code
COPY . .

# Build the Vite React application
RUN npm run build

# Use a lightweight NGINX server to host the static files
FROM nginx:alpine

# Copy the built files from the previous stage to Nginx's HTML folder
COPY --from=builder /app/dist /usr/share/nginx/html

# Add custom Nginx configuration to handle React Router (Single Page Application routing)
# This prevents 404 errors when refreshing on a route like /celulas
RUN echo "server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html index.htm; \
    location / { \
        try_files \$uri \$uri/ /index.html; \
    } \
}" > /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
