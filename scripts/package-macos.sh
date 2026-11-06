#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "$#" -ne 1 ]; then
    printf 'Usage: %s /absolute/output/directory\n' "$0" >&2
    exit 2
fi
mkdir -p "$1"
output_dir="$(cd "$1" && pwd)"
archive="$output_dir/Horus-macOS-AppleSilicon.zip"
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT

uv_version=0.13.7
uv_archive=uv-aarch64-apple-darwin.tar.gz
uv_sha256=81b811b57e4624df7ed3aac148e0359100d9962f3d9dce00aec533dc2e086731
curl -fLsS --retry 3 -o "$temp/$uv_archive" "https://github.com/astral-sh/uv/releases/download/$uv_version/$uv_archive"
(cd "$temp" && printf '%s  %s\n' "$uv_sha256" "$uv_archive" | shasum -a 256 -c -)

# Nur versionierte Dateien aus dem Release-Commit übernehmen.
git archive --prefix=Horus/ HEAD -- .python-version pyproject.toml uv.lock LICENSE README.md README.en.md \
    'Horus starten.command' 'Start Horus.command' src/harness web examples benchmarks | tar -xf - -C "$temp"

mkdir "$temp/Horus/.horus"
tar -xzf "$temp/$uv_archive" -C "$temp"
cp "$temp/uv-aarch64-apple-darwin/uv" "$temp/Horus/.horus/uv"
for license in LICENSE-APACHE LICENSE-MIT; do
    curl -fLsS --retry 3 -o "$temp/Horus/.horus/uv-$license" "https://raw.githubusercontent.com/astral-sh/uv/$uv_version/$license"
done

ditto -c -k --keepParent "$temp/Horus" "$temp/Horus-macOS-AppleSilicon.zip"
mv "$temp/Horus-macOS-AppleSilicon.zip" "$archive"
printf '%s\n' "$archive"
