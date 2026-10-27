# Changes from upstream

This is the Asciiverse packaging of Sil-Q, the maintained continuation of
Sil. Sil is by half and Scatha (the names Sil-Q's build gives as its
copyright holders, `SIL_COPYRIGHT` in `CMakeLists.txt`, and its manual's
"half and Scatha's vision"): Sil 1.0 came out in 2012 and 1.3, the last,
in 2016 (http://www.amirrorclear.net/flowers/game/sil/). Quirk started
Sil-Q from the Sil 1.3 code in 2017 (the first commit, "Initial commit of
Sil 1.3 code") and led it to 1.5.0 in 2022, with Eric Branlund among the
contributors and MicroChasm's tiles and manual; since January 2026
Michael G. Noll (miguno) has carried it on at
https://github.com/sil-quirk/sil-q, with 1.5.1-beta1 in May 2026.

## The import

The branch `main` starts from Sil-Q's own history, unchanged, at upstream
`master` commit `07fdf7751c8418f25b064e226e21716ce56534f2` (2026-10-16,
tree `037781d55054773c0c62aac08393f52272d22e4f`), which reports itself as
1.5.1.0-beta2. GitHub's source tarball of that commit,
`sil-q-07fdf7751c8418f25b064e226e21716ce56534f2.tar.gz`, has sha256
`cbcf3779434205d02cfb7d95ef7d2ff16c6aa0a872626fd60799532590dbd601` and
the same files as the commit. Sil-Q is the `upstream` remote, with its
tags (`v1.5.0`, `v1.5.1-beta1` and older). Everything after `07fdf77` is
ours.

Why not the latest stable tag, v1.5.0: it is from 2022-01-03 and has no
CMake build, and the 248 commits since fix every bug reported against it
(by the changelog), among them a buffer overflow when running in place,
an overflow when firing with no valid path, out-of-bounds reads when
searching disarmed chests and in `get_move_wander()`, a signed overflow
in `update_mon()` and memory leaks, and make the code build cleanly as
C99 with `-Wall -Wextra`. The changelog lists no gameplay changes since
1.5.0, so saves and play are 1.5.0's. Master is v1.5.1-beta1
(2026-05-12) plus 22 commits; the ones that touch the terminal build are
#226 (no window updates before a character exists, a crash) and a
`flush()` after `Term_flush()` between games.

## Licence

`LICENSE.md` says:

> Sil is free software; you can redistribute it and/or modify it under the
> terms of either the GNU General Public License as published by the Free
> Software Foundation, version 2, or the "Angband licence", shown below, with
> some exceptions:
>
> - The sounds are freeware, whatever that means.
>
> - The font files are under the licences noted in
>   [lib/xtra/font/copying.txt](lib/xtra/font/copying.txt),
>   all of which are OSI-compliant.

GPL version 2 is named without "or any later version", so the catalog
licence is `GPL-2.0-only` (the "or later" wording inside `LICENSE.md` is
only the GPL's own how-to-apply appendix). The Angband licence allows
only "not for profit" copying, so the Asciiverse distributes Sil-Q under
the GPL. The source files themselves carry only the old Angband notice
(Ben Harrison, James E. Wilson, Robert A. Koeneke); `LICENSE.md`
(`lib/docs/copying.txt` is the same text) is what grants the GPL, as for
Angband after its relicensing.

Left out of the archive:

- the sounds, `lib/xtra/sound/*.wav`: "freeware, whatever that means" is
  no licence one can rely on, and the curses build plays no sound. They
  stay in the repository as part of Sil-Q's history, but are never
  shipped;
- the fonts and tiles (`lib/xtra/font`, `lib/xtra/graf`), which only the
  X11, Windows and Cocoa builds use;
- `src/readdib.c` (Microsoft copyright, Windows only) is not compiled.

## Our changes

### Packaging

- `asciiverse/build.sh` builds only the curses (gcu) frontend through
  Sil-Q's CMake build (`SUPPORT_GCU_FRONTEND=ON`, X11 and Cocoa off) into
  `out/sil`: against the system ncurses on Debian, Ubuntu and macOS, or
  with `STATIC=1` statically against musl in Alpine, with FindCurses
  pointed at `libncursesw.a` (it would pick the shared library).
- `asciiverse/package.sh` packs `dist/sil-q-<target>.tar.gz` from
  `asciiverse/archive/sil-q.txt`: `sil`, `lib/edit`, `lib/pref` and
  `lib/xtra/tutorial` beside it, `LICENSE.md`, `asciiverse/NOTICE`
  (as `NOTICE`) and the Sil-Q 1.5.0 manual (`Sil-Q v1.5.0.pdf`, as
  `Sil-Q-manual.pdf`).
- `.github/workflows/release.yml` replaces Sil-Q's release workflow:
  static musl Linux (x86_64, aarch64) and macOS (x86_64, arm64) archives
  and `SHA256SUMS` on a pushed tag. Sil-Q's per-platform workflows
  (`linux.yml`, `mac.yml`, `windows.yml`, `src.yml`) are removed: they
  build the Windows, Cocoa and X11 editions the Asciiverse does not ship.
  No Windows build: the curses frontend needs a POSIX terminal.
- `.gitignore`: `out/`, `stage/`, `dist/`, `__pycache__/`.

### Files in the player's data folder

- With `USE_XDG_DATA_PATH`, which `CMakeLists.txt` sets for the Linux and
  non-Cocoa macOS builds, saved characters, high scores, pref files and
  character dumps, and the `.raw` files compiled from `lib/edit`, are
  kept in `$XDG_DATA_HOME/sil-q` (else `~/.local/share/sil-q`), in
  `save`, `scores`, `user` and `data`, made as needed
  (`xdg_user_paths()` in `src/init2.c`). They used to be folders inside
  `lib/`, so the game had to sit somewhere writable and was shared by
  everyone on the machine. Nothing is setgid.
- `lib/` is only read. Sil-Q looks for it in the folder it is started in,
  as before (av starts titles in their install folder), and else beside
  its own binary, found through `argv[0]` and the `PATH` with links
  resolved (`find_lib_dir()` in `src/main.c`).

### Terminal

- `src/main-gcu.c`: the main window fills the terminal. Upstream split a
  terminal bigger than 80x24 into the main window and up to three side
  windows, kept the map at 80x24 until the terminal was wider than 161
  columns or taller than 51 rows, and at 100x30 showed the
  equipment cut off in a 19 column strip. The old `-b` sub-option is
  still accepted; `sil -mgcu -- -w` gives the split layout.
- A terminal that changes size is followed (`gcu_resize()`): SIGWINCH,
  handled by the game instead of curses and without `SA_RESTART` so it
  ends the wait for a key, resizes curses and the main term, and the game
  redraws for the new size with the map kept on the player. In a menu,
  the menu is drawn again at once and the whole screen once it closes.
  Smaller than 80x24 is ignored until the terminal grows again; the split
  layout is only redrawn. Resuming after Ctrl-Z checks the size too.

### Fixes

- New characters are saved under their own name (`play_game()` in
  `src/dungeon.c`). The savefile was named at startup after the login
  name, so a character called Ada was saved as `1000.David`; "Open saved
  character", which asks for the character's name, could not find it,
  and the next new character under the login name overwrote it. Windows
  and Cocoa, which choose savefiles their own way, are unchanged.
- Saving no longer crashes when `CharOutput.txt` cannot be written
  (`updatecharinfoS()` in `src/save.c` used an unchecked `fopen()`).
  Checked on the unchanged upstream build with a read-only `lib/user`:
  Ctrl-S ended in "A gruesome software bug LEAPS out at you!" and a
  segmentation fault.
- No "Savefile ... does not exist" message, with the savefile's full
  path, when starting a new character (`load_player()` now takes the
  `new_game` flag); opening a saved character by a name that has no
  savefile still says so.
- The default character name comes from `LOGNAME`, then `USER`, before
  the password database (`user_name()` in `src/util.c`), as in the other
  Asciiverse titles; the previews run as "player".

### Preview

- `asciiverse/record/sil-q.py` plays the 100x30 preview in
  `asciiverse/casts/sil-q.cast` through `asciiverse/record/rec.py` (from
  the NetBSD games' recorder, reading the screen through pyte; when the
  game does not exit, it now follows SIGTERM with SIGKILL instead of
  waiting for ever).
- `asciiverse/build.sh` takes `JOBS` to limit parallel compiles.

## Checked, not changed

- Leaving the tutorial with Ctrl-X shows "You cannot save games-more-g
  the tutorial.": the `-more-` prompt is drawn over the message. The
  unchanged upstream build does the same; cosmetic, left alone.

## Ours

- **How to play it, at the top of README.md.** A short note on installing and
  starting it with av, or from a release archive; the original text follows
  unchanged.
