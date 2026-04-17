"""Thin ClickUp API client for the VPP daily report."""

from __future__ import annotations

import requests

BASE_URL = "https://api.clickup.com/api/v2"


class ClickUpClient:
    def __init__(self, api_token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": api_token})

    def search_tasks_in_folder(
        self,
        team_id: str,
        folder_id: str,
        date_updated_gt_ms: int,
        date_updated_lt_ms: int,
    ) -> list[dict]:
        """Return all tasks in a folder updated within the given ms window.

        Paginates until an empty page comes back.
        """
        tasks: list[dict] = []
        page = 0
        while True:
            resp = self.session.get(
                f"{BASE_URL}/team/{team_id}/task",
                params={
                    "page": page,
                    "project_ids[]": folder_id,
                    "date_updated_gt": date_updated_gt_ms,
                    "date_updated_lt": date_updated_lt_ms,
                    "include_closed": "true",
                    "subtasks": "false",
                },
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json().get("tasks", [])
            if not batch:
                break
            tasks.extend(batch)
            page += 1
        return tasks

    def get_time_in_status(self, task_id: str) -> dict | None:
        """Return time_in_status payload, or None if ClickUp has no TIS data.

        The endpoint returns HTTP 401 with body {"err":"No data for TIS"} for
        tasks whose status history hasn't been recorded — we treat this as "no
        data, skip this task" rather than an auth failure.
        """
        resp = self.session.get(
            f"{BASE_URL}/task/{task_id}/time_in_status",
            timeout=30,
        )
        if resp.status_code in (401, 404):
            try:
                body = resp.json()
            except ValueError:
                body = {}
            if "No data for TIS" in body.get("err", ""):
                return None
        resp.raise_for_status()
        return resp.json()
