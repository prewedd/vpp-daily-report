"""Pytest fixtures — seed required env vars so config.py can import."""

import json
import os

os.environ.setdefault("CLICKUP_TEAM_ID", "00000000")
os.environ.setdefault("CLICKUP_FOLDER_ID", "000000000000")
os.environ.setdefault(
    "EDITORS_JSON",
    json.dumps({"Dima from TLIC": "Dima", "Yuliia": "Yulia"}),
)
os.environ.setdefault(
    "LISTS_JSON",
    json.dumps({"Couples Projects": "Couples", "Reels": "Reels", "Other projects": "Other"}),
)
