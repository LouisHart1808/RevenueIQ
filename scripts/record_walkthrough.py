"""Record an actual browser workflow with explanatory captions; no metric substitution."""

from pathlib import Path
import os
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="revenueiq-video-") as folder, sync_playwright() as p:
        executable = os.getenv("BROWSER_EXECUTABLE") or (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if Path("/Applications/Google Chrome.app").exists()
            else None
        )
        browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            record_video_dir=folder,
            record_video_size={"width": 1440, "height": 960},
        )
        page = context.new_page()
        page.goto(os.getenv("BASE_URL", "http://127.0.0.1:8050"), wait_until="networkidle")
        page.get_by_text("R$ 13,221,498", exact=True).wait_for()

        def caption(message):
            page.evaluate(
                "message=>{let el=document.getElementById('walkthrough-caption');if(!el){el=document.createElement('div');el.id='walkthrough-caption';el.style.cssText='position:fixed;bottom:16px;left:280px;right:35px;background:#102237f2;color:white;padding:18px 22px;border-radius:9px;z-index:10000;font:17px Arial;box-shadow:0 4px 20px #0003;pointer-events:none';document.body.appendChild(el);}el.textContent=message;}",
                message,
            )
            page.wait_for_timeout(4000)

        caption("RevenueIQ: actual historical Olist transactions, reconciled through PostgreSQL and dbt.")
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(500)
        caption("Merchandise value is not profit. Click a contributor to investigate its baskets.")
        bar = page.locator("[id*=drill][id*=category]").first.locator(".barlayer .point path").first
        bar.scroll_into_view_if_needed()
        box = bar.bounding_box()
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.get_by_text("Exploring category:", exact=False).wait_for()
        page.evaluate("window.scrollTo(0,0)")
        caption("A chart click applies a shared category filter; whole-basket totals stay consistent.")
        page.get_by_role("button", name="Reset filters").click()
        page.get_by_text("R$ 13,221,498", exact=True).wait_for()
        page.get_by_role("button", name="03 Customer Intelligence").click()
        page.locator("#dates input").nth(1).fill("30 Jun 2017")
        page.locator("#dates input").nth(1).press("Enter")
        page.get_by_text("Customer cutoff: 2017-06-30.", exact=False).wait_for()
        caption("Travel back to June 2017: later purchases and deliveries cannot enter customer features.")
        page.locator("#cohort-select input").fill("2017-03-01")
        page.locator("#cohort-select input").press("Enter")
        page.locator("#cohort-chart").scroll_into_view_if_needed()
        page.get_by_text("Acquisition cohort 2017-03-01", exact=True).wait_for()
        caption("Follow the original acquisition cohort only through the cutoff; future ages are absent.")
        page.get_by_role("button", name="Reset filters").click()
        page.get_by_role("button", name="07 Advanced Analytics").click()
        page.evaluate("window.scrollTo(0,0)")
        page.get_by_text("Locked final-period results", exact=False).wait_for()
        caption("Model selection uses development months. The final period tests predictions and interval coverage.")
        page.get_by_text("Locked final-period results", exact=False).scroll_into_view_if_needed()
        caption("Only one of three test months falls inside the empirical band. The limitation stays visible.")
        page.get_by_role("button", name="08 Scenario Planning").click()
        page.locator("#scenario-result h2").wait_for()
        page.wait_for_load_state("networkidle")
        page.locator("#customer-growth [role=slider]").focus()
        page.keyboard.press("ArrowRight")
        page.get_by_text("Change from selected baseline: R$ 132,215 (+1.0%)", exact=True).wait_for()
        page.locator("#scenario-result").scroll_into_view_if_needed()
        caption("A +1% customer assumption changes projected merchandise value; it is not an observed causal uplift.")
        video = page.video
        context.close()
        video.save_as(str(ROOT / "reports/walkthrough.webm"))
        browser.close()


if __name__ == "__main__":
    main()
