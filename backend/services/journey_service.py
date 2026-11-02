import os
import time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

from schema.schema import (
    JourneyScenario,
    JourneyStep,
    JourneyReport,
    StepResult,
    ActionType,
    LoginJourneyRequest,
)
from services.url_validator import validate_url, URLValidationError


SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "screenshots"
)


async def execute_journey(scenario: JourneyScenario) -> JourneyReport:
    """
    Execute a multi-step user journey deterministically using Playwright.

    Executes each step in order:
    - Measures duration of each action
    - Validates expected outcomes and assertions
    - If a step fails, captures an immediate failure screenshot, records
      reproduction steps, and halts execution cleanly.
    """

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    start_total_time = time.perf_counter()
    step_results: list[StepResult] = []
    reproduction_steps: list[str] = []
    failed_step_index: int | None = None
    overall_status = "passed"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            for idx, step in enumerate(scenario.steps, start=1):
                step_desc = step.description or f"{step.action.value} on {step.selector or step.value}"
                step_start = time.perf_counter()
                error_message: str | None = None
                failure_screenshot: str | None = None

                try:

                    if step.action == ActionType.NAVIGATE:
                        if not step.value:
                            raise ValueError("Navigate action requires a target URL in 'value'.")
                        validate_url(step.value)

                        await page.goto(
                            step.value,
                            wait_until="domcontentloaded",
                            timeout=15000
                        )
                        reproduction_steps.append(f"Step {idx}: Navigate to '{step.value}'")

                    elif step.action == ActionType.CLICK:
                        if not step.selector:
                            raise ValueError("Click action requires a 'selector'.")

                        await page.click(step.selector, timeout=8000)
                        reproduction_steps.append(f"Step {idx}: Click '{step.selector}'")

                    elif step.action == ActionType.FILL:
                        if not step.selector:
                            raise ValueError("Fill action requires a 'selector'.")

                        val = step.value or ""
                        is_sensitive = "password" in step.selector.lower()
                        log_val = "******" if is_sensitive else val

                        await page.fill(step.selector, val, timeout=8000)
                        reproduction_steps.append(
                            f"Step {idx}: Fill '{step.selector}' with '{log_val}'"
                        )

                    elif step.action == ActionType.ASSERT_VISIBLE:
                        if not step.selector:
                            raise ValueError("Assert visible requires a 'selector'.")

                        await page.wait_for_selector(
                            step.selector,
                            state="visible",
                            timeout=8000
                        )
                        reproduction_steps.append(
                            f"Step {idx}: Assert element '{step.selector}' is visible"
                        )

                    elif step.action == ActionType.ASSERT_TEXT:
                        if not step.selector:
                            raise ValueError("Assert text requires a 'selector'.")

                        element = await page.wait_for_selector(
                            step.selector,
                            state="visible",
                            timeout=8000
                        )
                        actual_text = (await element.inner_text()) if element else ""
                        expected_text = step.value or ""

                        if expected_text.lower() not in actual_text.lower():
                            raise AssertionError(
                                f"Expected text '{expected_text}' not found in element '{step.selector}'. "
                                f"Actual text: '{actual_text.strip()[:100]}'"
                            )

                        reproduction_steps.append(
                            f"Step {idx}: Assert text '{expected_text}' exists in '{step.selector}'"
                        )

                    elif step.action == ActionType.ASSERT_URL:
                        expected_url_part = step.value or ""
                        current_url = page.url
                        if expected_url_part.lower() not in current_url.lower():
                            try:
                                await page.wait_for_url(f"**/*{expected_url_part}*", timeout=5000)
                                current_url = page.url
                            except Exception:
                                pass

                        if expected_url_part.lower() not in current_url.lower():
                            raise AssertionError(
                                f"Expected URL to contain '{expected_url_part}', but actual URL is '{current_url}'"
                            )

                        reproduction_steps.append(
                            f"Step {idx}: Assert URL contains '{expected_url_part}' (Current: '{current_url}')"
                        )

                    elif step.action == ActionType.WAIT:
                        seconds = float(step.value or 1.0)
                        await page.wait_for_timeout(seconds * 1000)
                        reproduction_steps.append(f"Step {idx}: Wait {seconds} seconds")

                    else:
                        raise ValueError(f"Unsupported action type: {step.action}")

                    duration_ms = round((time.perf_counter() - step_start) * 1000, 2)

                    step_results.append(
                        StepResult(
                            step_index=idx,
                            action=step.action.value,
                            description=step_desc,
                            status="passed",
                            duration_ms=duration_ms
                        )
                    )

                except Exception as exc:
                    duration_ms = round((time.perf_counter() - step_start) * 1000, 2)
                    error_message = str(exc)
                    overall_status = "failed"
                    failed_step_index = idx

                    # Capture failure screenshot
                    try:
                        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                        filename = f"failure_{scenario.scenario_id}_{idx}_{timestamp}.png"
                        failure_screenshot = os.path.join(SCREENSHOTS_DIR, filename)
                        await page.screenshot(path=failure_screenshot, full_page=True)
                    except Exception:
                        failure_screenshot = None

                    reproduction_steps.append(
                        f"Step {idx} [FAILED]: {step_desc} -> Error: {error_message}"
                    )

                    step_results.append(
                        StepResult(
                            step_index=idx,
                            action=step.action.value,
                            description=step_desc,
                            status="failed",
                            duration_ms=duration_ms,
                            error_message=error_message,
                            screenshot_path=failure_screenshot
                        )
                    )
                    break

        finally:
            await browser.close()

    total_duration_ms = round((time.perf_counter() - start_total_time) * 1000, 2)
    passed_steps = sum(1 for s in step_results if s.status == "passed")

    return JourneyReport(
        scenario_id=scenario.scenario_id,
        name=scenario.name,
        persona=scenario.persona,
        objective=scenario.objective,
        status=overall_status,
        total_steps=len(scenario.steps),
        passed_steps=passed_steps,
        failed_step_index=failed_step_index,
        duration_ms=total_duration_ms,
        step_results=step_results,
        reproduction_steps=reproduction_steps,
        executed_at=datetime.now(timezone.utc)
    )


def create_login_scenario(request: LoginJourneyRequest) -> JourneyScenario:
    """
    Construct a deterministic JourneyScenario from a LoginJourneyRequest.
    Ensures safe handling of credentials and standardizes the authentication flow.
    """

    steps = [
        JourneyStep(
            action=ActionType.NAVIGATE,
            value=str(request.login_url),
            description=f"Navigate to login page: {request.login_url}"
        ),
        JourneyStep(
            action=ActionType.FILL,
            selector=request.username_selector,
            value=request.username_or_email,
            description=f"Enter username/email: {request.username_or_email}"
        ),
        JourneyStep(
            action=ActionType.FILL,
            selector=request.password_selector,
            value=request.password,
            description="Enter password"
        ),
        JourneyStep(
            action=ActionType.CLICK,
            selector=request.submit_selector,
            description="Click login submit button"
        ),
    ]

    if request.expected_url_contains:
        steps.append(
            JourneyStep(
                action=ActionType.ASSERT_URL,
                value=request.expected_url_contains,
                description=f"Verify destination URL contains '{request.expected_url_contains}'"
            )
        )

    if request.expected_element_selector:
        steps.append(
            JourneyStep(
                action=ActionType.ASSERT_VISIBLE,
                selector=request.expected_element_selector,
                description=f"Verify authenticated element '{request.expected_element_selector}' is visible"
            )
        )

    if not request.expected_url_contains and not request.expected_element_selector:
        steps.append(
            JourneyStep(
                action=ActionType.WAIT,
                value="2.0",
                description="Wait for post-login redirection or state change"
            )
        )

    return JourneyScenario(
        scenario_id=f"SCN-LOGIN-{int(time.time())}",
        name=f"Automated Login Verification ({request.persona})",
        persona=request.persona,
        objective=f"Test authentication flow on {request.login_url} and verify successful sign-in.",
        steps=steps
    )

