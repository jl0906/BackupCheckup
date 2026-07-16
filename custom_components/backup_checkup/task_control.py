"""Helpers for tracking asynchronous BackupCheckup tasks."""

from __future__ import annotations

import asyncio


def release_current_task_reference[TaskResultT](
    tracked_task: asyncio.Task[TaskResultT] | None,
) -> asyncio.Task[TaskResultT] | None:
    """Release a tracked task when called from that task itself.

    A coordinator update may be dispatched from a task's ``finally`` block before
    asyncio marks the task as done. Clearing that self-reference first prevents
    entities from publishing a stale unavailable state after the work has finished.
    """
    if tracked_task is None:
        return None
    try:
        current_task = asyncio.current_task()
    except RuntimeError:
        return tracked_task
    return None if tracked_task is current_task else tracked_task
