# Crypto API Server

Backend API server for Crypto Market Dashboard

## Installation

```bash
npm install
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
PORT=8080
NODE_ENV=development

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_db
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto_pass

REDIS_HOST=localhost
REDIS_PORT=6379
```

## Development

```bash
npm run dev
```

## Production

```bash
npm run build
npm start
```

## API Endpoints

See main project README for API documentation.
