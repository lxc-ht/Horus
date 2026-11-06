#!/bin/bash

# Der Finder startet das Skript möglicherweise außerhalb des Repo-Ordners.
cd "$(dirname "$0")" || exit 1

language=de
if [ "${1:-}" = en ]; then language=en; fi

say() {
    if [ "$language" = en ]; then
        printf '%s\n' "$2"
    else
        printf '%s\n' "$1"
    fi
}

port="${HORUS_PORT:-8000}"
case "$port" in
    ''|*[!0-9]*)
        say 'HORUS_PORT muss zwischen 1 und 65535 liegen.' 'HORUS_PORT must be between 1 and 65535.'
        exit 1
        ;;
esac
if [ "${#port}" -gt 5 ] || [ "$((10#$port))" -lt 1 ] || [ "$((10#$port))" -gt 65535 ]; then
    say 'HORUS_PORT muss zwischen 1 und 65535 liegen.' 'HORUS_PORT must be between 1 and 65535.'
    exit 1
fi
port="$((10#$port))"
url="http://127.0.0.1:$port"

# Bei einem Doppelklick fehlen diese üblichen Installationsorte oft im PATH.
export PATH="$PATH:$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
uv_command=uv
if [ -x .horus/uv ]; then
    uv_command=./.horus/uv
    export UV_MANAGED_PYTHON=1
elif ! command -v uv >/dev/null 2>&1; then
    say 'uv fehlt. Lade das Horus ZIP mit eingebautem Starter herunter oder installiere uv.' \
        'uv is missing. Download the Horus ZIP with the included launcher or install uv.'
    say 'Enter drücken zum Schließen.' 'Press Enter to close.'
    read -r
    exit 1
fi

horus_ready() {
    # Keine Proxys verwenden: Auch die Statusabfrage bleibt auf diesem Rechner.
    curl --noproxy '*' -fsS --connect-timeout 1 --max-time 1 "$url/api/status" 2>/dev/null |
        plutil -extract fake xml1 -o - - >/dev/null 2>&1
}

open_browser() {
    if [ "${HORUS_NO_BROWSER:-0}" != 1 ]; then
        open "$url/?lang=$language"
    fi
}

if horus_ready; then
    say 'Horus läuft schon. Der Browser öffnet sich.' 'Horus is already running. Opening the browser.'
    open_browser
    exit 0
fi

if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    say "Port $port ist belegt. Setze HORUS_PORT auf einen freien Port." \
        "Port $port is in use. Set HORUS_PORT to an available port."
    say 'Enter drücken zum Schließen.' 'Press Enter to close.'
    read -r
    exit 1
fi

say 'Horus startet auf diesem Rechner.' 'Horus is starting on this computer.'
say 'Beim ersten Start lädt Horus Python und Pakete. Bei Bedarf lädt die App auch das Modell.' \
    'On first launch, Horus downloads Python and its packages. The app also downloads the model when needed.'
say 'Der Browser öffnet sich von selbst. Zum Beenden ctrl+C drücken oder dieses Fenster schließen.' \
    'The browser opens automatically. To stop Horus, press Ctrl+C or close this window.'

# exec behält die PID. Die Warteschleife endet auch, wenn der Server vorher endet.
server_pid=$$
(
    deadline=$((SECONDS + 90))
    while [ "$SECONDS" -lt "$deadline" ]; do
        kill -0 "$server_pid" 2>/dev/null || exit 0
        if horus_ready; then
            open_browser
            exit 0
        fi
        sleep 1
    done
    if kill -0 "$server_pid" 2>/dev/null; then
        say "Horus antwortet noch nicht. Öffne den Browser nach dem Start selbst: $url/?lang=$language" \
            "Horus is still starting. Open this address once it is ready: $url/?lang=$language"
    fi
) &

# Der Server bleibt im Vordergrund und erhält die Signale des Terminals direkt.
exec "$uv_command" run --locked --no-dev --extra web uvicorn web.app:app --host 127.0.0.1 --port "$port"
