# Real-Time Face Detection — Video Streaming System

> **Stack:** FastAPI · MediaPipe · Pillow · PostgreSQL · React · Docker  
> **No OpenCV used anywhere.**

---

## Quick Start (5 minutes)

```bash
git clone <repo-url> face-detection-app
cd face-detection-app
docker-compose up --build
```

| Service    | URL                          |
|------------|------------------------------|
| Frontend   | http://localhost:3000        |
| Backend    | http://localhost:8000        |
| API Docs   | http://localhost:8000/docs   |

---

## Architecture

See [`architecture.png`](./architecture.png) for the full system diagram.

```
Browser → WebSocket → FastAPI → MediaPipe → Pillow → PostgreSQL
                              ↓
                     Annotated JPEG → WebSocket → Browser
```

---

## API Endpoints

### 1. Receive video feed (REST fallback)
```
POST /feed/upload
Content-Type: multipart/form-data
Query: ?session_id=<string>

Response: image/jpeg (annotated frame)
```

### 2. Bidirectional WebSocket stream
```
WS /ws/feed?session_id=<string>

Client sends:  raw JPEG bytes
Server sends:  { "frame": "<base64-jpeg>", "face_found": bool, "frame_id": "<uuid>" }
```

### 3. ROI data
```
GET /roi?session_id=<string>&limit=50&offset=0

Response:
{
  "total": 42,
  "items": [
    {
      "id": "uuid",
      "frame_id": "uuid",
      "session_id": "string",
      "roi": { "x1": 50, "y1": 60, "x2": 200, "y2": 220 },
      "frame_size": { "width": 640, "height": 480 },
      "confidence": 0.97,
      "detected_at": "2024-01-01T12:00:00"
    }
  ]
}
```

---

## Database Schema

```sql
CREATE TABLE roi_detections (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    frame_id     VARCHAR(64) NOT NULL,
    session_id   VARCHAR(64) NOT NULL,
    x1           INTEGER NOT NULL,
    y1           INTEGER NOT NULL,
    x2           INTEGER NOT NULL,
    y2           INTEGER NOT NULL,
    frame_width  INTEGER NOT NULL,
    frame_height INTEGER NOT NULL,
    confidence   FLOAT,
    detected_at  TIMESTAMP DEFAULT NOW()
);
```

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **MediaPipe** for face detection | No OpenCV dependency; runs CPU-only; single-model short-range mode suits webcam |
| **Pillow** for bounding box | Pure Python; handles JPEG encode/decode; `draw.rectangle()` = axis-aligned box |
| **WebSocket** primary transport | Low-latency bidirectional; client sends raw bytes, server streams annotated frames |
| **PostgreSQL** for ROI storage | Relational model fits structured detection data; good for time-series queries |
| **asyncpg** driver | Native async; no thread-pool overhead for DB writes per frame |
| **Docker Compose** | One-command reproducible environment; services isolated on internal network |

---

## AI Collaboration Log

> As required by the assessment: documenting where AI assistance was used.

| Area | AI Used | How |
|------|---------|-----|
| Boilerplate structure | Claude (Anthropic) | Generated FastAPI skeleton, Pydantic schemas |
| MediaPipe integration | Claude | Suggested model_selection=0 for short-range |
| Pillow bounding box | Self | Verified `draw.rectangle()` spec matches axis-aligned box requirement |
| React WebSocket logic | Claude | Generated initial capture loop; modified FPS throttle manually |
| SQL schema | Self | Designed independently, reviewed with Claude |
| Tests | Claude + Self | Generated test stubs; added edge cases manually |

---

## Project Structure

```
face-detection-app/
├── backend/
│   ├── main.py              # FastAPI app + 3 endpoints
│   ├── face_detector.py     # MediaPipe detection
│   ├── frame_processor.py   # Pillow drawing + encoding
│   ├── database.py          # SQLAlchemy async + ROI model
│   ├── schemas.py           # Pydantic API contracts
│   ├── config.py            # Settings from env vars
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       └── test_api.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── VideoFeed.jsx    # WebSocket capture + display
│   │   ├── ROITable.jsx     # Polls /roi every 1.5s
│   │   ├── App.css
│   │   └── main.jsx
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── architecture.png
└── README.md
```
