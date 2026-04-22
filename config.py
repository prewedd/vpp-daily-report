"""Configuration for VPP daily report."""

TEAM_ID = "90152264233"
FOLDER_ID = "901513870625"
TIMEZONE = "Europe/Kyiv"

# Report window is [target_day 08:00 Kyiv, target_day+1 08:00 Kyiv), so late-
# night work (e.g. 02:00 AM) counts toward the previous workday.
WORKDAY_START_HOUR = 8

EDITORS = {
    "Dima from TLIC": "Dima",
    "Yuliia": "Yulia",
}

LISTS = {
    "Couples Projects": "Couples",
    "Reels": "Reels",
    "Other projects": "Other",
}

SECTION_ORDER = ["Couples", "Reels", "Other"]

STATUS_ACTIONS = {
    "edit que": "picked up",
    "editing": "continuing work on",
    "internal review": "sent for internal review",
    "sent to client": "sent to client",
    "editing corrections": "making corrections for",
    "review corrections": "reviewing corrections for",
    "corrections sent to client": "sent corrections to client",
    "uploaded on youtube": "uploaded",
    "in progress": "working on",
    "on review": "sent for review",
    "complete": "completed",
}

SKIP_STATUSES = {
    "waiting corrections",
    "review expired",
    "final draft approved",
    "finished",
    "to do",
}

# Ongoing work: task appears in the report every day while in this status, even
# if nothing changed today. Everything else in STATUS_ACTIONS is a transition
# event — shown only on the day date_updated falls in the window.
ONGOING_STATUSES = {
    "editing",
    "editing corrections",
    "in progress",
}
