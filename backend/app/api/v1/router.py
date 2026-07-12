from fastapi import APIRouter
from app.api.v1 import (
    auth, users, projects, tasks, checklist_items, comments, attachments, notifications,
)

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(projects.router)
router.include_router(tasks.router)
router.include_router(checklist_items.router)
router.include_router(comments.router)
router.include_router(attachments.router)
router.include_router(notifications.router)
