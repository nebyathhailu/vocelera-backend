# Vocelera Backend

An AI-powered citizen feedback analysis platform that ingests WhatsApp messages via Twilio, processes them with Google Gemini, and delivers real-time insights to a dashboard over WebSockets.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the Server](#running-the-server)
- [Apps](#apps)
- [API Reference](#api-reference)
- [WhatsApp Webhook](#whatsapp-webhook)
- [AI Insights](#ai-insights)
- [WebSockets](#websockets)
- [Celery Tasks](#celery-tasks)
- [Development Notes](#development-notes)

---

## Overview

Vocelera allows government agencies and organizations to collect citizen feedback via WhatsApp, analyse it using AI, and visualize trends and insights in a real-time dashboard. Documents (CSV, PDF, Excel) can also be uploaded for AI-powered analysis.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.0 + Django REST Framework |
| AI | Google Gemini 2.5 Flash |
| Messaging | Twilio WhatsApp API |
| Async Tasks | Celery + Redis |
| Real-time | Django Channels + Redis |
| Auth | JWT via `djangorestframework-simplejwt` |
| API Docs | drf-spectacular (Swagger UI) |
| Database | PostgreSQL (production) / SQLite (development) |
| Tunneling | ngrok (development) |

---

## Project Structure

```
vocelera-backend/
├── manage.py
├── .env                        # Environment variables (not committed)
├── db.sqlite3                  # SQLite DB (development only)
│
├── vocelera/                   # Project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── ai_services/                # Shared Gemini client
│   ├── gemini_client.py
│   ├── prompt_builder.py
│   └── response_parser.py
│
├── users/                      # Custom auth & user management
├── projects/                   # Analysis projects
├── messages_app/               # Citizen messages
├── insights/                   # AI-generated insights
├── reports/                    # Reporting
├── collaboration/              # Project participants
├── ai_app/                     # AI utilities
├── twilio_app/                 # WhatsApp webhook & ingestion
├── document_analysis/          # File upload & AI analysis
└── utils/                      # Shared utilities (pagination, permissions)
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL (for production) or SQLite (for development)
- Redis
- ngrok (for local WhatsApp webhook testing)
- A Twilio account with WhatsApp Sandbox enabled
- A Google AI Studio API key

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd vocelera-backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy the example env file and fill in your values
cp .env.example .env
```

### Environment Variables

Create a `.env` file in the project root with the following:

```bash
# Core
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,your-ngrok-domain.ngrok-free.dev

# Database (leave empty to use SQLite in development)
DATABASE_URL=postgres://user:password@localhost:5432/vocelera

# CORS (add your frontend URL)
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Google Gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Redis
REDIS_URL=redis://localhost:6379/0

# Insight generation threshold (every N messages)
INSIGHT_TRIGGER_EVERY_N_MESSAGES=10
```

> **Note:** If `DATABASE_URL` is left empty, Django will automatically fall back to a local SQLite database.

### Running the Server

```bash
# Apply migrations
python3 manage.py migrate

# Create a superuser
python3 manage.py createsuperuser

# Start the development server
python3 manage.py runserver
```

Start Redis and Celery in separate terminals:

```bash
# Terminal 2 — Redis
sudo systemctl start redis

# Terminal 3 — Celery worker
celery -A vocelera worker --loglevel=info

# Terminal 4 — ngrok tunnel (for WhatsApp webhook)
ngrok http 8000
```

---

## Apps

### `users`
Custom user model and JWT authentication. Handles registration, login, and token refresh.

### `projects`
Analysis projects that group messages and insights together. Users can create projects and invite participants with role-based access.

### `messages_app`
Stores citizen messages ingested from WhatsApp or bulk-imported via CSV. Supports filtering by project.

### `insights`
AI-generated insights for a project based on its messages. Insights can be triggered manually or automatically every N messages.

### `twilio_app`
Handles the Twilio WhatsApp webhook. Validates incoming requests, creates citizen profiles, ingests messages, and fires async Celery tasks.

### `document_analysis`
Accepts CSV, PDF, and Excel uploads. Parses the document, builds a Gemini prompt, and returns structured AI analysis including summary, themes, statistics, insights, and recommendations.

### `ai_services`
Shared `GeminiClient` used across the platform. Handles prompt construction, retries (excluding quota errors), and structured JSON response parsing.

---

## API Reference

Interactive API docs are available at:

```
http://127.0.0.1:8000/api/docs/
```

Raw OpenAPI schema:

```
http://127.0.0.1:8000/api/schema/
```

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register/` | Register a new user |
| `POST` | `/api/v1/auth/login/` | Obtain JWT tokens |
| `POST` | `/api/v1/auth/token/refresh/` | Refresh access token |
| `GET` | `/api/v1/projects/` | List user's projects |
| `POST` | `/api/v1/projects/` | Create a project |
| `GET` | `/api/v1/messages/?project_id=1` | List messages for a project |
| `POST` | `/api/v1/messages/bulk-import/` | Bulk import messages |
| `GET` | `/api/v1/insights/?project_id=1` | Get insights for a project |
| `POST` | `/api/v1/insights/projects/<id>/generate/` | Manually trigger AI insights |
| `POST` | `/api/v1/documents/analyze/` | Upload and analyse a document |
| `GET` | `/api/v1/documents/?project_id=1` | List document analyses |

---

## WhatsApp Webhook

Twilio sends incoming WhatsApp messages to:

```
POST /webhook/<project_id>/whatsapp/
```

### Setup

1. Start ngrok: `ngrok http 8000`
2. Copy your ngrok URL, e.g. `https://xxxx.ngrok-free.dev`
3. Go to [Twilio Console](https://console.twilio.com) → **Messaging → Sandbox for WhatsApp**
4. Set **"When a message comes in"** to:
   ```
   https://xxxx.ngrok-free.dev/webhook/1/whatsapp/
   ```
   Replace `1` with your actual project ID.
5. Send a WhatsApp message to the Twilio sandbox number

> **Note:** Twilio signature validation is skipped when `DEBUG=True`. Always validate signatures in production.

---

## AI Insights

Insights are generated by Google Gemini based on the messages in a project.

### Automatic Trigger
Insights are regenerated every `INSIGHT_TRIGGER_EVERY_N_MESSAGES` messages (default: 10). A cache lock prevents duplicate runs within 5 minutes.

### Manual Trigger
```
POST /api/v1/insights/projects/<project_id>/generate/
```

### Document Analysis
Upload a file to receive AI-generated structured analysis:

```
POST /api/v1/documents/analyze/
Content-Type: multipart/form-data

file: <your file>
project_id: 1  (optional)
```

Supported formats: `.csv`, `.pdf`, `.xlsx`, `.xls`

---

## WebSockets

Real-time updates are delivered via Django Channels over WebSocket connections.

| Channel Group | Event | Description |
|---|---|---|
| `project_<id>_messages` | `new_message` | New WhatsApp message ingested |
| `project_<id>_insights` | `new_insights` | AI insights regenerated |

Connect to WebSocket at:
```
ws://localhost:8000/ws/projects/<project_id>/
```

---

## Celery Tasks

| Task | Trigger | Description |
|---|---|---|
| `broadcast_new_message` | After WhatsApp message ingested | Pushes message to WebSocket group |
| `trigger_insight_generation` | Every N messages or manually | Runs AI insight generation and broadcasts result |

---

## Development Notes

- **SQLite vs PostgreSQL:** Leave `DATABASE_URL` empty in `.env` to use SQLite locally. Set it to a PostgreSQL URL for production.
- **Gemini quota:** The free tier allows 20 requests/day for `gemini-2.5-flash`. Use the manual insight trigger during development to conserve quota.
- **ngrok URL changes:** Every time you restart ngrok, update `ALLOWED_HOSTS` in `.env` and the webhook URL in Twilio Console.
- **JWT key length:** Use a `SECRET_KEY` of at least 32 characters to avoid `InsecureKeyLengthWarning`.
- **Redis required:** Both Celery and Django Channels depend on Redis. Make sure it is running before starting the server.
