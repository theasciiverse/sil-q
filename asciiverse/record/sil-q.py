"""Sil-Q preview: a new character goes down into Angband, explores and
fights what turns up.

The driver makes a character (a dwarf of Nogrod named Morwen, with
experience spent on melee and evasion), then plays from the screen: it
attacks anything next to it, rests when its health is below 70% and
nothing is in sight, picks up what it walks onto, and otherwise walks to
the nearest item, else the nearest dark cell beside known floor
(corridors stay dark until you stand next to them), by breadth-first
search over the map; with nothing left, it goes after the nearest
creature it can reach or takes the stairs down, as it also does after a
while on a level. After about 48 seconds it saves and quits (Ctrl-X),
passes the score list and leaves from the menu. A take where the
character dies is recorded again (it leaves through the death menu); of
the others the one with the most fighting and the deepest descent is
kept.

    python3 asciiverse/record/sil-q.py
"""
import collections, os, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rec

# the menus read the cursor keys as the terminal sends them by default
RIGHT, DOWN = b"\x1b[C", b"\x1b[B"

ROOT = rec.ROOT
STAGE = os.path.join(ROOT, "stage", "sil-q")
CAST = os.path.join(ROOT, "asciiverse", "casts", "sil-q.cast")
COL_MAP, ROW_MAP = 13, 1      # the map starts right of the sidebar, below the message line
DIRS = {(-1, -1): "7", (-1, 0): "8", (-1, 1): "9", (0, -1): "4",
        (0, 1): "6", (1, -1): "1", (1, 0): "2", (1, 1): "3"}
ITEMS = set(",|(!~=\"-?_[{}/\\$*)]")
FLOOR = set(".'^<>") | ITEMS
BLOCK = set("#%:")            # walls, mineral veins, rubble
MONSTER = re.compile(r"[A-Za-z&]")


class Player:
    def __init__(self, r):
        self.r = r
        self.seen = collections.Counter()
        self.tried = collections.Counter()
        self.picked = set()
        self.level_steps = 0
        self.last = None
        self.fights = 0
        self.descents = 0

    def grid(self):
        d = self.r.rows()
        return {(y, x): d[y][x] for y in range(ROW_MAP, len(d) - 2) for x in range(COL_MAP, len(d[y]))}

    def me(self, g):
        ats = [k for k, v in g.items() if v == "@"]
        if not ats:
            return None
        if self.last and len(ats) > 1:   # men and elves in the dungeon are @ too
            ats.sort(key=lambda k: max(abs(k[0] - self.last[0]), abs(k[1] - self.last[1])))
        self.last = ats[0]
        return ats[0]

    def health(self):
        m = re.search(r"Health\s+(\d+):(\d+)", self.r.text())
        return (int(m.group(1)), int(m.group(2))) if m else (1, 1)

    def prompts(self):
        for _ in range(10):
            t, top = self.r.text(), self.r.rows()[0]
            if "a) Return to game" in t:
                self.r.key("a", 0.2)
            elif "-more-" in t:
                self.r.key(" ", 0.25)
            elif "[y/n]" in top or "(y/n)" in top:
                self.r.key("n", 0.15)
            elif "Direction" in top:
                self.r.key("\x1b", 0.15)
            else:
                return

    def route(self, g, me, want_down):
        """The key for the next step: toward the stairs down when wanted,
        else the nearest item, else the nearest unknown cell beside floor.
        A 1-tuple means: this step reaches the stairs."""
        q = collections.deque([me])
        prev = {me: None}
        found = into = None
        while q and found is None:
            cur = q.popleft()
            c = g.get(cur, " ")
            if cur != me and want_down and c == ">":
                found = cur
                break
            if cur != me and not want_down and c in ITEMS and cur not in self.picked:
                found = cur
                break
            if not want_down:
                for dy, dx in DIRS:
                    n = (cur[0] + dy, cur[1] + dx)
                    if g.get(n) == " " and n not in self.seen and self.tried[n] < 2:
                        found, into = cur, n
                        break
                if found is not None:
                    break
            for dy, dx in DIRS:
                n = (cur[0] + dy, cur[1] + dx)
                cn = g.get(n)
                if n in prev or cn is None:
                    continue
                if (cn == " " and n in self.seen) or (cn in FLOOR or cn == "+"):
                    prev[n] = cur
                    q.append(n)
        if found is None:
            return None
        if found == me:
            self.tried[into] += 1
            return DIRS[(into[0] - me[0], into[1] - me[1])]
        goal = found
        while prev[found] != me:
            found = prev[found]
        key = DIRS[(found[0] - me[0], found[1] - me[1])]
        return (key,) if want_down and found == goal else key

    def toward_foe(self, g, me):
        """The first step toward the nearest creature that can be reached,
        when nothing else is left to do (one may stand in the corridor)."""
        q = collections.deque([me])
        prev = {me: None}
        while q:
            cur = q.popleft()
            for dy, dx in DIRS:
                n = (cur[0] + dy, cur[1] + dx)
                cn = g.get(n)
                if n in prev or cn is None:
                    continue
                if MONSTER.match(cn) or cn == "@":
                    while cur != me and prev[cur] != me:
                        cur = prev[cur]
                    step = n if cur == me else cur
                    return DIRS[(step[0] - me[0], step[1] - me[1])]
                if (cn == " " and n in self.seen) or cn in FLOOR or cn == "+":
                    prev[n] = cur
                    q.append(n)
        return None

    def step(self, elapsed):
        self.prompts()
        g = self.grid()
        me = self.me(g)
        if me is None:
            self.r.key(" ", 0.2)
            return
        y, x = me
        self.seen[me] += 1
        for (dy, dx), key in DIRS.items():
            c = g.get((y + dy, x + dx), " ")
            if MONSTER.match(c) or (c == "@" and (y + dy, x + dx) != me):
                self.fights += 1
                self.r.key(key, 0.22)
                return
        hp, hp_max = self.health()
        near = any((MONSTER.match(v) or v == "@") and k != me and abs(k[0] - y) < 8 and abs(k[1] - x) < 12
                   for k, v in g.items())
        if hp * 10 < hp_max * 7 and not near:
            self.r.key("Z", 0.8)
            return
        if "You see" in self.r.rows()[0] and me not in self.picked:
            self.picked.add(me)
            self.r.key("g", 0.25)
            return
        want_down = self.level_steps > 140 or (elapsed > 36 and self.descents == 0)
        key = self.route(g, me, want_down)
        if key is None and not want_down:
            key = self.route(g, me, True)
        if key is None:
            key = self.toward_foe(g, me)
        if key is None:
            self.r.key("5", 0.15)
            return
        if isinstance(key, tuple):
            self.r.key(key[0], 0.2)
            self.r.key(">", 0.9)
            self.descents += 1
            self.level_steps = 0
            self.seen.clear(); self.tried.clear(); self.picked.clear(); self.last = None
            return
        self.level_steps += 1
        self.r.key(key, 0.13)


def take(n):
    """One recording; returns its score, or None when the character died."""
    r = rec.Rec("sil-q", "Sil-Q", cwd=STAGE, exe="sil")
    r.wait_for("b) New character", 8)
    r.pump(1.5)
    r.key("b", 0.8)
    r.wait_for("Character Creation", 5)
    for key in (DOWN, DOWN):           # Naugrim, the dwarves
        r.key(key, 0.4)
    for want in ("House of", "allocate points to stats", "allocate points to skills"):
        r.key("\r", 0.1)
        r.wait_for(want, 5)
        r.pump(0.7)
    for key in [RIGHT] * 6 + [DOWN] * 2 + [RIGHT] * 5:    # melee 6, evasion 5
        r.key(key, 0.12)
    r.pump(0.6)
    for want in ("accept history", "accept age", "accept name"):
        r.key("\r", 0.1)
        r.wait_for(want, 5)
        r.pump(0.7)
    r.key("Morwen", 0.6)
    r.key("\r", 0.3)
    r.wait_for("Into the vast", 5)
    r.pump(2.0)
    r.key(" ", 0.3)
    r.wait_for("min 50 ft", 8)
    r.pump(1.0)
    p = Player(r)
    while r.elapsed() < 48:
        p.step(r.elapsed())
        if "You die" in r.text() or "You have been slain" in r.text():
            for _ in range(8):                  # leave through the death menu
                if "h) Exit" in r.text():
                    break
                r.key(" ", 0.6)
            r.key("h", 1.0)
            for _ in range(6):
                if "d) Quit" in r.text():
                    break
                r.key(" ", 0.6)
            r.finish(b"d")
            return None
    p.prompts()
    r.pump(1.0)
    r.key("\x18", 1.2)                  # save and quit
    for _ in range(6):
        if "d) Quit" in r.text():
            break
        r.key(" ", 1.0)
    r.pump(0.8)
    r.finish(b"d")
    return p.fights + 10 * p.descents


best = None
for attempt in range(8):
    score = take(attempt)
    if score is None:
        print("the character died; recording again", file=sys.stderr)
        continue
    print(f"take {attempt}: {score}", file=sys.stderr)
    if best is None or score > best[0]:
        best = (score, attempt)
        shutil.copy(CAST, CAST + ".best")
    if score >= 15:
        break
if best:
    os.replace(CAST + ".best", CAST)
