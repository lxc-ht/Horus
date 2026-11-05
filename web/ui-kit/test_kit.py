"""Browserprüfung der isolierten Designstudie, siehe README.md."""
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    root = Path(__file__).resolve().parent
    url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8013'
    # Eigenständige Dateien und ZIP dürfen nicht von der eingebetteten Quelle abweichen.
    source = dict(re.findall(r'<symbol id="i-([a-z]+)" viewBox="0 0 24 24">(.*?)</symbol>', (root / 'index.html').read_text()))
    with ZipFile(root / 'icons.zip') as archive:
        assert len(archive.namelist()) == len(source) == 18
        for name, paths in source.items():
            filename = f'lp7-{name}.svg'
            svg = (root / 'icons' / filename).read_bytes()
            element = ET.fromstring(svg)
            assert element.attrib['viewBox'] == '0 0 24 24'
            assert paths in svg.decode()
            assert archive.read(filename) == svg
            assert not element.findall('.//{http://www.w3.org/2000/svg}use')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width':1440, 'height':1000}, permissions=['clipboard-read', 'clipboard-write'])
        page = context.new_page()
        errors, unexpected_requests = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: unexpected_requests.append(request.url) if not request.url.startswith(url.rstrip('/') + '/') else None)
        page.goto(url)
        expect(page.locator('body')).to_have_attribute('data-look', 'lime')
        expect(page.locator('.segmented [data-look="lime"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#dashboardDemo')).to_have_attribute('data-layout', 'banner')
        expect(page.locator('.icon-tile')).to_have_count(18)
        for name, paths in source.items():
            page.locator(f'[data-icon="{name}"]').click()
            expect(page.locator(f'[data-icon="{name}"]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('#selectedSymbol use')).to_have_attribute('href', '#i-' + name)
        page.locator('[data-icon="analyze"]').click()
        page.locator('#copySvg').click()
        expect(page.locator('#iconFeedback')).to_contain_text('als SVG kopiert')
        svg = ET.fromstring(page.evaluate('navigator.clipboard.readText()'))
        assert len(svg) > 0 and svg.attrib['viewBox'] == '0 0 24 24'
        with page.expect_download() as download_event:
            page.locator('#downloadSvg').click()
        download = download_event.value
        assert download.suggested_filename == 'lp7-analyze.svg'
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / download.suggested_filename
            download.save_as(path)
            downloaded = ET.parse(path).getroot()
            assert downloaded.attrib['viewBox'] == '0 0 24 24'
            assert len(downloaded) == len(svg)

        for look in ['glass', 'lime', 'pure']:
            page.locator(f'.segmented [data-look="{look}"]').click()
            expect(page.locator('body')).to_have_attribute('data-look', look)
            for width in [320, 390, 768, 1024, 1440]:
                page.set_viewport_size({'width':width, 'height':900})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (look, width)

        for design in ['glass', 'lime', 'pure']:
            demo = page.locator(f'.demo[data-design="{design}"]')
            next_button = demo.locator('.demo-next')
            output = demo.locator('.demo-output')
            expect(output).to_be_disabled()
            next_button.click()
            expect(demo).to_have_attribute('data-stage', 'preview')
            expect(demo.locator('.demo-text')).to_contain_text('[PERSON_1]')
            expect(output).to_be_disabled()
            next_button.click()
            expect(demo.locator('.demo-status')).to_have_text('Freigegeben')
            expect(output).to_be_enabled()
            expect(next_button).to_be_disabled()
            output.click()
            expect(demo).to_have_attribute('data-stage', 'output')
            expect(demo.locator('.demo-text')).to_contain_text('Erika Musterfrau')
            expect(output).to_be_disabled()
            next_button.click()
            expect(demo).to_have_attribute('data-stage', 'original')
            expect(output).to_be_disabled()
            next_button.click()
            next_button.click()
            demo.locator('.demo-reset').click()
            expect(demo).to_have_attribute('data-stage', 'original')
            expect(output).to_be_disabled()

        dashboard = page.locator('#dashboardDemo')
        for layout in ['flow', 'banner']:
            page.locator(f'.dashboard-controls [data-layout="{layout}"]').click()
            expect(dashboard).to_have_attribute('data-layout', layout)
            page.locator('#dashReset').click()
            expect(page.locator('#dashRelease')).to_be_disabled()
            expect(page.locator('#dashOutput')).to_be_disabled()
            # Auch ein synthetischer Klick darf die Freigabesperre nicht umgehen.
            page.locator('#dashOutput').evaluate('button => button.dispatchEvent(new MouseEvent("click"))')
            expect(dashboard).to_have_attribute('data-stage', 'original')
            page.locator('#dashAnalyze').click()
            expect(page.locator('#dashPreview [data-person]')).to_have_count(2)
            expect(page.locator('#dashRelease')).to_be_enabled()
            expect(page.locator('#dashOutput')).to_be_disabled()
            page.locator('#dashRelease').click()
            expect(page.locator('#dashOutput')).to_be_enabled()
            other = 'banner' if layout == 'flow' else 'flow'
            page.locator(f'.dashboard-controls [data-layout="{other}"]').click()
            expect(page.locator('#dashOutput')).to_be_enabled()
            page.locator(f'.dashboard-controls [data-layout="{layout}"]').click()
            page.locator('#dashOutput').click()
            expect(page.locator('#dashAnswerStatus')).to_have_text('Fertig')
            expect(page.locator('#dashAnswer')).to_contain_text('Erika Musterfrau')
            page.locator('#dashPreview [data-person="1"]').click()
            expect(page.locator('#dashStatus')).to_have_text('Prüfung nötig')
            expect(page.locator('#dashOutput')).to_be_disabled()
            expect(page.locator('#dashAnswerStatus')).to_have_text('Ausstehend')
            expect(page.locator('#dashAnswer')).not_to_contain_text('Erika Musterfrau')
            expect(page.locator('#dashPreview')).to_contain_text('Erika Musterfrau')
            expect(page.locator('#dashPreview [data-person]')).to_have_count(1)
            page.locator('#dashRelease').click()
            page.locator('#dashAnalyze').click()
            expect(page.locator('#dashOutput')).to_be_disabled()
            expect(page.locator('#dashPreview [data-person]')).to_have_count(2)
            for width in [320, 390, 768, 1024, 1440]:
                page.set_viewport_size({'width':width, 'height':900})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (layout, width)
            page.locator('#dashReset').click()
            expect(dashboard).to_have_attribute('data-stage', 'original')
            expect(page.locator('#dashOutput')).to_be_disabled()
        assert not errors, errors
        assert not unexpected_requests, unexpected_requests
        browser.close()
    print('UI Kit geprüft: 18 SVG, Export, drei Looks, Ablaufdemos, zwei Dashboard Layouts, Freigabeverlust nach Änderungen und fünf Bildschirmbreiten.')


if __name__ == '__main__':
    main()
