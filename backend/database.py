"""
database.py — PostgreSQL connection + ROI table schema
Uses SQLAlchemy async engine with asyncpg driver.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# ── Engine ──────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


# ── Model ────────────────────────────────────────────────────────────────────
class ROIDetection(Base):
    """
    Stores one bounding-box detection per processed video frame.

    Columns
    -------
    id            : surrogate PK (UUID)
    frame_id      : client-supplied UUID that identifies the frame
    session_id    : groups all frames belonging to one streaming session
    x1, y1        : top-left corner of the axis-aligned bounding box (pixels)
    x2, y2        : bottom-right corner (pixels)
    frame_width   : original frame width  (needed to reproject relative coords)
    frame_height  : original frame height
    confidence    : detector confidence score [0, 1]
    detected_at   : server-side UTC timestamp
    """

    __tablename__ = "roi_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    frame_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    x1 = Column(Integer, nullable=False)
    y1 = Column(Integer, nullable=False)
    x2 = Column(Integer, nullable=False)
    y2 = Column(Integer, nullable=False)
    frame_width = Column(Integer, nullable=False)
    frame_height = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "frame_id": self.frame_id,
            "session_id": self.session_id,
            "roi": {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2},
            "frame_size": {"width": self.frame_width, "height": self.frame_height},
            "confidence": self.confidence,
            "detected_at": self.detected_at.isoformat(),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Create all tables on startup (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
