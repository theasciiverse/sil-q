#!/bin/sh
# Packs Sil-Q into its archive for av: dist/<id>-<target>.tar.gz (.zip for
# Windows), from the list in asciiverse/archive/<id>.txt: one file or folder
# per line, relative to the repo root, placed at the same path in the
# archive unless "src -> name" gives another; out/sil gets .exe on Windows.
# Sil-Q only reads these files: it writes to the player's data folder.
#
#   asciiverse/package.sh x86_64-unknown-linux-musl
set -eu
cd "$(dirname "$0")/.."
target="$1"
case "$target" in *windows*) exe=.exe ;; *) exe= ;; esac
mkdir -p dist
for list in asciiverse/archive/*.txt; do
  id=$(basename "$list" .txt)
  stage="stage/$id"
  rm -rf "$stage" && mkdir -p "$stage"
  grep -v '^#' "$list" | while IFS= read -r line; do
    [ -n "$line" ] || continue
    case "$line" in
      *" -> "*) src=${line%% -> *} name=${line#* -> } ;;
      *) src=$line name=$line ;;
    esac
    case "$src" in out/*) [ -f "$src$exe" ] && src="$src$exe" && name="$name$exe" ;; esac
    mkdir -p "$stage/$(dirname "$name")"
    cp -R "$src" "$stage/$name"
  done
  rm -f "dist/$id-$target.tar.gz" "dist/$id-$target.zip"
  if [ -n "$exe" ]; then
    (cd "$stage" && zip -qr "../../dist/$id-$target.zip" .)
  else
    tar -czf "dist/$id-$target.tar.gz" -C "$stage" .
  fi
done
ls dist
