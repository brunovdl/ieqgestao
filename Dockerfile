# Stage 1: Build the React app
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci

# Copy application source code
COPY . .

# Receive build arguments from EasyPanel
ARG SUPABASE_URL
ARG SUPABASE_KEY
ARG GROQ_API_KEY

# Write a .env.production file so Vite can find the variables at build time
RUN echo "VITE_SUPABASE_URL=${SUPABASE_URL}" > .env.production && \
    echo "VITE_SUPABASE_ANON_KEY=${SUPABASE_KEY}" >> .env.production && \
    echo "VITE_GROQ_API_KEY=${GROQ_API_KEY}" >> .env.production

# Build the Vite React application
RUN npm run build

# Stage 2: Serve with NGINX
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Configure NGINX for React Router (SPA)
RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / {\n\
    try_files $uri $uri/ /index.html;\n\
    }\n\
    }\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
