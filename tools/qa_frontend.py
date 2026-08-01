from __future__ import annotations

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8474/"
VIEWPORTS = {"desktop": (1600, 1000), "tablet": (768, 900), "mobile": (480, 860)}
OUT = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "qa-v2"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for name, (width, height) in VIEWPORTS.items():
            context = browser.new_context(viewport={"width": width, "height": height})
            context.add_init_script("localStorage.setItem('wizard_done','1'); localStorage.setItem('selected_path','opencode_free');")
            page = context.new_page()
            js_errors: list[str] = []
            console_errors: list[str] = []
            bad_responses: list[dict] = []
            page.on("pageerror", lambda exc, bucket=js_errors: bucket.append(str(exc)))
            page.on("console", lambda msg, bucket=console_errors: bucket.append(msg.text) if msg.type == "error" else None)
            page.on("response", lambda response, bucket=bad_responses: bucket.append({"url": response.url, "status": response.status}) if response.status >= 400 else None)
            page.goto(BASE_URL, wait_until="networkidle")
            page.locator("#composer-input").wait_for(state="visible")

            metrics = page.evaluate("""() => ({
              viewport: innerWidth,
              scrollWidth: document.documentElement.scrollWidth,
              overflowX: document.documentElement.scrollWidth > innerWidth,
              composerWidth: document.querySelector('.composer').getBoundingClientRect().width,
              composerBottom: document.querySelector('.composer').getBoundingClientRect().bottom,
              targetMin: Math.min(...Array.from(document.querySelectorAll('button')).map(x => x.getBoundingClientRect()).filter(rect => rect.width > 0 && rect.height > 0).map(rect => rect.height)),
              visibleNav: Array.from(document.querySelectorAll('.primary-nav [data-view]')).filter(x => getComputedStyle(x).display !== 'none').map(x => x.dataset.view)
            })""")

            # Real navigation and async provider rendering.
            page.locator('[data-view="settings"]').click()
            page.locator("#provider-settings").wait_for(state="visible")
            page.wait_for_timeout(250)
            provider_cards = page.locator("#provider-settings .provider-card").count()
            page.locator('[data-view="executive"]').click()
            page.locator("#capture-input").wait_for(state="visible")
            page.locator('[data-view="workspace"]').click()
            page.locator("#composer-input").wait_for(state="visible")

            # Keyboard command palette contract.
            page.keyboard.press("Control+K")
            palette_visible = page.locator("#command-palette").evaluate("el => el.classList.contains('open')")
            page.keyboard.press("Escape")

            page.screenshot(path=str(OUT / f"{name}-{width}x{height}.png"), full_page=True)
            expected_mobile_nav = ["workspace", "executive", "memory", "settings"]
            passed = (
                not metrics["overflowX"]
                and metrics["composerWidth"] >= min(360, width - 24)
                and not js_errors
                and not console_errors
                and not bad_responses
                and provider_cards >= 4
                and palette_visible
                and (name != "mobile" or metrics["targetMin"] >= 44)
                and (name != "mobile" or metrics["visibleNav"] == expected_mobile_nav)
            )
            results[name] = {
                "width": width,
                "height": height,
                "metrics": metrics,
                "provider_cards": provider_cards,
                "palette_visible": palette_visible,
                "js_errors": js_errors,
                "console_errors": console_errors,
                "bad_responses": bad_responses,
                "passed": passed,
            }
            context.close()
        browser.close()

    (OUT / "viewport-results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if all(item["passed"] for item in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
