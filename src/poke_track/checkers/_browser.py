from contextlib import contextmanager

from playwright.sync_api import sync_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@contextmanager
def rendered_page(url: str, timeout_ms: int = 30000):
    """Load `url` in a real (headless) browser and yield (response, page).

    Some retailers only expose live stock status after client-side JS runs,
    so a plain HTTP GET isn't enough. This launches a fresh browser per call,
    which is fine at multi-minute poll intervals.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(1500)
            yield response, page
        finally:
            browser.close()
