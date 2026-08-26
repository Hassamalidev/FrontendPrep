"""Mounts every v1 router under the configured API prefix."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, agent, auth, catalog, content, issb, practice, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(catalog.router)
api_router.include_router(practice.router)
api_router.include_router(issb.router)
api_router.include_router(content.router)
api_router.include_router(admin.router)
api_router.include_router(agent.router)
