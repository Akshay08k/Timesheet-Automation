"""Tests for Google Gemini summary service and rule-based fallback."""

from backend.app.services.ai.gemini_service import GeminiSummaryService


def test_rule_based_summary_fallback_with_commits():
    service = GeminiSummaryService(api_key=None)

    sample_commits = [
        {
            "external_id": "a1b2c3d4e5f6",
            "repository": "vcc-vcqms-api",
            "title": "feat: implement daily inspection approval workflow",
        },
        {
            "external_id": "f6e5d4c3b2a1",
            "repository": "vcc-vcqms-api",
            "title": "fix: correct inspection status filter on dashboard",
        },
    ]
    sample_prs = [
        {
            "external_id": "142",
            "repository": "vcc-vcqms-api",
            "title": "Inspection workflow improvements",
            "status": "active",
        }
    ]
    sample_manual = [
        {
            "category": "Meeting",
            "description": "Sprint planning and requirement review with client",
            "duration_hours": 1.0,
        }
    ]

    output = service.generate_daily_summary(
        date_str="2026-10-30",
        commits=sample_commits,
        pull_requests=sample_prs,
        work_items=[],
        manual_activities=sample_manual,
    )

    assert output.task_summary is not None
    assert len(output.detailed_bullets) >= 3
    assert "a1b2c3d4" in output.referenced_commit_shas
    assert "142" in output.referenced_pr_ids
    assert "VCQMS" in output.suggested_project


def test_prompt_payload_builder_does_not_contain_secrets():
    service = GeminiSummaryService(api_key=None)
    prompt = service._build_prompt_payload(
        date_str="2026-10-30",
        commits=[{"external_id": "c12345678", "repository": "repo-a", "title": "fix database connection"}],
        pull_requests=[],
        work_items=[],
        manual_activities=[],
        custom_instructions="Focus on API fixes",
    )

    assert "2026-10-30" in prompt
    assert "fix database connection" in prompt
    assert "Focus on API fixes" in prompt
    assert "PAT" not in prompt
