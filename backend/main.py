"""
main.py — FastAPI application entry point.

Endpoints
---------
POST /feed/upload      — receive a single JPEG/PNG frame (REST fallback)
WS   /ws/feed          — bidirectional WebSocket: receive frames, stream back annotated
GET  /roi              — query stored ROI detections from PostgreSQL
GET  /health           — liveness probe
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import ROIDetection, get_db, init_db
from face_detector import detect_face
from frame_processor import bytes_to_pil, draw_roi, pil_to_base64_jpeg, pil_to_jpeg_bytes
from schemas import HealthResponse, ROIListResponse, ROIResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Real-Time Face Detection API",
    description="WebSocket-based face detection pipeline using MediaPipe + Pillow.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Initialising database tables…")
    await init_db()
    logger.info("Database ready.")


# ── Helper ────────────────────────────────────────────────────────────────────
async def _process_and_store(
    raw_bytes: bytes,
    session_id: str,
    frame_id: str,
    db: AsyncSession,
) -> tuple[bytes, bool]:
    """
    Core pipeline:
      1. Decode bytes → PIL Image
      2. Detect face (MediaPipe)
      3. Draw ROI box (Pillow)
      4. Persist detection to DB
      5. Return annotated JPEG bytes + face_found flag
    """
    pil_img = bytes_to_pil(raw_bytes)
    detection = detect_face(pil_img)
    annotated, face_found = draw_roi(pil_img, detection)

    if face_found and detection:
        roi = ROIDetection(
            frame_id=frame_id,
            session_id=session_id,
            x1=detection.x1,
            y1=detection.y1,
            x2=detection.x2,
            y2=detection.y2,
            frame_width=detection.frame_width,
            frame_height=detection.frame_height,
            confidence=detection.confidence,
        )
        db.add(roi)
        await db.commit()

    return pil_to_jpeg_bytes(annotated), face_found


# ── Endpoint 1: Receive video feed frame (REST) ───────────────────────────────
@app.post(
    "/feed/upload",
    summary="Upload a single video frame",
    response_class=Response,
    responses={
        200: {"content": {"image/jpeg": {}}, "description": "Annotated JPEG frame"},
        400: {"description": "Invalid image data"},
    },
)
async def upload_frame(
    file: UploadFile = File(..., description="JPEG or PNG frame"),
    session_id: str = Query(default="default", description="Streaming session identifier"),
    db: AsyncSession = Depends(get_db),
):
    """
    **Endpoint 1** — Accept a single frame, run face detection, return annotated image.
    The ROI is stored in PostgreSQL if a face is detected.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {file.content_type}")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file received.")

    try:
        frame_id = str(uuid.uuid4())
        annotated_bytes, _ = await _process_and_store(raw, session_id, frame_id, db)
    except Exception as exc:
        logger.exception("Frame processing error: %s", exc)
        raise HTTPException(status_code=500, detail="Frame processing failed.")

    return Response(content=annotated_bytes, media_type="image/jpeg")


# ── Endpoint 2: WebSocket — bidirectional streaming ──────────────────────────
@app.websocket("/ws/feed")
async def websocket_feed(
    websocket: WebSocket,
    session_id: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    **Endpoint 2** — WebSocket feed endpoint.

    Protocol
    --------
    Client sends raw JPEG bytes for each frame.
    Server responds with a JSON message:
        {
          "frame": "<base64-jpeg>",
          "face_found": true,
          "frame_id": "<uuid>"
        }
    """
    await websocket.accept()
    sid = session_id or str(uuid.uuid4())
    logger.info("WebSocket session started: %s", sid)

    try:
        while True:
            raw = await websocket.receive_bytes()
            frame_id = str(uuid.uuid4())

            try:
                annotated_bytes, face_found = await _process_and_store(raw, sid, frame_id, db)
                b64 = pil_to_base64_jpeg(
                    __import__("frame_processor").bytes_to_pil(annotated_bytes)
                )
                await websocket.send_json(
                    {"frame": b64, "face_found": face_found, "frame_id": frame_id}
                )
            except Exception as exc:
                logger.error("Frame error in session %s: %s", sid, exc)
                await websocket.send_json({"error": "Frame processing failed", "frame_id": frame_id})

    except WebSocketDisconnect:
        logger.info("WebSocket session ended: %s", sid)


# ── Endpoint 3: Serve ROI data ────────────────────────────────────────────────
@app.get(
    "/roi",
    response_model=ROIListResponse,
    summary="Query stored ROI detections",
)
async def get_roi(
    session_id: Optional[str] = Query(None, description="Filter by session"),
    limit: int = Query(50, ge=1, le=500, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """
    **Endpoint 3** — Return stored bounding-box detections from PostgreSQL.
    Optionally filter by `session_id`. Results are newest-first.
    """
    stmt = select(ROIDetection).order_by(desc(ROIDetection.detected_at))
    if session_id:
        stmt = stmt.where(ROIDetection.session_id == session_id)

    count_result = await db.execute(stmt)
    total = len(count_result.scalars().all())

    paged = stmt.limit(limit).offset(offset)
    result = await db.execute(paged)
    rows = result.scalars().all()

    return ROIListResponse(
        total=total,
        items=[ROIResponse(**r.to_dict()) for r in rows],
    )


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")
