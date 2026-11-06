#!/bin/bash

# Der Finder startet das Skript möglicherweise außerhalb des Repo-Ordners.
cd "$(dirname "$0")" || exit 1

port="${LP7_PORT:-8000}"
case "$port" in
    ''|*[!0-9]*)
        printf 'LP7_PORT muss eine Portnummer zwischen 1 und 65535 sein.\n'
        exit 1
        ;;
esac
if [ "${#port}" -gt 5 ] || [ "$((10#$port))" -lt 1 ] || [ "$((10#$port))" -gt 65535 ]; then
    printf 'LP7_PORT muss eine Portnummer zwischen 1 und 65535 sein.\n'
    exit 1
fi
port="$((10#$port))"
url="http://127.0.0.1:$port"

# Bei einem Doppelklick fehlen diese üblichen Installationsorte oft im PATH.
export PATH="$PATH:$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
if ! command -v uv >/dev/null 2>&1; then
    cat <<'TEXT'
LP7 braucht das Werkzeug uv, das ist auf diesem Mac nicht installiert.
Installieren mit: curl -LsSf https://astral.sh/uv/install.sh | sh
Danach LP7 erneut per Doppelklick starten.
Enter drücken zum Schließen.
TEXT
    read -r
    exit 1
fi

lp7_ready() {
    # Keine Proxys verwenden: Auch die Statusabfrage bleibt auf diesem Rechner.
    curl --noproxy '*' -fsS --connect-timeout 1 --max-time 1 "$url/api/status" 2>/dev/null |
        plutil -extract fake xml1 -o - - >/dev/null 2>&1
}

open_browser() {
    if [ "${LP7_NO_BROWSER:-0}" != 1 ]; then
        open "$url"
    fi
}

if lp7_ready; then
    printf 'LP7 läuft schon. Der Browser öffnet sich.\n'
    open_browser
    exit 0
fi

if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    printf 'Port %s ist von einem anderen Programm belegt.\n' "$port"
    cat <<'TEXT'
Starte LP7 mit einem anderen Port, zum Beispiel im Terminal: LP7_PORT=8010 "./LP7 starten.command"
Enter drücken zum Schließen.
TEXT
    read -r
    exit 1
fi

cat <<'TEXT'
LP7 startet. Alles läuft nur auf diesem Rechner.
Beim ersten Start lädt LP7 Pakete und das Erkennungsmodell, zusammen rund 2,7 GB. Das dauert mit schnellem Netz etwa 2 Minuten.
Der Browser öffnet sich von selbst. Dieses Fenster bitte offen lassen.
Zum Beenden: ctrl+C drücken oder das Fenster schließen.
TEXT

# exec behält die PID. Die Warteschleife endet auch, wenn der Server vorher endet.
server_pid=$$
(
    deadline=$((SECONDS + 90))
    while [ "$SECONDS" -lt "$deadline" ]; do
        kill -0 "$server_pid" 2>/dev/null || exit 0
        if lp7_ready; then
            open_browser
            exit 0
        fi
        sleep 1
    done
    if kill -0 "$server_pid" 2>/dev/null; then
        printf 'LP7 antwortet noch nicht. Öffne in ein paar Sekunden selbst: %s\n' "$url"
    fi
) &

# Der Server bleibt im Vordergrund und erhält die Signale des Terminals direkt.
exec uv run --locked --extra web uvicorn web.app:app --host 127.0.0.1 --port "$port"
