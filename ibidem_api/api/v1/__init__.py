from fastapi import APIRouter

from . import suc
from . import token

tags_metadata = []
tags_metadata.extend(suc.tags_metadata)

router = APIRouter()
router.include_router(suc.router, prefix="/suc")
router.include_router(token.router, prefix="/token")
