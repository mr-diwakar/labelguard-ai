"""Aggregates every versioned route behind a single prefix."""

from fastapi import APIRouter

from app.api import health
from app.core.config import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(health.router, tags=["health"])
