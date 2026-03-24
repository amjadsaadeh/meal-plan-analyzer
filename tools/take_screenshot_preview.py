from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a reasonably large viewport to look nice
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        page.goto("http://localhost:8000/login/")
        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "Test1234")
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_url("http://localhost:8000/")
        page.wait_for_load_state("networkidle")

        # Meal Plan Preview (PDF view simulation)
        print("Taking Meal Plan Preview screenshot...")
        page.goto("http://localhost:8000/plan/7/preview/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.screenshot(path="docs/assets/meal_plan_preview.png", full_page=True)

        browser.close()


if __name__ == "__main__":
    run()
