FROM node:20-alpine AS builder

WORKDIR /app

# Copy package.json and lockfile from api-server directory
COPY api-server/package*.json ./
# Install dependencies strictly from lockfile
RUN npm ci

# Copy source code
COPY api-server/src ./src
COPY api-server/tsconfig.json ./

# Copy shared module to src/shared
COPY shared ./src/shared

# Build
RUN npm run build

FROM node:20-alpine

WORKDIR /app

# Copy package.json and lockfile
COPY api-server/package*.json ./

# Install only production dependencies
RUN npm ci --omit=dev

# Copy artifacts
COPY --from=builder /app/dist ./dist

EXPOSE 8080

CMD ["node", "dist/index.js"]