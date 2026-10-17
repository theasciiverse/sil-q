#!/bin/sh
# Builds Sil-Q for the Asciiverse catalog into out/sil: only the curses
# (gcu) frontend, no X11, Cocoa or sound, through Sil-Q's own CMake build.
# One script serves every target (see .github/workflows/release.yml):
#
#   asciiverse/build.sh                     # Debian, Ubuntu, macOS: system ncurses
#   STATIC=1 asciiverse/build.sh            # Alpine: static musl, ncurses linked in
#   CMAKE_ARGS=-DBUILD_ENABLE_SANITIZERS=ON BUILD=build/asan asciiverse/build.sh
#
# CC, CFLAGS and LDFLAGS from the environment are passed on; CMAKE_ARGS adds
# options (macOS: -DCMAKE_OSX_ARCHITECTURES=x86_64 to build for Intel);
# JOBS limits the parallel compiles (default: one per processor).
set -eu
cd "$(dirname "$0")/.."
build="${BUILD:-build/asciiverse}"
set -- -DCMAKE_BUILD_TYPE="${BUILD_TYPE:-Release}" \
  -DSUPPORT_GCU_FRONTEND=ON -DSUPPORT_X11_FRONTEND=OFF -DSUPPORT_COCOA_FRONTEND=OFF
if [ -n "${STATIC:-}" ]; then
  # link the static ncursesw and everything else in
  # (CMake's FindCurses would pick the shared ones; it adds the form
  # library too, which the game does not use)
  a=$(${CC:-cc} -print-file-name=libncursesw.a)
  f=$(${CC:-cc} -print-file-name=libformw.a)
  set -- "$@" -DCURSES_NEED_NCURSES=ON \
    -DCURSES_CURSES_LIBRARY="$a" -DCURSES_NCURSES_LIBRARY="$a" -DCURSES_FORM_LIBRARY="$f" \
    -DCMAKE_EXE_LINKER_FLAGS="-static ${LDFLAGS:-}"
fi
# shellcheck disable=SC2086
cmake -S . -B "$build" "$@" ${CMAKE_ARGS:-}
cmake --build "$build" --parallel "${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}"
mkdir -p out
cp "$build/sil" out/sil
echo "built out/sil"
