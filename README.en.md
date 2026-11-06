# Horus

**Team Horus** · Leuphana AI Hackathon 2026

[Deutsch](README.md) · [**Download Horus for macOS**](https://github.com/lxc-ht/Horus/releases/download/v0.1.0-preview.1/Horus-macOS-AppleSilicon.zip)

Horus pseudonymizes text on your computer. It replaces detected names, contact details, identifiers and other sensitive values with placeholders such as `[PERSON_1]`. You can review the result before sharing it and restore the original values in the reply on your computer.

## Quick start for Apple silicon Macs

1. [**Download Horus**](https://github.com/lxc-ht/Horus/releases/download/v0.1.0-preview.1/Horus-macOS-AppleSilicon.zip).
2. Extract the ZIP and double-click `Start Horus.command`. Use `Horus starten.command` to start in German.
3. Horus opens in your browser. Keep the Terminal window open while using Horus. Press Ctrl+C or close the window to stop it.

The ZIP includes `uv`. Horus automatically downloads Python, its packages and the detection model on first use. Have an internet connection and several gigabytes of free space. macOS may ask you to approve this preview the first time you open it. [Apple's guide to opening downloaded apps](https://support.apple.com/en-us/102445)

## Use Horus

1. Paste text, load the fictional example, or import a digital PDF, Word document or email.
2. Analyze the text. Review the highlighted findings and manually replace any sensitive details Horus missed.
3. Approve the preview, copy it, and paste it into the AI service you use.
4. Paste the reply into Horus to restore the values on your computer.

The interface and launch instructions are available in English. Placeholder labels and some detection and error messages still use German. The interface uses the local address `127.0.0.1`. You decide what to share with the AI service.

## Detection limits

Detection can miss sensitive values. A passage can also identify someone through context. Review the complete preview before sharing it. In a small sample of 12 fictional documents, Horus fully replaced 32 of 36 annotated values and produced five false positives. [Sample and method](benchmarks/README.md)

## Run from source

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run from the repository folder:

```bash
uv run --locked --extra web uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/?lang=en`. To build the macOS preview ZIP from a committed revision, run `./scripts/package-macos.sh dist` on macOS.

Horus is available under the [MIT license](LICENSE). For attribution, see the [German README](README.md#danksagung).
