from fastapi import APIRouter
from app.api.v1 import users, auth

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(auth.router)
