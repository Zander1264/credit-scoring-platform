from fastapi import APIRouter

from app.api.data_interaction import data_router as data_router

main_router = APIRouter()

main_router.include_router(data_router, tags=['Data interaction'])
