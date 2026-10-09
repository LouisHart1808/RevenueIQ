"""Real browser navigation, filter, scenario, export, and responsive checks."""

from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    executable = os.getenv("BROWSER_EXECUTABLE") or (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if Path("/Applications/Google Chrome.app").exists()
        else None
    )
    browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
    page = browser.new_page(viewport={"width": 1512, "height": 1100}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(os.getenv("BASE_URL", "http://127.0.0.1:8050"), wait_until="networkidle")
    page.get_by_text("R$ 13,221,498", exact=True).wait_for()
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(ROOT / "reports/dashboard-overview.png"), full_page=True)
    results = []
    for i, name in enumerate(
        [
            "Executive Overview",
            "Revenue Intelligence",
            "Customer Intelligence",
            "Product Intelligence",
            "Operations Intelligence",
            "Geographic Intelligence",
            "Advanced Analytics",
            "Scenario Planning",
            "Data Quality & Methodology",
        ]
    ):
        page.get_by_role("button", name=f"{i + 1:02d} {name}").click()
        page.wait_for_timeout(700)
        page.wait_for_function("document.querySelector('h1').textContent === '" + name + "'")
        page.wait_for_load_state("networkidle")
        assert page.get_by_text("This view could not load.", exact=False).count() == 0, name
        page.screenshot(path=str(ROOT / f"reports/dashboard-{i + 1:02d}.png"), full_page=True)
        results.append({"page": name, "passed": True})
    page.get_by_role("button", name="01 Executive Overview").click()
    page.get_by_text("R$ 13,221,498", exact=True).wait_for()
    page.wait_for_load_state("networkidle")
    category_chart = page.locator("[id*=drill][id*=category]").first
    bar = category_chart.locator(".barlayer .point path").first
    bar.scroll_into_view_if_needed()
    box = bar.bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.get_by_text("Exploring category:", exact=False).wait_for()
    page.wait_for_load_state("networkidle")
    assert page.locator("#category").inner_text().strip() != "All categories"
    page.get_by_role("button", name="Reset filters").click()
    page.get_by_text("R$ 13,221,498", exact=True).wait_for()
    page.wait_for_load_state("networkidle")
    region = page.locator("[id*=drill][id*=state]").first.locator(".barlayer .point path").first
    region.scroll_into_view_if_needed()
    box = region.bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.get_by_text("Exploring state:", exact=False).wait_for()
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="Reset filters").click()
    page.get_by_role("button", name="02 Revenue Intelligence").click()
    seller_bar = page.locator("[id*=drill][id*=seller]").first.locator(".barlayer .point path").first
    seller_bar.scroll_into_view_if_needed()
    box = seller_bar.bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.get_by_text("Exploring seller:", exact=False).wait_for()
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="Reset filters").click()
    page.get_by_role("button", name="01 Executive Overview").click()
    page.get_by_text("R$ 13,221,498", exact=True).wait_for()
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="04 Product Intelligence").click()
    page.get_by_text("Product explorer", exact=True).wait_for()
    page.wait_for_load_state("networkidle")
    expect(page.locator("#product-result-count")).to_contain_text("matching products")
    page.locator("#product-search").fill("health_beauty")
    page.locator("#product-search").press("Enter")
    page.wait_for_load_state("networkidle")
    page.locator("#product-sort input").fill("Most units sold")
    page.locator("#product-sort input").press("Enter")
    page.wait_for_load_state("networkidle")
    with page.expect_download() as products_download:
        page.get_by_role("button", name="Export matching products", exact=True).click()
    import csv
    with open(products_download.value.path(), newline="") as exported:
        products = list(csv.DictReader(exported))
    assert len(products) > 200, "Product export was truncated"
    assert {row["category"] for row in products} == {"health_beauty"}
    units = [int(row["units"]) for row in products]
    assert units == sorted(units, reverse=True)
    page.locator("#product-search").fill("no_such_product_12345")
    page.locator("#product-search").press("Enter")
    page.get_by_text("No products match this search.", exact=True).wait_for()
    page.get_by_role("button", name="01 Executive Overview").click()
    page.get_by_text("R$ 13,221,498", exact=True).wait_for()
    page.wait_for_load_state("networkidle")
    with page.expect_download() as download:
        page.get_by_role("button", name="Export CSV").click()
    assert download.value.suggested_filename == "revenueiq_monthly.csv"
    page.locator("#state input").fill("SP")
    page.locator("#state input").press("Enter")
    expect(page.get_by_text("R$ 13,221,498", exact=True)).to_have_count(0, timeout=30000)
    page.wait_for_load_state("networkidle")
    page.locator("#category input").fill("health_beauty")
    page.locator("#category input").press("Enter")
    page.wait_for_load_state("networkidle")
    assert page.get_by_text("No delivered orders", exact=False).count() == 0
    page.get_by_role("button", name="Reset filters").click()
    page.get_by_text("R$ 13,221,498", exact=True).wait_for()
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="08 Scenario Planning").click()
    page.locator("#scenario-result h2").wait_for()
    page.wait_for_load_state("networkidle")
    page.locator("#customer-growth [role=slider]").wait_for()
    page.locator("#customer-growth [role=slider]").focus()
    page.keyboard.press("ArrowRight")
    page.get_by_text("Change from selected baseline: R$ 132,215 (+1.0%)", exact=True).wait_for()
    page.get_by_role("button", name="03 Customer Intelligence").click()
    page.locator("#cohort-select input").fill("2017-01-01")
    page.locator("#cohort-select input").press("Enter")
    page.get_by_text("Acquisition cohort 2017-01-01", exact=True).wait_for()
    page.get_by_role("button", name="01 Executive Overview").click()
    page.get_by_text("R$ 13,221,498", exact=True).wait_for()
    page.wait_for_load_state("networkidle")
    assert page.locator("#drill-feedback").inner_text() == "", "Reset left stale filter feedback"
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(1200)
    page.screenshot(path=str(ROOT / "reports/dashboard-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), "Mobile horizontal overflow"
    browser.close()
    (ROOT / "reports/browser_validation.json").write_text(
        json.dumps(
            {
                "navigation": results,
                "javascript_errors": errors,
                "csv_download": True,
                "product_search_sort_and_complete_export": True,
                "state_category_filters": True,
                "chart_drill_down": True,
                "scenario_slider": True,
                "cohort_selection": True,
                "responsive_width": 390,
            },
            indent=2,
        )
    )
    assert not errors, errors
