"""Dark dashboard theme, icon art and small custom widgets for the Truck Config Manager UI."""
from __future__ import annotations

import ctypes
import tkinter as tk
from tkinter import ttk

# ---------- palette ----------
BG = "#121417"
SURFACE = "#1a1d22"
RAISED = "#22262d"
FIELD = "#2a2f37"
HOVER = "#2f343d"
BORDER = "#2e333b"
TEXT = "#e8eaed"
MUTED = "#8a919c"
FAINT = "#5b616b"
ACCENT = "#f2a93b"
ACCENT_HOVER = "#ffbe5c"
ACCENT_DIM = "#3a2c16"
ON_ACCENT = "#1a1406"
DANGER = "#ef5a5a"
SELECT = "#3b2f1b"
STRIPE = "#1e2126"
GAME_COLOR = {"ets2": "#4c9aff", "ats": "#ef5a5a"}

# ---------- fonts ----------
UI = ("Segoe UI", 10)
BOLD = ("Segoe UI Semibold", 10)
SMALL = ("Segoe UI", 9)
SMALL_BOLD = ("Segoe UI Semibold", 9)
H1 = ("Bahnschrift SemiBold", 22)
H2 = ("Bahnschrift SemiBold", 14)
BRAND = ("Bahnschrift SemiBold", 15)
BADGE = ("Bahnschrift SemiBold", 9)
CAPS = ("Bahnschrift SemiBold", 8)
MONO = ("Cascadia Mono", 9)

# Segoe Fluent Icons (Win11) / MDL2 Assets (Win10) share these code points
ICON_FONT = ("Segoe Fluent Icons", 11)
I_COMPARE = ""
I_HISTORY = ""
I_CAMERA = ""
I_FOLDER = ""
I_FORWARD = ""
I_BACK = ""
I_SYNC = ""
I_SEARCH = ""
I_WARNING = ""
I_CLOSE = ""
I_CHECK = ""
I_SORT = "\ue8cb"
I_HELP = "\ue897"
I_LINK = "\ue71b"
I_PLAY = "\ue768"
I_ADD = "\ue710"
I_DELETE = "\ue74d"
I_GLOBE = "\ue774"
I_PUZZLE = "\uea86"
I_REPAIR = "\ue90f"
I_REFRESH = "\ue72c"


def setup(root: tk.Tk) -> None:
    global ICON_FONT
    from tkinter import font as tkfont
    fams = set(tkfont.families(root))
    ICON_FONT = ("Segoe Fluent Icons" if "Segoe Fluent Icons" in fams else "Segoe MDL2 Assets", 11)

    root.configure(bg=BG)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.font", UI)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=TEXT, font=UI, bordercolor=BORDER, lightcolor=BORDER,
                darkcolor=BORDER, troughcolor=SURFACE, fieldbackground=FIELD, focuscolor=ACCENT,
                selectbackground=SELECT, selectforeground=TEXT, insertcolor=TEXT)

    # tables
    s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    s.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                rowheight=32, borderwidth=0, font=UI)
    s.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
    s.configure("Treeview.Heading", background=RAISED, foreground=MUTED, font=SMALL_BOLD,
                relief="flat", borderwidth=0, padding=(10, 8))
    s.map("Treeview.Heading", background=[("active", HOVER)], foreground=[("active", TEXT)])
    s.configure("Treeview.Item", padding=(6, 0))

    # scrollbars: thin, no arrows
    for orient in ("Vertical", "Horizontal"):
        s.layout(f"{orient}.TScrollbar", [(f"{orient}.Scrollbar.trough", {"sticky": "nswe", "children": [
            (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        s.configure(f"{orient}.TScrollbar", troughcolor=SURFACE, background=HOVER, bordercolor=SURFACE,
                    lightcolor=HOVER, darkcolor=HOVER, gripcount=0, arrowsize=10, width=10)
        s.map(f"{orient}.TScrollbar", background=[("active", FAINT), ("pressed", MUTED)],
              lightcolor=[("active", FAINT)], darkcolor=[("active", FAINT)])

    # inputs
    s.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=TEXT, arrowcolor=MUTED,
                bordercolor=FIELD, lightcolor=FIELD, darkcolor=FIELD, padding=(8, 5), arrowsize=14)
    s.map("TCombobox", fieldbackground=[("readonly", FIELD)], background=[("active", HOVER)],
          foreground=[("readonly", TEXT)], selectbackground=[("readonly", FIELD)],
          selectforeground=[("readonly", TEXT)], bordercolor=[("focus", ACCENT)],
          lightcolor=[("focus", ACCENT)], darkcolor=[("focus", ACCENT)], arrowcolor=[("active", TEXT)])
    s.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, bordercolor=FIELD, lightcolor=FIELD,
                darkcolor=FIELD, padding=(6, 5))
    s.configure("Search.TEntry", fieldbackground=FIELD, bordercolor=FIELD, lightcolor=FIELD, darkcolor=FIELD,
                padding=(2, 6))
    s.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])

    img = logo_image(root, 64, None)
    root.iconphoto(True, img)
    root._tcm_icon = img  # keep a reference


def dark_titlebar(win: tk.Misc) -> None:
    """Windows 10/11: dark caption + caption colour matching the app background."""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        on = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), 4)
        r, g, b = (int(BG[i:i + 2], 16) for i in (1, 3, 5))
        colour = ctypes.c_int(b << 16 | g << 8 | r)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colour), 4)
    except Exception:
        pass


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


# ---------- logo (steering wheel on an amber tile, supersampled so it stays smooth) ----------

def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def logo_image(master, size: int, bg: str | None) -> tk.PhotoImage:
    """bg=None leaves the corners transparent (window icon)."""
    tile, dark = _rgb(ACCENT), _rgb(ON_ACCENT)
    back = _rgb(bg) if bg else (0x20, 0x20, 0x20)
    ss = 4
    radius, ring_r, ring_w, hub_r, spoke = 0.22, 0.31, 0.085, 0.085, 0.04

    def sample(x, y):  # x, y in 0..1 -> 0 outside, 1 tile, 2 wheel
        dx, dy = max(radius - x, 0, x - (1 - radius)), max(radius - y, 0, y - (1 - radius))
        if dx * dx + dy * dy > radius * radius:
            return 0
        cx, cy = x - 0.5, y - 0.5
        d = (cx * cx + cy * cy) ** 0.5
        if abs(d - ring_r) < ring_w / 2 or d < hub_r:
            return 2
        if d < ring_r and (abs(cy) < spoke or (abs(cx) < spoke and cy > 0)):
            return 2
        return 1

    img = tk.PhotoImage(master=master, width=size, height=size)
    rows, clear = [], []
    for py in range(size):
        row = []
        for px in range(size):
            acc, inside = [0, 0, 0], 0
            for sy in range(ss):
                for sx in range(ss):
                    k = sample((px + (sx + 0.5) / ss) / size, (py + (sy + 0.5) / ss) / size)
                    c = back if k == 0 else tile if k == 1 else dark
                    inside += k != 0
                    for i in range(3):
                        acc[i] += c[i]
            n = ss * ss
            row.append("#%02x%02x%02x" % tuple(v // n for v in acc))
            if bg is None and inside == 0:
                clear.append((px, py))
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    for px, py in clear:
        img.transparency_set(px, py, True)
    return img


# ---------- widgets ----------

class Button(tk.Frame):
    KINDS = {  # bg, hover bg, fg
        "primary": (ACCENT, ACCENT_HOVER, ON_ACCENT),
        "secondary": (RAISED, HOVER, TEXT),
        "ghost": (None, RAISED, MUTED),
    }

    def __init__(self, master, text, command, kind="secondary", icon=None, padx=14, pady=7):
        bg, hover, fg = self.KINDS[kind]
        self._bg, self._hover, self._fg = bg or master["bg"], hover, fg
        if self._bg == hover:  # ghost button sitting on a raised card
            self._hover = HOVER
        super().__init__(master, bg=self._bg, cursor="hand2")
        self.command, self.enabled = command, True
        self.parts = []
        if icon:
            self.parts.append(tk.Label(self, text=icon, font=ICON_FONT, bg=self._bg, fg=fg))
            self.parts[-1].pack(side="left", padx=(padx, 0), pady=pady)
        self.parts.append(tk.Label(self, text=text, font=BOLD, bg=self._bg, fg=fg))
        self.parts[-1].pack(side="left", padx=(8 if icon else padx, padx), pady=pady)
        for w in (self, *self.parts):
            w.bind("<Enter>", lambda e: self._paint(self._hover))
            w.bind("<Leave>", lambda e: self._paint(self._bg))
            w.bind("<ButtonRelease-1>", self._click)

    def _paint(self, bg):
        if not self.enabled:
            bg = self._bg
        for w in (self, *self.parts):
            w.configure(bg=bg)

    def _click(self, _e):
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, on: bool):
        self.enabled = on
        self.configure(cursor="hand2" if on else "arrow")
        for w in self.parts:
            w.configure(fg=self._fg if on else FAINT, cursor="hand2" if on else "arrow")
        self._paint(self._bg)


class Chip(tk.Label):
    """Toggle chip bound to a BooleanVar."""

    def __init__(self, master, text, var: tk.BooleanVar, command=None):
        super().__init__(master, font=SMALL_BOLD, padx=12, pady=6, cursor="hand2")
        self.var, self.command, self.text = var, command, text
        self.bind("<ButtonRelease-1>", self._toggle)
        self.bind("<Enter>", lambda e: self._paint(True))
        self.bind("<Leave>", lambda e: self._paint(False))
        self._paint(False)

    def _toggle(self, _e):
        self.var.set(not self.var.get())
        self._paint(True)
        if self.command:
            self.command()

    def _paint(self, hover):
        on = self.var.get()
        self.configure(text=("✓  " if on else "") + self.text,
                       bg=ACCENT_DIM if on else (HOVER if hover else RAISED), fg=ACCENT if on else MUTED)


class Segmented(tk.Frame):
    """Segmented selector: options = [(value, text, dot_colour)]."""

    def __init__(self, master, options, var: tk.StringVar, command=None):
        super().__init__(master, bg=RAISED, padx=3, pady=3)
        self.var, self.command, self.items = var, command, {}
        for value, text, dot in options:
            f = tk.Frame(self, bg=RAISED, cursor="hand2")
            f.pack(side="left")
            d = tk.Label(f, text="●", font=SMALL, fg=dot, bg=RAISED)
            d.pack(side="left", padx=(12, 0), pady=4)
            t = tk.Label(f, text=text, font=SMALL_BOLD, bg=RAISED)
            t.pack(side="left", padx=(6, 14), pady=4)
            for w in (f, d, t):
                w.bind("<ButtonRelease-1>", lambda e, v=value: self._pick(v))
            self.items[value] = (f, d, t)
        self._paint()

    def _pick(self, value):
        self.var.set(value)
        self._paint()
        if self.command:
            self.command()

    def _paint(self):
        for value, (f, d, t) in self.items.items():
            on = value == self.var.get()
            bg = HOVER if on else RAISED
            for w in (f, d, t):
                w.configure(bg=bg)
            t.configure(fg=TEXT if on else MUTED)


class NavItem(tk.Frame):
    def __init__(self, master, icon, text, command):
        super().__init__(master, bg=SURFACE, cursor="hand2")
        self.active = False
        self.bar = tk.Frame(self, bg=SURFACE, width=3)
        self.bar.pack(side="left", fill="y")
        self.icon = tk.Label(self, text=icon, font=(ICON_FONT[0], 13), bg=SURFACE, fg=MUTED)
        self.icon.pack(side="left", padx=(16, 12), pady=10)
        self.text = tk.Label(self, text=text, font=BOLD, bg=SURFACE, fg=MUTED)
        self.text.pack(side="left")
        self.badge = tk.Label(self, font=BADGE, bg=ACCENT_DIM, fg=ACCENT, padx=7)
        for w in (self, self.icon, self.text, self.badge):
            w.bind("<ButtonRelease-1>", lambda e: command())
            w.bind("<Enter>", lambda e: self._paint(True))
            w.bind("<Leave>", lambda e: self._paint(False))

    def set_badge(self, text):
        if text:
            self.badge.configure(text=text)
            self.badge.pack(side="right", padx=16)
        else:
            self.badge.pack_forget()

    def set_active(self, on):
        self.active = on
        self._paint(False)

    def _paint(self, hover):
        bg = RAISED if (self.active or hover) else SURFACE
        for w in (self, self.icon, self.text):
            w.configure(bg=bg)
        self.bar.configure(bg=ACCENT if self.active else bg)
        self.icon.configure(fg=ACCENT if self.active else (TEXT if hover else MUTED))
        self.text.configure(fg=TEXT if (self.active or hover) else MUTED)


class SearchBox(tk.Frame):
    def __init__(self, master, var: tk.StringVar, placeholder="Filter actions or inputs", width=30):
        super().__init__(master, bg=FIELD, highlightthickness=1, highlightbackground=FIELD,
                         highlightcolor=ACCENT)
        tk.Label(self, text=I_SEARCH, font=(ICON_FONT[0], 10), bg=FIELD, fg=MUTED).pack(side="left", padx=(10, 2))
        self.entry = ttk.Entry(self, textvariable=var, width=width, style="Search.TEntry", font=UI)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.hint = tk.Label(self, text=placeholder, font=UI, bg=FIELD, fg=FAINT)
        self.hint.bind("<Button-1>", lambda e: self.entry.focus_set())
        self.var = var
        var.trace_add("write", lambda *a: self._hint())
        self.entry.bind("<FocusIn>", lambda e: self.configure(highlightbackground=ACCENT))
        self.entry.bind("<FocusOut>", lambda e: self.configure(highlightbackground=FIELD))
        self.entry.bind("<Escape>", lambda e: var.set(""))
        self._hint()

    def _hint(self):
        if self.var.get():
            self.hint.place_forget()
        else:
            self.hint.place(in_=self.entry, x=6, rely=0.5, anchor="w")


def section(master, text, bg=SURFACE):
    tk.Label(master, text=text, font=CAPS, fg=FAINT, bg=bg).pack(anchor="w", padx=24, pady=(22, 8))


# ---------- dialogs ----------

class Dialog(tk.Toplevel):
    def __init__(self, master, title, message, buttons, entry=False, tone=ACCENT, detail=None):
        super().__init__(master, bg=SURFACE)
        self.withdraw()
        self.title(title)
        self.transient(master)
        self.resizable(False, False)
        self.result, self.entry = None, entry
        tk.Frame(self, bg=tone, height=3).pack(fill="x")
        body = tk.Frame(self, bg=SURFACE, padx=26, pady=22)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=title, font=H2, bg=SURFACE, fg=TEXT).pack(anchor="w")
        tk.Label(body, text=message, font=UI, bg=SURFACE, fg=MUTED, wraplength=460,
                 justify="left").pack(anchor="w", pady=(8, 0))
        if detail:
            tk.Label(body, text=detail, font=MONO, bg=RAISED, fg=TEXT, wraplength=440, justify="left",
                     padx=12, pady=10, anchor="w").pack(fill="x", pady=(14, 0))
        if entry:
            self.var = tk.StringVar()
            e = ttk.Entry(body, textvariable=self.var, width=46, font=UI)
            e.pack(fill="x", pady=(14, 0))
            self.after(50, e.focus_set)
        bar = tk.Frame(self, bg=BG, padx=18, pady=14)
        bar.pack(fill="x")
        for text, value, kind in reversed(buttons):
            Button(bar, text, lambda v=value: self.close(v), kind).pack(side="right", padx=(8, 0))
        self.bind("<Return>", lambda e: self.close(buttons[0][1]))
        self.bind("<Escape>", lambda e: self.close(None))
        self.protocol("WM_DELETE_WINDOW", lambda: self.close(None))

        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_reqwidth()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        dark_titlebar(self)
        self.grab_set()
        self.wait_window()

    def close(self, value):
        if self.entry and value is True:
            value = self.var.get()
        self.result = value
        self.destroy()


def confirm(master, title, message, ok="Continue", detail=None, tone=ACCENT) -> bool:
    return Dialog(master, title, message, ((ok, True, "primary"), ("Cancel", False, "secondary")),
                  detail=detail, tone=tone).result is True


def info(master, title, message):
    Dialog(master, title, message, (("OK", True, "primary"),))


def error(master, title, message):
    Dialog(master, title, message, (("OK", True, "primary"),), tone=DANGER)


def ask_string(master, title, message, ok="Save"):
    return Dialog(master, title, message, ((ok, True, "primary"), ("Cancel", None, "secondary")),
                  entry=True).result
