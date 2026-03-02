from fastapi import APIRouter

from app.api.antifraud import antifraud_router

main_router = APIRouter()

main_router.include_router(antifraud_router, prefix='/api')
