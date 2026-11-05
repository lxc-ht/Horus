"""Kommandozeile: python -m harness run DATEI (oder Text über stdin).

Ruft nur harness.api auf. Ablauf: analyze → prüfen → release → send (oder Kopier-Modus) → restore.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import warnings
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import api

HEADER = "Das geht an Claude — bitte prüfen"
SUBHEADER = "{n} Stellen ersetzt. Platzhalter sind hervorgehoben. Nichts wird gesendet, bevor du ok eingibst."
HELP = "+ BEGRIFF TYP zusätzlich maskieren · - PLATZHALTER zurücknehmen · ok freigeben · q abbrechen"
ABORTED = "Abgebrochen. Es wurde nichts gesendet."

TYPE_STYLES = {
    "PERSON": "bold black on bright_cyan",
    "FIRMA": "bold black on bright_magenta",
    "ADRESSE": "bold black on bright_yellow",
    "ORT": "bold black on yellow",
    "EMAIL": "bold black on bright_green",
    "TELEFON": "bold black on green",
    "IBAN": "bold white on red",
    "DATUM": "bold black on bright_blue",
}

console = Console()


class LineInput:
    """Liest Eingaben zeilenweise. Kam der Text über stdin, wird vom Terminal gelesen."""

    def __init__(self, use_tty: bool):
        self.stream = sys.stdin
        if use_tty:
            try:
                self.stream = open("/dev/tty", encoding="utf-8")
            except OSError:
                raise SystemExit("Kein Terminal für die Prüfschleife verfügbar. Bitte eine Datei angeben.")
        self.echo = not self.stream.isatty()

    def readline(self, prompt: str = "") -> str | None:
        if prompt:
            console.print(prompt, end="")
        line = self.stream.readline()
        if not line:
            return None
        line = line.rstrip("\n")
        if self.echo and prompt:
            console.print(line, style="dim")
        return line


def _highlight(result: api.MaskResult) -> Text:
    text = Text(result.masked_text)
    for r in result.replacements:
        text.stylize(TYPE_STYLES.get(r.typ, "bold reverse"), r.start, r.end)
    return text


def _show(result: api.MaskResult) -> None:
    console.rule(f"[bold]{HEADER}")
    console.print(SUBHEADER.format(n=len(result.replacements)))
    console.print(Panel(_highlight(result), border_style="cyan"))

    summary: OrderedDict[str, list] = OrderedDict()
    for r in sorted(result.replacements, key=lambda r: (r.typ, r.placeholder)):
        entry = summary.setdefault(r.placeholder, [r.typ, r.original, 0])
        entry[2] += 1
    if summary:
        table = Table(title="Zuordnung (bleibt lokal)", title_justify="left")
        table.add_column("Platzhalter")
        table.add_column("Typ")
        table.add_column("Original")
        table.add_column("Anzahl", justify="right")
        for placeholder, (typ, original, count) in summary.items():
            table.add_row(Text(placeholder, style=TYPE_STYLES.get(typ, "")), typ, original, str(count))
        console.print(table)

    for w in result.warnings:
        console.print(f"[yellow]⚠ {w}")
    console.print(f"[dim]{HELP}")


def _review(result: api.MaskResult, inp: LineInput) -> api.Release | None:
    """Prüfschleife. Liefert die Freigabe oder None bei Abbruch."""
    _show(result)
    while True:
        line = inp.readline("[bold]> [/]")
        if line is None:
            return None
        cmd = line.strip()
        if not cmd:
            continue
        if cmd.lower() == "q":
            return None
        if cmd.lower() == "ok":
            try:
                return api.release(result.session_id)
            except api.LeakError as e:
                console.print(f"[bold red]{e}")
                continue
        try:
            if cmd.startswith("+"):
                parts = cmd[1:].strip().rsplit(None, 1)
                if len(parts) != 2:
                    console.print(f"[red]{HELP}")
                    continue
                result = api.add_manual(result.session_id, parts[0], parts[1])
            elif cmd.startswith("-"):
                result = api.remove(result.session_id, cmd[1:].strip())
            else:
                console.print(f"[red]{HELP}")
                continue
        except ValueError as e:
            console.print(f"[red]{e}")
            continue
        _show(result)


def _copy_mode(rel: api.Release, message: str, inp: LineInput) -> str | None:
    console.print(Panel(Text(rel.text), title="Freigegebener Text", border_style="green"))
    if shutil.which("pbcopy"):
        subprocess.run(["pbcopy"], input=rel.text.encode("utf-8"), check=False)
    console.print(f"[bold yellow]{message}")
    lines: list[str] = []
    while True:
        line = inp.readline()
        if line is None:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines) if lines else None


def _report(restored: api.RestoreResult) -> None:
    console.rule("[bold]Antwort, lokal zurückübersetzt")
    console.print(Panel(Text(restored.text), border_style="green"))
    if not restored.warnings:
        console.print("[green]Alle Platzhalter eindeutig zurückübersetzt.")
    for w in restored.warnings:
        console.print(f"[yellow]⚠ {w}")


def _save(session_id: str, text: str) -> Path:
    out = Path("data") / "out"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.now():%Y%m%d-%H%M%S}-{session_id[:8]}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def run(source: str | None) -> int:
    from_stdin = source in (None, "-")
    text = sys.stdin.read() if from_stdin else Path(source).read_text(encoding="utf-8")
    if not text.strip():
        console.print("[red]Kein Text.")
        return 2
    inp = LineInput(use_tty=from_stdin)

    with console.status("Erkenne sensible Angaben …"):
        result = api.analyze(text)

    rel = _review(result, inp)
    if rel is None:
        console.print(f"[bold]{ABORTED}")
        return 1

    try:
        with console.status("Sende freigegebenen Text an Claude …"):
            answer = api.send(rel)
    except api.NoApiKeyError as e:
        answer = _copy_mode(rel, str(e), inp)
        if answer is None:
            console.print("[red]Keine Antwort eingefügt.")
            return 1
    except api.ReleaseMismatchError as e:
        console.print(f"[bold red]{e}")
        return 1
    except api.CloudError as e:
        console.print(f"[bold red]{e}")
        return 1

    restored = api.restore(result.session_id, answer)
    _report(restored)

    choice = inp.readline("Ergebnis nach data/out/ speichern? [j/N] ")
    if choice and choice.strip().lower() in ("j", "ja", "y"):
        console.print(f"Gespeichert: {_save(result.session_id, restored.text)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness", description="Lokaler Pseudonymisierungs-Harness")
    parser.add_argument("-v", "--verbose", action="store_true", help="Protokoll (nur Platzhalter, Typen, Zählungen)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run", help="Text prüfen, freigeben, senden und zurückübersetzen")
    p_run.add_argument("datei", nargs="?", help="Textdatei; ohne Angabe oder mit - wird stdin gelesen")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.ERROR, format="%(levelname)s %(name)s: %(message)s")
    if not args.verbose:
        # Hinweise der ML-Bibliotheken verdecken sonst die Prüfansicht.
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
    if args.command == "run":
        return run(args.datei)
    return 2
