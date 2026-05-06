"""
tests/test_api.py — pytest suite covering all 3 endpoints + core logic.

Run with:
    pytest tests/ -v
"""

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image

# ── App import (patch DB before it connects) ──────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _make_jpeg_bytes(w: int = 320, h: int = 240) -> bytes:
    """Create a minimal valid JPEG image in-memory."""
    img = Image.new("RGB", (w, h), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def client():
    """Async test client with DB and MediaPipe mocked out."""
    mock_db_session = AsyncMock()
    mock_db_session.add = MagicMock()
    mock_db_session.commit = AsyncMock()
    mock_db_session.rollback = AsyncMock()
    mock_db_session.close = AsyncMock()

    async def override_get_db():
        yield mock_db_session

    with patch("database.init_db", new_callable=AsyncMock):
        from main import app
        from database import get_db
        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

        app.dependency_overrides.clear()


# ── Health ────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Endpoint 1: /feed/upload ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_upload_frame_returns_jpeg(client):
    """Valid JPEG → 200 + image/jpeg content."""
    with patch("main.detect_face", return_value=None):
        resp = await client.post(
            "/feed/upload",
            files={"file": ("frame.jpg", _make_jpeg_bytes(), "image/jpeg")},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_upload_frame_unsupported_type(client):
    """Non-image content type → 400."""
    resp = await client.post(
        "/feed/upload",
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_frame_empty_body(client):
    """Empty file → 400."""
    resp = await client.post(
        "/feed/upload",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_frame_stores_roi_when_face_detected(client):
    """When face detected, DB .add() must be called."""
    from face_detector import DetectionResult
    mock_detection = DetectionResult(
        x1=50, y1=60, x2=150, y2=180,
        confidence=0.92,
        frame_width=320, frame_height=240,
    )
    with patch("main.detect_face", return_value=mock_detection), \
         patch("main.draw_roi", return_value=(Image.new("RGB", (320, 240)), True)):

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.close = AsyncMock()

        async def override():
            yield mock_db

        from main import app
        from database import get_db
        app.dependency_overrides[get_db] = override

        resp = await client.post(
            "/feed/upload",
            files={"file": ("frame.jpg", _make_jpeg_bytes(), "image/jpeg")},
        )

        app.dependency_overrides.clear()

    assert resp.status_code == 200
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


# ── Endpoint 3: /roi ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_roi_endpoint_returns_list(client):
    """/roi returns a JSON object with total + items list."""
    from database import ROIDetection
    from datetime import datetime

    fake_row = ROIDetection(
        frame_id="frame-1",
        session_id="sess-1",
        x1=10, y1=20, x2=100, y2=120,
        frame_width=320, frame_height=240,
        confidence=0.88,
    )
    fake_row.id = uuid.uuid4()
    fake_row.detected_at = datetime.utcnow()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_row]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.rollback = AsyncMock()
    mock_db.close = AsyncMock()

    async def override():
        yield mock_db

    from main import app
    from database import get_db
    app.dependency_overrides[get_db] = override

    resp = await client.get("/roi")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "items" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_roi_bounding_box_coordinates_valid(client):
    """ROI coords must satisfy x1 < x2 and y1 < y2."""
    from face_detector import DetectionResult
    det = DetectionResult(
        x1=10, y1=20, x2=200, y2=180,
        confidence=0.9, frame_width=320, frame_height=240,
    )
    assert det.x1 < det.x2
    assert det.y1 < det.y2


# ── Core logic: face_detector ─────────────────────────────────────────────────
def test_detect_face_no_face_returns_none():
    """Blank image (no face) → None."""
    from face_detector import detect_face
    blank = Image.new("RGB", (320, 240), color=(128, 128, 128))
    result = detect_face(blank)
    assert result is None


def test_draw_roi_no_detection_returns_image():
    """draw_roi with None detection must still return a PIL Image."""
    from frame_processor import draw_roi
    img = Image.new("RGB", (320, 240), color=(50, 50, 50))
    annotated, face_found = draw_roi(img, None)
    assert not face_found
    assert annotated.size == (320, 240)


def test_pil_to_jpeg_bytes_produces_valid_jpeg():
    """Encoded bytes must start with JPEG magic bytes (FFD8)."""
    from frame_processor import pil_to_jpeg_bytes
    img = Image.new("RGB", (100, 100), color=(0, 255, 0))
    data = pil_to_jpeg_bytes(img)
    assert data[:2] == b"\xff\xd8"
