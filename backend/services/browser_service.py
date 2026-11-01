import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from services.issue_classifier import classify_http_response


SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "screenshots"
)


async def analyze_website(
    url: str,
    expected_http_statuses: dict | None = None
):

    if expected_http_statuses is None:
        expected_http_statuses = {}

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=True
        )

        try:
            page = await browser.new_page()

            console_errors = []
            page_errors = []
            failed_requests = []
            http_errors = []
            page.on(
                "console",
                lambda message: console_errors.append({
                    "message": message.text,
                    "type": message.type
                }) if message.type == "error" else None
            )
            page.on(
                "pageerror",
                lambda error: page_errors.append(str(error))
            )
            page.on(
                "requestfailed",
                lambda request: failed_requests.append({
                    "url": request.url,
                    "error": request.failure
                })
            )
            page.on(
                "response",
                lambda response: http_errors.append({
                    "url": response.url,
                    "status": response.status
                }) if response.status >= 400 else None
            )

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=15000
            )

            title = await page.title()

            buttons = await page.locator(
                "button"
            ).all_text_contents()

            links = await page.locator(
                "a"
            ).all_text_contents()

            forms = await page.locator(
                "form"
            ).count()

            classified_issues = [
                classify_http_response(
                    error,
                    expected_http_statuses
                )
                for error in http_errors
            ]

            # ── Capture screenshot evidence ──

            screenshot_path = None

            try:
                os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

                domain = urlparse(url).netloc.replace(":", "_")
                timestamp = datetime.now(timezone.utc).strftime(
                    "%Y%m%d_%H%M%S"
                )
                filename = f"{timestamp}_{domain}.png"
                screenshot_path = os.path.join(
                    SCREENSHOTS_DIR, filename
                )

                await page.screenshot(
                    path=screenshot_path,
                    full_page=True
                )

            except Exception:
                # Screenshot failure should not break the scan
                screenshot_path = None

            return {
                "url": page.url,
                "title": title,

                "http_status": (
                    response.status if response else None
                ),

                "buttons": buttons,
                "links": links,
                "forms_count": forms,

                "console_errors": console_errors,
                "page_errors": page_errors,
                "failed_requests": failed_requests,
                "http_errors": http_errors,

                "issues": classified_issues,
                "screenshot_path": screenshot_path
            }

        finally:
            await browser.close()