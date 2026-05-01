"""Query router: accepts founder questions and streams agent responses via SSE."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents.orchestrator import run_pipeline
from backend.auth.middleware import verify_jwt
from backend.rag.pipeline import RAGPipeline
from backend.storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    upload_id: Optional[str] = None


@router.post("")
async def query(
    body: QueryRequest,
    request: Request,
    founder: dict = Depends(verify_jwt),
) -> StreamingResponse:
    """Stream a multi-agent analysis for the founder's question via SSE.

    Args:
        body: Question and optional upload_id.
        request: FastAPI request (used to detect client disconnect).
        founder: Verified JWT claims.

    Returns:
        StreamingResponse of SSE events from each agent in sequence.
    """
    founder_id: str = founder["sub"]
    logger.info("Query from founder=%s question=%r", founder_id, body.question[:80])

    sb = get_supabase_client()
    rag = RAGPipeline(supabase_client=sb)

    async def event_stream():
        try:
            async for chunk in run_pipeline(
                question=body.question,
                founder_id=founder_id,
                rag_pipeline=rag,
            ):
                if await request.is_disconnected():
                    logger.info("Client disconnected — stopping stream")
                    break
                yield chunk
        except Exception as exc:
            logger.error("Stream error for founder=%s: %s", founder_id, str(exc))
            yield f"event: error\ndata: {json.dumps({'code': 'INTERNAL_ERROR', 'message': 'Stream failed'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
