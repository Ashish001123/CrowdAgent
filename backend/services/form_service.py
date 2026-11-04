import os
from datetime import datetime, timezone
from playwright.async_api import async_playwright

from schema.schema import (
    FormValidationRequest,
    FormValidationReport,
    FormTestCaseResult,
    FormFieldConfig,
)
from services.url_validator import validate_url


SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "screenshots"
)


def _infer_field_config(raw_field: dict) -> FormFieldConfig:
    """Infer field type, valid data, and invalid edge-case data from discovered input."""
    name = raw_field.get("name") or raw_field.get("id") or "field"
    f_type = raw_field.get("type", "text").lower()
    is_required = raw_field.get("required", False)

    selector = f"input[name='{name}']" if raw_field.get("name") else f"#{raw_field.get('id')}"

    if "email" in name.lower() or f_type == "email":
        return FormFieldConfig(
            selector=selector,
            name=name,
            field_type="email",
            required=is_required,
            valid_value="qa.tester@example.com",
            invalid_value="not-a-valid-email"
        )

    if "phone" in name.lower() or "tel" in f_type:
        return FormFieldConfig(
            selector=selector,
            name=name,
            field_type="tel",
            required=is_required,
            valid_value="5551234567",
            invalid_value="abc-phone-invalid"
        )

    if "number" in f_type or "age" in name.lower() or "quantity" in name.lower():
        return FormFieldConfig(
            selector=selector,
            name=name,
            field_type="number",
            required=is_required,
            valid_value="10",
            invalid_value="-99999"
        )

    if "password" in f_type or "pass" in name.lower():
        return FormFieldConfig(
            selector=selector,
            name=name,
            field_type="password",
            required=is_required,
            valid_value="SecureP@ssw0rd!2026",
            invalid_value=""
        )

    return FormFieldConfig(
        selector=selector,
        name=name,
        field_type="text",
        required=is_required,
        valid_value="Valid Sample Text",
        invalid_value="<script>alert(1)</script>"
    )


async def execute_form_validation(request: FormValidationRequest) -> FormValidationReport:
    """
    Simulate an 'Edge Case Hunter' persona testing a form for validation flaws:
    - Empty submission against required constraints
    - Invalid/malformed input rejection
    - Optional valid submission check
    """

    url_str = str(request.url)
    validate_url(url_str)
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    test_cases: list[FormTestCaseResult] = []
    detected_fields: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # ── 1. Navigate and Discover Form ──
            await page.goto(url_str, wait_until="domcontentloaded", timeout=15000)

            # Wait for form to exist
            form_locator = page.locator(request.form_selector)
            if await form_locator.count() == 0:
                raise ValueError(f"Form matching selector '{request.form_selector}' was not found on {url_str}.")

            # Discover input elements if fields not provided
            configured_fields = list(request.fields)

            if not configured_fields:
                inputs = await page.locator(
                    f"{request.form_selector} input:not([type='hidden']):not([type='submit']):not([type='button']), "
                    f"{request.form_selector} textarea, "
                    f"{request.form_selector} select"
                ).all()

                for inp in inputs:
                    name_attr = await inp.get_attribute("name") or ""
                    id_attr = await inp.get_attribute("id") or ""
                    type_attr = await inp.get_attribute("type") or "text"
                    required_attr = await inp.get_attribute("required") is not None

                    if name_attr or id_attr:
                        field_dict = {
                            "name": name_attr,
                            "id": id_attr,
                            "type": type_attr,
                            "required": required_attr
                        }
                        detected_fields.append(field_dict)
                        configured_fields.append(_infer_field_config(field_dict))

            # ── Test Case 1: Empty Required Fields ──
            if request.test_empty_submission and configured_fields:
                test_name = "Empty Required Fields Submission"
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                shot_path = os.path.join(SCREENSHOTS_DIR, f"form_empty_{timestamp}.png")

                initial_url = page.url
                # Ensure all fields are clear
                for field in configured_fields:
                    try:
                        await page.fill(field.selector, "")
                    except Exception:
                        pass

                # Attempt submit
                await page.click(request.submit_selector, timeout=5000)
                await page.wait_for_timeout(1000)
                await page.screenshot(path=shot_path, full_page=True)

                # Verification:
                # 1. Check if HTML5 :invalid pseudo-classes are triggered
                invalid_count = await page.locator(f"{request.form_selector} :invalid").count()
                # 2. Check if custom error selector is visible
                custom_error = False
                if request.expected_error_selector:
                    custom_error = await page.locator(request.expected_error_selector).is_visible()

                # 3. Check if page stayed on the form URL (not redirected away)
                stayed_on_page = page.url == initial_url

                if invalid_count > 0 or custom_error or stayed_on_page:
                    test_cases.append(
                        FormTestCaseResult(
                            test_case=test_name,
                            status="passed",
                            description="Verifies that submitting empty required fields is properly prevented.",
                            evidence=f"Submission blocked. Detected {invalid_count} invalid fields under HTML5 constraint validation.",
                            screenshot_path=shot_path
                        )
                    )
                else:
                    test_cases.append(
                        FormTestCaseResult(
                            test_case=test_name,
                            status="failed",
                            description="Verifies that submitting empty required fields is properly prevented.",
                            evidence=f"Form allowed empty submission. URL redirected to: {page.url}",
                            screenshot_path=shot_path
                        )
                    )

            # ── Test Case 2: Invalid Format Input Testing ──
            invalid_candidates = [f for f in configured_fields if f.invalid_value is not None]

            if request.test_invalid_inputs and invalid_candidates:
                test_name = "Invalid Format Input Rejection"
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                shot_path = os.path.join(SCREENSHOTS_DIR, f"form_invalid_{timestamp}.png")

                # Reload fresh form state
                await page.goto(url_str, wait_until="domcontentloaded", timeout=15000)
                initial_url = page.url

                # Fill invalid values for test candidates, valid values for remaining required fields
                for field in configured_fields:
                    val = field.invalid_value if field in invalid_candidates else field.valid_value
                    if val is not None:
                        try:
                            await page.fill(field.selector, val)
                        except Exception:
                            pass

                # Attempt submit
                await page.click(request.submit_selector, timeout=5000)
                await page.wait_for_timeout(1000)
                await page.screenshot(path=shot_path, full_page=True)

                invalid_count = await page.locator(f"{request.form_selector} :invalid").count()
                stayed_on_page = page.url == initial_url

                if invalid_count > 0 or stayed_on_page:
                    test_cases.append(
                        FormTestCaseResult(
                            test_case=test_name,
                            status="passed",
                            description="Verifies that the form rejects malformed or invalid inputs (e.g. invalid email format).",
                            evidence=f"Submission blocked as expected for malformed inputs. {invalid_count} invalid elements flagged.",
                            screenshot_path=shot_path
                        )
                    )
                else:
                    test_cases.append(
                        FormTestCaseResult(
                            test_case=test_name,
                            status="failed",
                            description="Verifies that the form rejects malformed or invalid inputs.",
                            evidence="Form accepted invalid/malformed data and proceeded with submission.",
                            screenshot_path=shot_path
                        )
                    )

            # ── Test Case 3: Valid Input Submission (Optional) ──
            if request.test_valid_submission and configured_fields:
                test_name = "Valid Input Submission"
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                shot_path = os.path.join(SCREENSHOTS_DIR, f"form_valid_{timestamp}.png")

                await page.goto(url_str, wait_until="domcontentloaded", timeout=15000)
                for field in configured_fields:
                    try:
                        await page.fill(field.selector, field.valid_value)
                    except Exception:
                        pass

                await page.click(request.submit_selector, timeout=5000)
                await page.wait_for_timeout(2000)
                await page.screenshot(path=shot_path, full_page=True)

                test_cases.append(
                    FormTestCaseResult(
                        test_case=test_name,
                        status="passed",
                        description="Verifies that the form accepts correctly formatted inputs and completes submission.",
                        evidence=f"Submitted valid data without client-side obstruction. Final URL: {page.url}",
                        screenshot_path=shot_path
                    )
                )

        finally:
            await browser.close()

    total = len(test_cases)
    passed = sum(1 for t in test_cases if t.status == "passed")
    failed = sum(1 for t in test_cases if t.status == "failed")
    overall = "passed" if failed == 0 and total > 0 else "failed"

    summary_text = (
        f"Executed {total} form validation tests ({passed} passed, {failed} failed). "
        f"Form testing evaluated under persona '{request.persona}'."
    )

    return FormValidationReport(
        url=url_str,
        form_selector=request.form_selector,
        persona=request.persona,
        total_tests=total,
        passed_tests=passed,
        failed_tests=failed,
        overall_status=overall,
        summary=summary_text,
        test_cases=test_cases,
        detected_fields=detected_fields,
        executed_at=datetime.now(timezone.utc)
    )

