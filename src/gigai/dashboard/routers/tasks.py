from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from gigai.dashboard.mock_data import build_task_detail, build_tasks
from gigai.dashboard.models import TaskList, TaskStatusUpdateRequest
from gigai.storage import append_audit_log

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])
_ALLOWED_STATUSES = {"pending", "in_progress", "completed", "on_hold"}


@router.get("/api/tasks", response_model=TaskList)
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    architect_email: Optional[str] = None,
):
    try:
        tasks = build_tasks()
        if status:
            tasks = [task for task in tasks if task.status == status]
        if priority:
            tasks = [task for task in tasks if task.priority == priority]
        if architect_email:
            tasks = [task for task in tasks if task.assigned_to == architect_email]
        logger.info("Retrieved %s tasks", len(tasks))
        return tasks
    except Exception as ex:
        logger.error("Error listing tasks: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    try:
        return build_task_detail(task_id)
    except Exception as ex:
        logger.error("Error getting task %s: %s", task_id, ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.post("/api/tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    payload: TaskStatusUpdateRequest | None = None,
    new_status: Optional[str] = Query(default=None),
):
    try:
        resolved_status = (payload.new_status if payload else None) or new_status
        if resolved_status not in _ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")

        logger.info("Task %s status updated to %s", task_id, resolved_status)
        append_audit_log(
            "task",
            task_id,
            "task_status_updated",
            "dashboard_api",
            {"new_status": resolved_status},
        )
        return {
            "status": "success",
            "task_id": task_id,
            "new_status": resolved_status,
            "updated_at": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as ex:
        logger.error("Error updating task %s: %s", task_id, ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/tasks/by-architect/{email}")
async def get_architect_tasks(email: str):
    try:
        tasks = [task.model_dump() for task in build_tasks() if task.assigned_to == email]
        return tasks
    except Exception as ex:
        logger.error("Error getting architect tasks for %s: %s", email, ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex
