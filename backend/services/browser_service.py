from playwright.async_api import async_playwright


async def analyze_website(url: str):

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=True
        )

        try:
            page = await browser.new_page()

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=15000
            )

            title = await page.title()

            buttons = await page.locator("button").all_text_contents()

            links = await page.locator("a").all_text_contents()

            forms = await page.locator("form").count()

            return {
                "url": page.url,
                "title": title,
                "http_status": response.status if response else None,
                "buttons": buttons,
                "links": links,
                "forms_count": forms
            }

        finally:
            await browser.close()