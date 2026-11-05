"""Browserprüfung gegen den bewusst gestarteten Testmodus, siehe web/README.md."""
import sys

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Verhindert, dass die Prüfung versehentlich einen echten Kern benutzt.
        status = context.request.get(url + "/api/status").json()
        assert status["fake"] is True, "Bitte mit HARNESS_FAKE=1 starten."
        page.goto(url)
        expect(page.locator("#connectionMode")).to_have_text("Testmodus")
        expect(page.locator("#btnRelease")).to_be_disabled()
        expect(page.locator("#btnCopy")).to_be_disabled()
        expect(page.locator("#btnSend")).to_have_count(0)
        expect(page.locator("#stepOriginal")).to_have_attribute("aria-current", "step")

        page.locator("#btnExample").click()
        page.locator("#btnAnalyze").click()
        expect(page.locator("#btnRelease")).to_be_enabled()
        expect(page.locator("#btnCopy")).to_be_disabled()
        expect(page.locator("#releaseStatus")).to_have_text("Prüfung nötig")
        expect(page.locator("#stepReview")).to_have_attribute("aria-current", "step")
        expect(page.locator("#counter")).to_contain_text("Weitergabe nur durch dich")

        # Unsichere Stelle: sichtbar, ersetzbar, und „Passt so“ blendet sie aus.
        suspect = page.locator("#masked .suspect")
        expect(suspect).to_have_text("Nordlicht")
        expect(page.locator("#notes")).to_contain_text("1 unsichere Stelle")
        suspect.click()
        expect(page.locator("#menuKeep")).to_be_visible()
        page.locator("#menuKeep").click()
        expect(suspect).to_have_count(0)
        expect(page.locator("#notes")).not_to_contain_text("unsichere Stelle")

        page.locator("#btnRelease").click()
        expect(page.locator("#btnCopy")).to_be_enabled()
        expect(page.locator("#releaseStatus")).to_have_text("Freigegeben")
        expect(page.locator("#stepAnswer")).to_have_attribute("aria-current", "step")
        page.locator("#btnCopy").click()
        expect(page.locator("#copied")).to_have_text("Kopiert.")
        assert "[PERSON_1]" in page.evaluate("navigator.clipboard.readText()")
        page.locator("#answerInput").fill("[PERSON_1] schreibt an [PERSON_2].")
        page.locator("#btnRestore").click()
        expect(page.locator("#answerStatus")).to_have_text("Zurückübersetzt")
        expect(page.locator("#answer")).to_contain_text("Erika Musterfrau")

        page.locator("#masked .chip button").first.click()
        expect(page.locator("#releaseStatus")).to_have_text("Prüfung nötig")
        expect(page.locator("#btnCopy")).to_be_disabled()
        expect(page.locator("#answerStatus")).to_have_text("Ausstehend")
        for width in [390, 768, 1024, 1440]:
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width

        assert not errors, errors
        browser.close()
    print("Browserprüfung bestanden: Freigabe, Kopieren, Rückübersetzung und vier Bildschirmbreiten.")


if __name__ == "__main__":
    main()
