from fastapi import APIRouter

from app.api.products import products_router as products_router

main_router = APIRouter()

main_router.include_router(products_router, prefix='/api')
