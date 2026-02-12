from fastapi import APIRouter

from . import v1

tags_metadata = []
tags_metadata.extend(v1.tags_metadata)

router = APIRouter()
router.include_router(v1.router, prefix="/v1")
