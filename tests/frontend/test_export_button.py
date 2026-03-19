import pytest
from playwright.sync_api import Page, expect


@pytest.mark.django_db(transaction=True)
def test_export_button_visible(logged_in_page, live_server, meal_plan_with_day):
    """Export button renders on the meal plan preview page."""
    plan, _ = meal_plan_with_day
    page = logged_in_page
    page.goto(f"{live_server.url}/meal-plan/{plan.pk}/preview/")
    # The export overlay is rendered server-side — no Vue mount needed
    export_btn = page.locator("#export-idle button.export-button")
    expect(export_btn).to_be_visible(timeout=5000)


@pytest.mark.django_db(transaction=True)
def test_export_button_error_state(logged_in_page, live_server, meal_plan_with_day):
    """Clicking export transitions to progress state, then to error state on a failed job."""
    plan, _ = meal_plan_with_day
    page = logged_in_page
    fake_job_id = "12345678-0000-0000-0000-000000000001"

    # Mock POST /api/export-jobs/ — only intercept POST, let GETs fall through
    def handle_post_or_continue(route):
        if route.request.method == "POST":
            route.fulfill(
                status=201,
                content_type="application/json",
                body=(
                    f'{{"id": "{fake_job_id}", "status": "pending",'
                    f' "progress": 0, "error_message": ""}}'
                ),
            )
        else:
            route.continue_()

    page.route("**/api/export-jobs/", handle_post_or_continue)

    # Mock GET poll — always return failed
    page.route(
        f"**/api/export-jobs/{fake_job_id}/",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                f'{{"id": "{fake_job_id}", "status": "failed",'
                f' "progress": 0, "error_message": "Test failure message"}}'
            ),
        ),
    )

    page.goto(f"{live_server.url}/meal-plan/{plan.pk}/preview/")
    page.wait_for_selector("#export-idle button.export-button", timeout=5000)
    page.locator("#export-idle button.export-button").click()

    # Progress card should appear while pending, then error card after poll responds
    expect(page.locator("#export-error")).to_be_visible(timeout=5000)
    expect(page.locator(".export-error-msg")).to_contain_text("Test failure message")

    # Retry button must be visible in the error state
    retry_btn = page.locator("#export-error button.export-button")
    expect(retry_btn).to_be_visible()
