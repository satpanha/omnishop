# OmniShop TMA

> A high-performance single-seller e-commerce **Telegram Mini App** with automated messaging across Telegram & Instagram.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────┐
│  Telegram Mini   │────▶│   FastAPI Backend │────▶│ PostgreSQL │
│  App (Next.js)   │◀────│   (Python 3.11+) │◀────│  (Neon DB) │
└─────────────────┘     └──────────────────┘     └────────────┘
                              │       │
                    ┌─────────┘       └──────────┐
                    ▼                            ▼
            ┌──────────────┐          ┌───────────────┐
            │ Telegram Bot │          │ Instagram     │
            │ API Webhooks │          │ Graph API     │
            └──────────────┘          └───────────────┘
```

**Pattern:** Layered Webhook-Driven Monolith (Asynchronous)

## Tech Stack

| Layer     | Technology                  | Why                                    |
|-----------|-----------------------------|----------------------------------------|
| Frontend  | Next.js 14 + TypeScript     | SSG, fast navigation in Telegram WebView |
| Backend   | FastAPI + Python 3.11       | Native async, auto OpenAPI docs        |
| Database  | PostgreSQL (Neon DB)        | Serverless, scales-to-zero, free tier  |
| Auth      | Telegram initData + JWT     | Cryptographic verification, no passwords |
| Hosting   | Vercel (FE) + Render (BE)   | Free tier compatible                   |

## Prerequisites

- **Python 3.11+** with `pip`
- **Node.js 18+** with `npm`
- **PostgreSQL** (local or [Neon DB](https://neon.tech) free tier)
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))

## Quick Start

### 1. Clone & Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual values
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The Mini App will be available at `http://localhost:3000`.

### 4. Webhook Testing (Optional)

For testing Telegram/Instagram webhooks locally:

```bash
# Install ngrok
ngrok http 8000

# Set the webhook URL via Telegram Bot API
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://<NGROK_URL>/api/v1/webhooks/telegram"}'
```

## Environment Variables

| Variable                 | Required | Description                                |
|--------------------------|----------|--------------------------------------------|
| `DATABASE_URL`           | ✅       | PostgreSQL connection string               |
| `TELEGRAM_BOT_TOKEN`     | ✅       | Bot token from @BotFather                  |
| `TELEGRAM_WEBHOOK_SECRET`| ✅       | Secret token for webhook verification      |
| `JWT_SECRET_KEY`         | ✅       | Random 256-bit key for JWT signing         |
| `ADMIN_TELEGRAM_ID`      | ✅       | Your personal Telegram user ID             |
| `INSTAGRAM_VERIFY_TOKEN` | ❌       | Token for Instagram webhook verification   |
| `INSTAGRAM_APP_SECRET`   | ❌       | Meta app secret for signature validation   |
| `INSTAGRAM_ACCESS_TOKEN` | ❌       | Page access token for Instagram Graph API  |
| `FRONTEND_URL`           | ❌       | Frontend URL for CORS (default: localhost) |

## Project Structure

```
omnishop/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/v1/          # Route handlers
│   │   ├── auth/            # Telegram + JWT auth
│   │   ├── middleware/      # Rate limiting
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # Database migrations
│   └── tests/               # Pytest suite
│
└── frontend/                # Next.js Telegram Mini App
    └── src/
        ├── app/             # App Router pages
        ├── components/      # Reusable UI components
        ├── hooks/           # React hooks
        ├── lib/             # API client, utilities
        └── styles/          # CSS design system
```

## API Endpoints

| Method | Path                           | Auth    | Description              |
|--------|--------------------------------|---------|--------------------------|
| POST   | `/api/v1/auth/telegram`        | None    | Validate initData, get JWT |
| GET    | `/api/v1/products`             | None    | List active products     |
| POST   | `/api/v1/products`             | Admin   | Create product           |
| PUT    | `/api/v1/products/{id}`        | Admin   | Update product           |
| DELETE | `/api/v1/products/{id}`        | Admin   | Soft-delete product      |
| POST   | `/api/v1/transactions`         | Buyer   | Place an order           |
| GET    | `/api/v1/transactions`         | Admin   | List all transactions    |
| PATCH  | `/api/v1/transactions/{id}/status` | Admin | Update order status   |
| POST   | `/api/v1/webhooks/telegram`    | Webhook | Telegram bot webhook     |
| POST   | `/api/v1/webhooks/instagram`   | Webhook | Instagram DM webhook     |
| GET    | `/api/v1/webhooks/instagram`   | None    | Meta hub challenge       |

## License

Private — All rights reserved.
# omnishop
