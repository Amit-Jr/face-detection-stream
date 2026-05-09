# AI Collaboration Attestation

## Tools Used
- **Claude (Anthropic)** — primary AI assistant
- **My own judgment** — architecture decisions, debugging, review

---

## What AI Generated

| File | AI Contribution | My Contribution |
|------|----------------|-----------------|
| `backend/main.py` | FastAPI skeleton, endpoint structure | Reviewed all 3 endpoints, verified HTTP semantics, added session_id logic |
| `backend/face_detector.py` | MediaPipe integration pattern | Chose MediaPipe over dlib after evaluating no-OpenCV constraint |
| `backend/frame_processor.py` | Pillow draw.rectangle() approach | Verified axis-aligned bounding box spec met, tuned JPEG quality |
| `backend/database.py` | SQLAlchemy async boilerplate | Designed schema columns myself (frame_id, session_id, confidence) |
| `backend/schemas.py` | Pydantic model structure | Verified response contracts match frontend needs |
| `backend/tests/test_api.py` | Test stubs and mock patterns | Added edge cases: empty file, wrong content-type, no-face scenario |
| `frontend/VideoFeed.jsx` | WebSocket capture loop | Modified FPS throttle (15fps), binary ArrayBuffer transport |
| `frontend/ROITable.jsx` | Polling structure | Set 1.5s interval based on UX judgment |
| `docker-compose.yml` | Service definitions | Added healthcheck dependency, internal network isolation |

---

## What AI Did NOT Do

- Choose MediaPipe over OpenCV — that was a deliberate decision based on the constraint
- Design the PostgreSQL schema — I designed the columns and relationships
- Decide the WebSocket protocol (binary JPEG in, base64 JSON out) — my call
- Write the nginx reverse proxy config for WS upgrades — researched and wrote manually
- Debug any runtime errors — done by me

---

## My Review Process

Every AI-generated file was:
1. Read line by line before committing
2. Tested manually in the browser / via curl
3. Modified where needed (e.g. FPS cap, error handling paths)

---

## Honest Assessment

Using AI accelerated boilerplate generation (~3x faster). However, the core
architectural decisions — no OpenCV, MediaPipe model_selection=0 for short-range
webcam, async SQLAlchemy for per-frame DB writes, binary WebSocket transport —
were made by me based on the problem constraints.

I can explain and defend every line of this codebase.
