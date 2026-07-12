from fastapi import APIRouter
from app.api.v1 import (
    auth, users, projects, tasks, checklist_items, comments, attachments, notifications,
    sla, automations, ai, analytics, reports, labels, workspaces, predictive,
)

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(workspaces.router)
router.include_router(projects.router)
router.include_router(tasks.router)
router.include_router(checklist_items.router)
router.include_router(comments.router)
router.include_router(attachments.router)
router.include_router(notifications.router)
router.include_router(sla.router)
router.include_router(sla.sla_task_router)
router.include_router(automations.router)
router.include_router(ai.router)
router.include_router(analytics.router)
router.include_router(reports.router)
router.include_router(labels.router)
router.include_router(predictive.router)
