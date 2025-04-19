from fastapi import APIRouter
from fastcache.decorator import cache
import asyncio

router = APIRouter(
    prefix="/demo",
    tags=["demo"],
)


@router.get("/")
@cache(expire=60)
async def get_demo():
    await asyncio.sleep(7)
    return {"message": "demo data"}
