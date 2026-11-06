![Horus wordmark with the Eye of Horus on mint glass](docs/images/horus-header.jpg)

# Horus · Use AI. Keep your data.

**Horus replaces sensitive details with placeholders on your computer.** For example, “Erika Musterfrau” becomes `[PERSON_1]`. You review the masked text before sharing it with a chatbot. Horus restores the original values in the reply on your computer.

[Deutsch](README.md) · [Quick start](#quick-start) · [How it works](#how-it-works) · [Limits](#limits)

## Quick start

1. [Download the Horus preview for Apple silicon Macs](https://github.com/lxc-ht/Horus/releases/download/v0.1.0-preview.1/Horus-macOS-AppleSilicon.zip) and extract the ZIP.
2. Double-click `Start Horus.command`. Horus opens in your browser in English. The first launch requires internet access and several gigabytes of free space for Python packages and the detection model.
3. Load the built-in example and analyze it. The sample uses fictional details.

<details>
<summary>Run from the repository</summary>

Install uv, then clone the repository or download the ZIP from GitHub and extract it. Run these commands from the repository folder.

```bash
uv sync
uv run --locked --extra web uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser and select **EN**. Installation was tested on macOS. See the [German setup notes](README.md#schnellstart) for Gatekeeper and download instructions.

</details>

## How it works

![Erika Musterfrau in the original becomes \[PERSON_1\] in the approved preview and returns as Erika Musterfrau in the local reply](docs/images/horus-workflow-en.jpg)

1. **Enter and analyze.** Paste text or load a digital PDF, Word document or email. Horus replaces detected names, addresses, bank details and other sensitive information with placeholders.
2. **Review and approve.** Check the preview and mark anything Horus missed. Yellow highlights flag uncertain matches. Approve the preview to enable copying.
3. **Copy and restore.** Paste the approved text into a chatbot of your choice. Paste its reply into Horus to restore the original values on your computer.

You decide what to copy to the chatbot. The browser interface keeps the mapping between placeholders and original values on your computer.

<details>
<summary>See the interface with a fictional law firm example (German)</summary>

![Horus showing a fictional original, an approved preview and a locally restored reply](web/assets/horus-ablauf.png)

</details>

## Limits

Pseudonymization can leave identifying clues in the surrounding text, and detection can miss sensitive information. Review the full preview before approving it. Whether a workflow complies with privacy rules depends on how you use it.

## Testing and development

In a sample of 12 fictional documents, Horus fully replaced 32 of 36 annotated values and produced five false positives. See the [sample and method](benchmarks/README.md) and the [German README](README.md#tests-und-entwicklung) for installation measurements, development commands and architecture.

## Credits and license

Built by Team Horus at the Leuphana AI Hackathon 2026. [Acknowledgments](README.md#danksagung) · [MIT license](LICENSE)
