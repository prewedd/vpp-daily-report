"""Unit tests for report_builder. Run with: python -m pytest test_report_builder.py"""

from report_builder import TaskEvent, build_report, resolve_event


def test_empty_hides_all_sections():
    out = build_report([], "Thu, Apr 17")
    assert out.startswith("📹 VPP Daily Report — Thu, Apr 17")
    assert "— Couples —" not in out
    assert "— Reels —" not in out
    assert "— Other —" not in out
    assert "No activity." in out


def test_same_action_collapses_task_names():
    events = [
        TaskEvent("Couples", "Dima", "made revisions for", "Matt & Teresa"),
        TaskEvent("Couples", "Dima", "made revisions for", "Jess & Grayson"),
    ]
    out = build_report(events, "Thu, Apr 17")
    assert "Dima — made revisions for Matt & Teresa · Jess & Grayson" in out


def test_different_actions_concat_with_separator():
    events = [
        TaskEvent("Couples", "Yulia", "internal review for", "Carsyn & Tom"),
        TaskEvent("Couples", "Yulia", "uploaded", "Diana & Bo"),
    ]
    out = build_report(events, "Thu, Apr 17")
    assert "Yulia — internal review for Carsyn & Tom · uploaded Diana & Bo" in out


def test_inactive_section_hidden_active_section_shows_all_editors():
    events = [
        TaskEvent("Reels", "Yulia", "working on", "Brand X"),
    ]
    out = build_report(events, "Thu, Apr 17")
    assert "— Couples —" not in out
    assert "— Other —" not in out
    assert "— Reels —" in out
    # In the active Reels section, both editors show (Dima with dash).
    lines = out.splitlines()
    reels_i = lines.index("— Reels —")
    assert lines[reels_i + 1] == "Dima — -"
    assert lines[reels_i + 2] == "Yulia — working on Brand X"


def test_resolve_event_skips_unknown_list():
    task = {
        "name": "Foo",
        "list": {"name": "Some Other List"},
        "assignees": [{"username": "Dima from TLIC"}],
    }
    assert resolve_event(task, "editing") is None


def test_resolve_event_skips_unknown_editor():
    task = {
        "name": "Foo",
        "list": {"name": "Couples Projects"},
        "assignees": [{"username": "Stranger"}],
    }
    assert resolve_event(task, "editing") is None


def test_resolve_event_maps_known_trio():
    task = {
        "name": "Matt & Teresa",
        "list": {"name": "Couples Projects"},
        "assignees": [{"username": "Dima from TLIC"}],
    }
    ev = resolve_event(task, "EDITING")
    assert ev is not None
    assert ev.section == "Couples"
    assert ev.editor == "Dima"
    assert ev.action == "continuing work on"
    assert ev.task_name == "Matt & Teresa"
