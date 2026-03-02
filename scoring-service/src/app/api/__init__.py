from fastapi import APIRouter

from app.api.scoring import scoring_router as scoring_router

main_router = APIRouter()

main_router.include_router(scoring_router, prefix='/api')
