from fastapi import APIRouter

from . import suc

tags_metadata = []
tags_metadata.extend(suc.tags_metadata)

router = APIRouter()
router.include_router(suc.router, prefix="/suc")
