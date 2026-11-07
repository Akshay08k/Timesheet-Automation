"""Unit tests for TimesheetService helper functions including README formatting."""

from backend.app.services.timesheet.timesheet_service import format_readme_summary


def test_format_readme_summary_combines_overview_and_bullets():
    overview = "Resolved multiple issues across the VCQMS repository."
    bullets = [
        "Updated inbound AQL filtering to strictly match exact SKU.",
        "Resolved NCP listing query timeouts by correcting ProductMaster joins.",
        "- Already has dash bullet",
    ]

    result = format_readme_summary(overview, bullets)

    assert result.startswith("Resolved multiple issues across the VCQMS repository.\n\n")
    assert "- Updated inbound AQL filtering to strictly match exact SKU." in result
    assert "- Resolved NCP listing query timeouts by correcting ProductMaster joins." in result
    assert "- Already has dash bullet" in result
    # Check there is no double dash
    assert "--" not in result


def test_format_readme_summary_does_not_duplicate_existing_bullets():
    already_formatted = (
        "High level summary.\n\n"
        "- Task A completed\n"
        "- Task B completed"
    )
    bullets = ["Task A completed", "Task B completed"]

    result = format_readme_summary(already_formatted, bullets)
    assert result == already_formatted


def test_format_readme_summary_empty_bullets():
    overview = "On Leave"
    assert format_readme_summary(overview, []) == "On Leave"
    assert format_readme_summary(overview, None) == "On Leave"


def test_format_readme_summary_only_bullets():
    bullets = ["Fixed bug in inventory", "Merged PR #1234"]
    result = format_readme_summary("", bullets)
    assert result == "- Fixed bug in inventory\n- Merged PR #1234"

