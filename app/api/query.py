from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


async def _pipeline_stub(_q: str):
    # stub — replace with actual pipeline calls later
    yield {"data": "ok"}


@router.get("/query")
async def query_doc(q: str = Query(..., description="Question to answer")):
    async def event_generator():
        async for chunk in _pipeline_stub(q):
            yield chunk

    return EventSourceResponse(event_generator())