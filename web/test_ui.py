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
        expect(page.locator("#fakeBand")).to_be_visible()
        expect(page.locator("header, footer, .workflow, .summary, #connectionMode")).to_have_count(0)
        workspace = page.locator("#workspace")
        original = page.locator('[data-step="stepOriginal"]')
        review = page.locator('[data-step="stepReview"]')
        answer = page.locator('[data-step="stepAnswer"]')

        def expanded(step):
            expect(workspace).to_have_attribute("data-focus", step)
            page.wait_for_function("""step => {
                const cards = [...document.querySelectorAll('.work-card')];
                const active = cards.find(card => card.dataset.step === step);
                return cards.every(card => card === active || active.clientWidth > card.clientWidth * 1.3);
            }""", arg=step)

        # Hover vergrößert die Spalte; Schreiben hält den Fokus fest.
        original.hover()
        expanded("stepOriginal")
        review.hover()
        expanded("stepReview")
        answer.hover()
        expanded("stepAnswer")
        page.locator("#original").fill("Text zum Schreiben")
        expanded("stepOriginal")
        review.hover()
        expect(workspace).to_have_attribute("data-focus", "stepOriginal")
        page.locator("#h-masked").click()
        expanded("stepReview")
        expect(page.locator("#btnRelease")).to_be_disabled()
        expect(page.locator("#btnCopy")).to_be_disabled()
        expect(page.locator("#btnSend")).to_have_count(0)
        expect(page.locator("#dispatchStatus")).to_contain_text("Kopieren bis zur Freigabe gesperrt")

        page.locator("#btnExample").click()
        page.locator("#btnAnalyze").click()
        expect(page.locator("#btnRelease")).to_be_enabled()
        expect(page.locator("#btnCopy")).to_be_disabled()
        expect(page.locator("#releaseStatus")).to_have_text("Prüfung nötig")
        expect(page.locator(".work-card[data-active=true]")).to_have_attribute("data-step", "stepReview")
        expect(page.locator("#btnAnalyze")).not_to_have_class("primary")
        expect(page.locator("#legend")).to_contain_text("Unsicher, bitte prüfen")
        expect(page.locator("#counter")).to_contain_text("Angaben ersetzt")

        # Unsichere Stelle: sichtbar, ersetzbar, und „Passt so“ blendet sie aus.
        suspect = page.locator("#masked .suspect")
        expect(suspect).to_have_text("Nordlicht")
        expect(page.locator("#notes")).to_contain_text("1 unsichere Stelle")
        suspect.click()
        expect(page.locator("#menuKeep")).to_be_visible()
        page.locator("#menuKeep").click()
        expect(suspect).to_have_count(0)
        expect(page.locator("#notes")).not_to_contain_text("unsichere Stelle")
        expect(page.locator("#legend")).not_to_contain_text("Unsicher, bitte prüfen")

        page.locator("#btnRelease").click()
        expect(page.locator("#btnCopy")).to_be_enabled()
        expect(page.locator("#releaseStatus")).to_have_text("Freigegeben")
        expect(page.locator("#releaseLabel")).to_have_text("Vorschau freigegeben")
        page.locator("#btnCopy").click()
        expect(page.locator("#copied")).to_have_text("Kopiert.")
        assert "[PERSON_1]" in page.evaluate("navigator.clipboard.readText()")
        page.locator("#btnCopy").press("Tab")
        expect(page.locator("#answerInput")).to_be_focused()
        expanded("stepAnswer")
        page.locator("#answerInput").fill("[PERSON_1] schreibt an [PERSON_2].")
        page.locator("#btnRestore").click()
        expect(page.locator("#answerStatus")).to_have_text("Zurückübersetzt")
        expect(page.locator("#answer")).to_contain_text("Erika Musterfrau")
        # Markierter Text bleibt während eines Hovers erhalten.
        page.evaluate("""() => {
            document.activeElement.blur();
            const range = document.createRange();
            range.selectNodeContents(document.querySelector('#answer'));
            const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
        }""")
        original.hover()
        expect(workspace).to_have_attribute("data-focus", "stepAnswer")
        assert "Erika Musterfrau" in page.evaluate("getSelection().toString()")
        page.evaluate("getSelection().removeAllRanges()")
        review.hover()
        expanded("stepReview")

        page.locator("#masked .chip button").first.click()
        expect(page.locator("#releaseStatus")).to_have_text("Prüfung nötig")
        expect(page.locator("#btnCopy")).to_be_disabled()
        expect(page.locator("#answerStatus")).to_have_text("Ausstehend")
        for width in [320, 390, 768, 1024, 1440]:
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width

        page.emulate_media(reduced_motion="reduce")
        assert workspace.evaluate("e => getComputedStyle(e).transitionDuration") == "0s"
        touch_context = browser.new_context(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True)
        touch = touch_context.new_page()
        touch.goto(url)
        touch.locator('#original').tap()
        expect(touch.locator('#workspace')).to_have_attribute('data-focus', 'stepOriginal')
        touch.locator('#h-masked').tap()
        expect(touch.locator('#workspace')).to_have_attribute('data-focus', 'stepReview')
        assert touch.evaluate('document.documentElement.scrollWidth <= innerWidth')
        touch_context.close()
        assert not errors, errors
        browser.close()
    print("Browserprüfung bestanden: Freigabe, Kopieren, Rückübersetzung, fünf Bildschirmbreiten, Hover, Klick, Tastatur, Textauswahl und Touch.")


if __name__ == "__main__":
    main()
