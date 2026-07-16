"""Tests for verification task-state cleanup."""

from __future__ import annotations

import asyncio

from custom_components.backup_checkup.task_control import (
    release_current_task_reference,
)


def test_current_task_reference_is_released_before_final_refresh() -> None:
    """A finishing verification must not keep the button unavailable."""

    async def _scenario() -> None:
        current = asyncio.current_task()
        assert current is not None
        assert release_current_task_reference(current) is None

    asyncio.run(_scenario())


def test_unrelated_task_reference_is_preserved() -> None:
    """Only the task performing cleanup may release its tracked reference."""

    async def _scenario() -> None:
        other = asyncio.create_task(asyncio.sleep(0))
        try:
            assert release_current_task_reference(other) is other
        finally:
            await other

    asyncio.run(_scenario())
