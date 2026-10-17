"""Recorder for Sil-Q's catalog preview (hub/RECORDING.md), from the NetBSD
games' (theasciiverse/netbsd-games, asciiverse/record/rec.py).

The driver beside this file, asciiverse/record/sil-q.py, plays the game:
it starts a Rec, which runs the game under `asciinema rec` in a 100x30
pseudo-terminal, reads the screen through pyte and sends keys. The cast
goes to asciiverse/casts/<id>.cast. Usage, from the repo root after
asciiverse/build.sh (which puts the binary in out/) and
asciiverse/package.sh (which lays the archive out in stage/sil-q), with
pyte installed:

    python3 asciiverse/record/sil-q.py

The game runs by name from out/ on PATH, so the cast's header holds no
local path, in the folder av would start it in (cwd=, the staged archive,
whose lib/ it reads); its files go to a throwaway home folder under the
name "player".
"""
import fcntl, os, pty, select, shutil, struct, sys, tempfile, termios, time

import pyte

# ncurses draws a run of one character with REP (CSI n b, "repeat the last
# character n times"), which pyte does not know: a box border would read as
# "lq" then "k", and runs of reversed spaces would vanish. Teach it here.
_draw = pyte.Screen.draw


def _draw_remembering(self, data):
    if data:
        self.last_char = data[-1]
    _draw(self, data)


def _repeat_last(self, n=1, *rest, **kw):
    if getattr(self, "last_char", None):
        _draw(self, self.last_char * max(1, n))


pyte.Screen.draw = _draw_remembering
pyte.Screen.repeat_last = _repeat_last
pyte.Stream.csi = dict(pyte.Stream.csi, b="repeat_last")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# curses turns on keypad mode, so the cursor keys arrive in application form
UP, DOWN, RIGHT, LEFT = b"\x1bOA", b"\x1bOB", b"\x1bOC", b"\x1bOD"
ENTER, ESC = b"\r", b"\x1b"


class Rec:
    def __init__(self, id, title, args=(), cols=100, rows=30, cwd=None, exe=None):
        self.home = tempfile.mkdtemp(prefix="sil-q-rec-")
        out = os.path.join(ROOT, "out")
        env = {
            "PATH": f"{out}:{os.environ['PATH']}",
            "HOME": self.home,
            "USER": "player",
            "LOGNAME": "player",
            "XDG_DATA_HOME": os.path.join(self.home, "data"),
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "LANG": "C.UTF-8",
        }
        cmd = " ".join([exe or id, *args])
        cast = os.path.join(ROOT, "asciiverse", "casts", f"{id}.cast")
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.ByteStream(self.screen)
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(cwd or self.home)
            os.execvpe("asciinema", ["asciinema", "rec", "--overwrite", "-q", "--idle-time-limit", "2",
                "--window-size", f"{cols}x{rows}", "--capture-env", "TERM,COLORTERM,LANG",
                "--title", title, "--command", cmd, cast], env)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        self.start = time.time()
        self.cast = cast

    def pump(self, t):
        """Read the game's output for t seconds, keeping the screen current."""
        end = time.time() + t
        while True:
            left = end - time.time()
            r, _, _ = select.select([self.fd], [], [], max(0.0, min(0.02, left)))
            if r:
                try:
                    self.stream.feed(os.read(self.fd, 65536))
                except OSError:
                    return False
            if left <= 0:
                return True

    def key(self, k, wait=0.15):
        if isinstance(k, str):
            k = k.encode()
        os.write(self.fd, k)
        self.pump(wait)

    def rows(self):
        return self.screen.display

    def text(self):
        return "\n".join(self.screen.display)

    def wait_for(self, s, timeout=5.0):
        end = time.time() + timeout
        while time.time() < end:
            if s in self.text():
                return True
            self.pump(0.05)
        return False

    def elapsed(self):
        return time.time() - self.start

    def finish(self, quit_keys=b"q", grace=3.0):
        """Quit the game so the cast ends with the terminal restored."""
        if quit_keys:
            self.key(quit_keys, 0.5)
        end = time.time() + grace
        while time.time() < end:
            if not self.pump(0.1):
                break
            done, _ = os.waitpid(self.pid, os.WNOHANG)
            if done:
                break
        else:
            print("game did not exit; stopping the recording", file=sys.stderr)
            os.kill(self.pid, 15)
            for _ in range(20):
                if not self.pump(0.1) or os.waitpid(self.pid, os.WNOHANG)[0]:
                    break
            else:
                os.kill(self.pid, 9)
        try:
            os.waitpid(self.pid, 0)
        except ChildProcessError:
            pass
        shutil.rmtree(self.home, ignore_errors=True)
        print(f"{self.cast}: {os.path.getsize(self.cast) // 1024} KB, {self.elapsed():.0f} s", file=sys.stderr)
