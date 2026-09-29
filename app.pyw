"""Truck Config Manager - snapshot, restore and sync ETS2/ATS controller bindings."""
import os
import threading
import webbrowser
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk

from truckcfg import cleanup, core, loadorder, mods, steamugc, theme as T

MISSING = "—  not in this game"


def fmt(kind, v, raw):
    return MISSING if v is None else v if raw else core.pretty_input(kind, v)


def when(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%b %d, %Y  ·  %H:%M")
    except ValueError:
        return iso


def bordered(master, bg=T.SURFACE):
    return tk.Frame(master, bg=bg, highlightthickness=1, highlightbackground=T.BORDER)


class DiffTable(tk.Frame):
    def __init__(self, master, left_title, right_title, on_select=None):
        super().__init__(master, bg=T.SURFACE, highlightthickness=1, highlightbackground=T.BORDER)
        cols = ("action", "kind", "left", "right")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="extended")
        for c, title, w, stretch in (("action", "ACTION", 200, False), ("kind", "TYPE", 90, False),
                                     ("left", left_title, 360, True), ("right", right_title, 360, True)):
            self.tree.heading(c, text=title, anchor="w")
            self.tree.column(c, width=w, minwidth=60, stretch=stretch, anchor="w")
        self.tree.tag_configure("odd", background=T.STRIPE)
        self.tree.tag_configure("missing", foreground=T.FAINT)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.empty = tk.Label(self, bg=T.SURFACE, fg=T.MUTED, font=T.UI, justify="center")
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda e: on_select())
        self.rows = {}

    def set_titles(self, left, right):
        self.tree.heading("left", text=left)
        self.tree.heading("right", text=right)

    def load(self, rows, show_unmapped=True, query="", empty="Nothing to show.", raw=False):
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        q = query.strip().lower()
        for r in rows:
            if not show_unmapped and not r.mapped:
                continue
            left, right = fmt(r.kind, r.left, raw), fmt(r.kind, r.right, raw)
            if q and not any(q in (s or "").lower() for s in (r.name, r.left, r.right, left, right)):
                continue
            tags = ["odd"] if len(self.rows) % 2 else []
            if r.left is None or r.right is None:
                tags.append("missing")
            kind = "input" if r.kind == "mix" else r.kind
            iid = self.tree.insert("", "end", values=(r.name, kind, left, right), tags=tags)
            self.rows[iid] = r
        if self.rows:
            self.empty.place_forget()
        else:
            self.empty.configure(text=empty)
            self.empty.place(relx=0.5, rely=0.5, anchor="center")

    def selected(self):
        return [self.rows[i] for i in self.tree.selection()]

    def all(self):
        return list(self.rows.values())


class App(tk.Tk):
    def __init__(self):
        T.enable_dpi_awareness()
        super().__init__()
        T.setup(self)
        self.title("Truck Config Manager")
        self.geometry("1400x900")
        self.minsize(1120, 760)
        self.profiles = {k: core.find_profiles(g) for k, g in core.GAMES.items()}
        self.profile_var = {k: tk.StringVar() for k in core.GAMES}
        self.show_unmapped = tk.BooleanVar(value=False)
        self.show_raw = tk.BooleanVar(value=False)
        self.query = tk.StringVar()
        self.query.trace_add("write", lambda *a: self.render_compare())
        self.cmp_rows = []
        self._run_result, self._run_thread = None, None
        self.mod_list, self._mods_gen, self._mods_results, self.mods_loaded = [], 0, {}, False
        self.mod_query = tk.StringVar()
        self.mod_query.trace_add("write", lambda *a: self.render_mods())
        self.mod_active_only = tk.BooleanVar(value=False)
        self.mod_sort = ("order", False)  # (column, descending)
        self.mod_order, self.mod_order_saved, self.mod_sii, self.order_err = [], [], None, None
        self.clutter = []

        # status bar
        foot = tk.Frame(self, bg=T.SURFACE)
        foot.pack(side="bottom", fill="x")
        tk.Frame(self, bg=T.BORDER, height=1).pack(side="bottom", fill="x")
        self.status = tk.Label(foot, bg=T.SURFACE, fg=T.MUTED, font=T.SMALL, anchor="w", padx=16, pady=6)
        self.status.pack(side="left", fill="x", expand=True)
        store = tk.Label(foot, text=f"Snapshots stored in {core.STORE}", bg=T.SURFACE, fg=T.FAINT,
                         font=T.SMALL, padx=16, cursor="hand2")
        store.pack(side="right")
        store.bind("<ButtonRelease-1>", lambda e: self.open_store())

        self._build_sidebar().pack(side="left", fill="y")
        tk.Frame(self, bg=T.BORDER, width=1).pack(side="left", fill="y")
        main = tk.Frame(self, bg=T.BG)
        main.pack(side="left", fill="both", expand=True)
        self.banner = self._build_banner(main)
        self.pages_host = tk.Frame(main, bg=T.BG)
        self.pages_host.pack(fill="both", expand=True)
        self.pages = {"compare": self._build_compare(self.pages_host),
                      "snapshots": self._build_snapshots(self.pages_host),
                      "mods": self._build_mods(self.pages_host),
                      "cleanup": self._build_cleanup(self.pages_host)}
        self.show_page("compare")

        T.dark_titlebar(self)
        self.startup_check()
        self.refresh_all()
        self.refresh_cleanup()
        self.poll_running()

    # ----- helpers -----
    def profile(self, key):
        label = self.profile_var[key].get()
        return next((p for p in self.profiles[key] if p.label == label), None)

    def say(self, msg):
        self.status.config(text=msg)

    def guard(self, fn):
        try:
            fn()
        except Exception as e:  # surface file/game errors instead of dying silently
            T.error(self, "Something went wrong", str(e))

    def refresh_all(self):
        self.refresh_compare()
        self.refresh_snapshots()
        self.refresh_cards()

    def show_page(self, key):
        for k, page in self.pages.items():
            page.pack_forget()
            self.nav[k].set_active(k == key)
        self.pages[key].pack(fill="both", expand=True)
        if key == "mods" and not self.mods_loaded:
            self.refresh_mods()

    def page_header(self, parent, title, subtitle):
        head = tk.Frame(parent, bg=T.BG)
        head.pack(fill="x")
        tk.Label(head, text=title, font=T.H1, bg=T.BG, fg=T.TEXT).pack(anchor="w")
        sub = tk.Label(head, text=subtitle, font=T.UI, bg=T.BG, fg=T.MUTED, justify="left", anchor="w")
        sub.pack(anchor="w", pady=(2, 0), fill="x")
        return sub

    # ----- sidebar -----
    def _build_sidebar(self):
        s = tk.Frame(self, bg=T.SURFACE, width=300)
        s.pack_propagate(False)

        brand = tk.Frame(s, bg=T.SURFACE, padx=22, pady=22)
        brand.pack(fill="x")
        self._logo = T.logo_image(self, 44, T.SURFACE)
        tk.Label(brand, image=self._logo, bg=T.SURFACE).pack(side="left")
        words = tk.Frame(brand, bg=T.SURFACE)
        words.pack(side="left", padx=(14, 0))
        tk.Label(words, text="TRUCK CONFIG", font=T.BRAND, bg=T.SURFACE, fg=T.TEXT).pack(anchor="w")
        tk.Label(words, text="MANAGER  ·  ETS2 / ATS", font=T.CAPS, bg=T.SURFACE, fg=T.ACCENT).pack(anchor="w")
        tk.Frame(s, bg=T.BORDER, height=1).pack(fill="x")

        T.section(s, "WORKSPACE")
        self.nav = {}
        for key, icon, text in (("compare", T.I_COMPARE, "Compare games"),
                                ("snapshots", T.I_HISTORY, "Snapshots"),
                                ("mods", T.I_PUZZLE, "Mods"),
                                ("cleanup", T.I_REPAIR, "Cleanup")):
            self.nav[key] = T.NavItem(s, icon, text, lambda k=key: self.show_page(k))
            self.nav[key].pack(fill="x")

        T.section(s, "GAMES")
        self.cards = {k: self._game_card(s, k) for k in core.GAMES}
        return s

    def _game_card(self, parent, key):
        g, color = core.GAMES[key], T.GAME_COLOR[key]
        card = tk.Frame(parent, bg=T.RAISED)
        card.pack(fill="x", padx=16, pady=(0, 12))
        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")
        body = tk.Frame(card, bg=T.RAISED, padx=14, pady=12)
        body.pack(side="left", fill="both", expand=True)

        top = tk.Frame(body, bg=T.RAISED)
        top.pack(fill="x")
        tk.Label(top, text=key.upper(), bg=color, fg="#0d0f12", font=T.BADGE, padx=7, pady=1).pack(side="left")
        run = tk.Label(top, bg=T.RAISED, font=T.SMALL_BOLD)
        run.pack(side="right")
        tk.Label(body, text=g.title, bg=T.RAISED, fg=T.TEXT, font=T.BOLD).pack(anchor="w", pady=(8, 6))

        profiles = self.profiles[key]
        cb = ttk.Combobox(body, state="readonly", textvariable=self.profile_var[key], font=T.UI,
                          values=[p.label for p in profiles])
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", lambda e: (cb.selection_clear(), self.refresh_all()))
        if profiles:
            cb.current(0)
        else:
            cb.set("No profiles found")
        stats = tk.Label(body, bg=T.RAISED, fg=T.MUTED, font=T.SMALL, justify="left", anchor="w")
        stats.pack(fill="x", pady=(10, 0))
        row = tk.Frame(body, bg=T.RAISED)
        row.pack(fill="x", pady=(8, 0))
        T.Button(row, "Launch", lambda: os.startfile(f"steam://rungameid/{mods.STEAM_APP[key]}"),
                 kind="ghost", icon=T.I_PLAY, padx=8, pady=4).pack(side="left")
        T.Button(row, "Profile folder", lambda: self.open_profile(key), kind="ghost", icon=T.I_FOLDER,
                 padx=8, pady=4).pack(side="left", padx=(4, 0))
        return {"run": run, "stats": stats}

    def open_profile(self, key):
        p = self.profile(key)
        os.startfile(p.path if p else mods.game_dir(core.GAMES[key]))

    def refresh_cards(self):
        for k, card in self.cards.items():
            p = self.profile(k)
            if not p:
                card["stats"].config(text="Launch the game once to create a profile.")
                continue
            b = core.parse_bindings(core.read_text(p.path / "controls.sii"))
            mapped = sum(1 for (kind, _), v in b.items() if kind != "constant" and core.is_mapped(kind, v))
            snaps = core.list_snapshots(p)
            last = when(snaps[0].created) if snaps else "never"
            card["stats"].config(text=f"{mapped} mapped inputs   ·   {len(snaps)} snapshots\nLast snapshot  {last}")
        self.render_running()

    def poll_running(self):
        """Check every few seconds whether the games are open (tasklist runs off the UI thread)."""
        res, self._run_result = self._run_result, None
        if res is not None:
            self.running = res
            self.render_running()
        if not (self._run_thread and self._run_thread.is_alive()):
            def work():
                self._run_result = {k: core.is_running(g) for k, g in core.GAMES.items()}
            self._run_thread = threading.Thread(target=work, daemon=True)
            self._run_thread.start()
        self.after(2500, self.poll_running)

    def render_running(self):
        running = getattr(self, "running", {})
        for k, card in self.cards.items():
            on = running.get(k, False)
            card["run"].config(text="●  RUNNING" if on else "●  CLOSED", fg=T.ACCENT if on else T.FAINT)

    # ----- warning banner -----
    def _build_banner(self, parent):
        b = tk.Frame(parent, bg=T.ACCENT_DIM)
        tk.Frame(b, bg=T.ACCENT, width=4).pack(side="left", fill="y")
        tk.Label(b, text=T.I_WARNING, font=(T.ICON_FONT[0], 14), bg=T.ACCENT_DIM, fg=T.ACCENT).pack(
            side="left", padx=(14, 10), pady=12)
        self.banner_text = tk.Label(b, bg=T.ACCENT_DIM, fg=T.TEXT, font=T.UI, justify="left", anchor="w")
        self.banner_text.pack(side="left", fill="x", expand=True)
        close = tk.Label(b, text=T.I_CLOSE, font=(T.ICON_FONT[0], 10), bg=T.ACCENT_DIM, fg=T.MUTED, cursor="hand2")
        close.pack(side="right", padx=14)
        close.bind("<ButtonRelease-1>", lambda e: b.pack_forget())
        T.Button(b, "Review snapshots", lambda: self.show_page("snapshots"), kind="ghost").pack(side="right")
        return b

    # ----- compare page -----
    def _build_compare(self, parent):
        f = tk.Frame(parent, bg=T.BG, padx=32, pady=26)
        self.cmp_summary = self.page_header(
            f, "Compare games", "Every binding and setting that differs between your ETS2 and ATS profiles.")

        bar = tk.Frame(f, bg=T.BG)
        bar.pack(fill="x", pady=(20, 12))
        T.SearchBox(bar, self.query).pack(side="left")
        T.Chip(bar, "Show unmapped actions", self.show_unmapped,
               command=lambda: (self.render_compare(), self.show_snapshot_diff())).pack(side="left", padx=10)
        T.Chip(bar, "Raw values", self.show_raw,
               command=lambda: (self.render_compare(), self.show_snapshot_diff())).pack(side="left")
        self.cmp_counts = tk.Label(bar, bg=T.BG, fg=T.MUTED, font=T.SMALL)
        self.cmp_counts.pack(side="right")

        actions = tk.Frame(f, bg=T.BG)
        actions.pack(side="bottom", fill="x", pady=(12, 0))
        self.sel_label = tk.Label(actions, bg=T.BG, fg=T.MUTED, font=T.SMALL)
        self.sel_label.pack(side="left")
        T.Button(actions, "Sync all  ETS2 → ATS", lambda: self.copy("ets2", "ats", True), kind="primary",
                 icon=T.I_SYNC).pack(side="right")
        self.btn_to_ets2 = T.Button(actions, "Copy selected to ETS2", lambda: self.copy("ats", "ets2"),
                                    icon=T.I_BACK)
        self.btn_to_ets2.pack(side="right", padx=8)
        self.btn_to_ats = T.Button(actions, "Copy selected to ATS", lambda: self.copy("ets2", "ats"),
                                   icon=T.I_FORWARD)
        self.btn_to_ats.pack(side="right")

        self.cmp = DiffTable(f, "ETS2  ·  EURO TRUCK SIMULATOR 2", "ATS  ·  AMERICAN TRUCK SIMULATOR",
                             on_select=self.update_selection)
        self.cmp.pack(fill="both", expand=True)
        self.update_selection()
        return f

    def update_selection(self):
        n = len([r for r in self.cmp.selected() if r.left is not None and r.right is not None])
        self.sel_label.config(text=f"{n} shared binding(s) selected" if n else
                              "Select rows (Ctrl / Shift-click) to copy them one way or the other.")
        self.btn_to_ats.set_enabled(bool(n))
        self.btn_to_ets2.set_enabled(bool(n))

    def refresh_compare(self):
        e, a = self.profile("ets2"), self.profile("ats")
        self.cmp_rows = [] if not (e and a) else core.diff_bindings(
            core.parse_bindings(core.read_text(e.path / "controls.sii")),
            core.parse_bindings(core.read_text(a.path / "controls.sii")))
        self.render_compare()

    def render_compare(self):
        rows = self.cmp_rows
        self.cmp.load(rows, self.show_unmapped.get(), self.query.get(),
                      empty=("ETS2 and ATS bindings match.  Nothing to sync." if not self.query.get()
                             else "No differences match that filter."), raw=self.show_raw.get())
        mapped = [r for r in rows if r.mapped]
        shared = sum(1 for r in mapped if r.left is not None and r.right is not None)
        hidden = "" if self.show_unmapped.get() else f"   ·   {len(rows) - len(mapped)} unmapped hidden"
        self.cmp_counts.config(text=f"{shared} differ   ·   {len(mapped) - shared} in one game only{hidden}")
        self.update_selection()
        self.say(f"{shared} mapped binding(s) differ between ETS2 and ATS; "
                 f"{len(mapped) - shared} mapped action(s) exist in only one game.")

    def copy(self, src_key, dst_key, everything=False):
        src, dst = self.profile(src_key), self.profile(dst_key)
        rows = self.cmp.all() if everything else self.cmp.selected()
        rows = [r for r in rows if r.left is not None and r.right is not None]
        if not rows:
            T.info(self, "Nothing to copy", "Select one or more rows that exist in both games.")
            return
        names = ", ".join(r.name for r in rows[:14]) + (" …" if len(rows) > 14 else "")
        if not T.confirm(self, f"Copy {len(rows)} binding(s) to {dst_key.upper()}?",
                         f"These bindings from {src.game.title} will overwrite the ones in {dst.game.title}. "
                         f"A snapshot of {dst_key.upper()} is taken first, so you can undo it from Snapshots.",
                         ok=f"Copy to {dst_key.upper()}", detail=names):
            return

        def run():
            n, missing = core.copy_bindings(src, dst, [(r.kind, r.name) for r in rows])
            self.refresh_all()
            self.say(f"Copied {n} binding(s) {src_key.upper()} → {dst_key.upper()}."
                     + (f" Skipped (not in target): {missing}" if missing else ""))
        self.guard(run)

    # ----- snapshots page -----
    def _build_snapshots(self, parent):
        f = tk.Frame(parent, bg=T.BG, padx=32, pady=26)
        self.page_header(f, "Snapshots", "Point-in-time copies of controls.sii and gearbox layouts. "
                                         "Restore one if a game update or sync conflict scrambles your bindings.")
        bar = tk.Frame(f, bg=T.BG)
        bar.pack(fill="x", pady=(20, 12))
        self.snap_game = tk.StringVar(value="ats")
        T.Segmented(bar, [(k, k.upper(), T.GAME_COLOR[k]) for k in core.GAMES], self.snap_game,
                    command=self.refresh_snapshots).pack(side="left")
        T.Button(bar, "Open folder", self.open_folder, kind="ghost", icon=T.I_FOLDER).pack(side="right")
        self.btn_restore = T.Button(bar, "Restore to game", self.restore, icon=T.I_HISTORY)
        self.btn_restore.pack(side="right", padx=8)
        T.Button(bar, "Take snapshot", self.snapshot, kind="primary", icon=T.I_CAMERA).pack(side="right")

        pw = tk.PanedWindow(f, orient="vertical", bg=T.BG, sashwidth=14, bd=0, sashrelief="flat",
                            opaqueresize=True)
        pw.pack(fill="both", expand=True)

        lf = bordered(pw)
        self.snaps = ttk.Treeview(lf, columns=("created", "label", "files"), show="headings", selectmode="browse")
        for c, t, w, stretch in (("created", "TAKEN", 220, False), ("label", "LABEL", 300, False),
                                 ("files", "FILES", 400, True)):
            self.snaps.heading(c, text=t, anchor="w")
            self.snaps.column(c, width=w, stretch=stretch, anchor="w")
        self.snaps.tag_configure("odd", background=T.STRIPE)
        self.snaps.tag_configure("auto", foreground=T.MUTED)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.snaps.yview)
        self.snaps.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.snaps.pack(fill="both", expand=True)
        self.snaps.bind("<<TreeviewSelect>>", lambda e: self.show_snapshot_diff())
        pw.add(lf, minsize=140, height=260)

        df = tk.Frame(pw, bg=T.BG)
        self.snap_info = tk.Label(df, bg=T.BG, fg=T.MUTED, font=T.UI, anchor="w", justify="left")
        self.snap_info.pack(fill="x", pady=(0, 10))
        self.snap_diff = DiffTable(df, "SNAPSHOT", "CURRENT")
        self.snap_diff.pack(fill="both", expand=True)
        pw.add(df, minsize=180)
        self.snap_list = []
        return f

    def refresh_snapshots(self):
        p = self.profile(self.snap_game.get())
        self.snaps.delete(*self.snaps.get_children())
        self.snap_list = core.list_snapshots(p) if p else []
        for i, s in enumerate(self.snap_list):
            tags = ["odd"] if i % 2 else []
            if s.label.startswith(("auto-", "after-")):
                tags.append("auto")
            self.snaps.insert("", "end", iid=str(i), tags=tags,
                              values=(when(s.created), s.label or "—", ", ".join(s.meta.get("files", []))))
        self.snap_diff.load([], empty="Select a snapshot above to see what changed since it was taken.")
        self.snap_info.config(text=f"{len(self.snap_list)} snapshot(s) for "
                                   f"{core.GAMES[self.snap_game.get()].title}.")
        self.btn_restore.set_enabled(False)

    def current_snapshot(self):
        sel = self.snaps.selection()
        return self.snap_list[int(sel[0])] if sel else None

    def show_snapshot_diff(self):
        s, p = self.current_snapshot(), self.profile(self.snap_game.get())
        self.btn_restore.set_enabled(bool(s))
        if not (s and p):
            return
        rows, other = core.diff_snapshot(s, p)
        self.snap_diff.load(rows, self.show_unmapped.get(),
                            empty="Identical.  The game's bindings haven't changed since this snapshot.",
                            raw=self.show_raw.get())
        if not self.show_unmapped.get():
            rows = [r for r in rows if r.mapped]
        msg = f"{len(rows)} binding(s) differ between this snapshot and the game right now."
        if other:
            msg += f"   Other changed files: {', '.join(other)}"
        self.snap_info.config(text=msg, fg=T.TEXT if rows or other else T.MUTED)

    def snapshot(self):
        p = self.profile(self.snap_game.get())
        if not p:
            return
        label = T.ask_string(self, f"Snapshot {p.game.title}",
                             "Give it a label so you can find it later (optional).", ok="Take snapshot")
        if label is None:
            return
        self.guard(lambda: (core.take_snapshot(p, label), self.refresh_snapshots(), self.refresh_cards(),
                            self.say(f"Snapshot saved for {p.game.title}.")))

    def restore(self):
        s, p = self.current_snapshot(), self.profile(self.snap_game.get())
        if not s:
            return
        if not T.confirm(self, f"Restore {p.game.key.upper()} controls?",
                         f"This overwrites {p.game.title}'s controls with the snapshot from {when(s.created)}. "
                         "The current files are snapshotted first, so this can be undone.",
                         ok="Restore", tone=T.DANGER):
            return
        self.guard(lambda: (core.restore_snapshot(s, p), self.refresh_all(),
                            self.say(f"Restored {p.game.title} controls from {when(s.created)}.")))

    def open_folder(self):
        s = self.current_snapshot()
        p = self.profile(self.snap_game.get())
        target = s.path if s else (core.snapshot_root(p) if p else core.STORE)
        target.mkdir(parents=True, exist_ok=True)
        os.startfile(target)

    def open_store(self):
        core.STORE.mkdir(parents=True, exist_ok=True)
        os.startfile(core.STORE)

    # ----- mods page -----
    MOD_COLS = (("order", "#", 40, False, "e"), ("name", "MOD", 200, True, "w"), ("source", "SOURCE", 80, False, "w"),
                ("version", "VERSION", 70, False, "w"), ("compat", "GAME VERSION", 112, False, "w"),
                ("size", "SIZE", 74, False, "e"), ("status", "IN GAME", 88, False, "w"))

    def _build_mods(self, parent):
        f = tk.Frame(parent, bg=T.BG, padx=32, pady=26)
        self.page_header(f, "Mods", "Local and Steam Workshop mods for each game. Turn mods on and set their load "
                                    "order here - # 1 is the top of the in-game Mod Manager and wins conflicts.")
        bar = tk.Frame(f, bg=T.BG)
        bar.pack(fill="x", pady=(20, 12))
        self.mod_game = tk.StringVar(value="ats")
        T.Segmented(bar, [(k, k.upper(), T.GAME_COLOR[k]) for k in core.GAMES], self.mod_game,
                    command=self.refresh_mods).pack(side="left")
        T.SearchBox(bar, self.mod_query, placeholder="Search mods, authors, categories", width=30).pack(
            side="left", padx=10)
        T.Chip(bar, "Active only", self.mod_active_only, command=self.render_mods).pack(side="left")
        T.Button(bar, "Open mod folder", self.open_mod_folder, kind="ghost", icon=T.I_FOLDER).pack(side="right")
        T.Button(bar, "Rescan", self.refresh_mods, kind="ghost", icon=T.I_REFRESH).pack(side="right", padx=4)
        T.Button(bar, "Install mod…", self.install_mod, kind="primary", icon=T.I_ADD).pack(side="right", padx=4)

        counts_row = tk.Frame(f, bg=T.BG)
        counts_row.pack(fill="x", pady=(0, 10))
        T.Button(counts_row, "Load order guide", self.show_order_guide, kind="ghost", icon=T.I_HELP, padx=8,
                 pady=4).pack(side="right")
        self.btn_autosort = T.Button(counts_row, "Auto-sort load order", self.auto_sort, kind="secondary",
                                     icon=T.I_SORT, padx=10, pady=4)
        self.btn_autosort.pack(side="right", padx=6)
        self.mods_counts = tk.Label(counts_row, bg=T.BG, fg=T.MUTED, font=T.SMALL, anchor="w", justify="left")
        self.mods_counts.pack(side="left", fill="x", expand=True)

        # unsaved load-order bar (shown only while there are staged changes)
        self.order_bar = tk.Frame(f, bg=T.ACCENT_DIM)
        tk.Frame(self.order_bar, bg=T.ACCENT, width=4).pack(side="left", fill="y")
        self.order_bar_text = tk.Label(self.order_bar, bg=T.ACCENT_DIM, fg=T.TEXT, font=T.UI, anchor="w")
        self.order_bar_text.pack(side="left", padx=14, pady=10)
        T.Button(self.order_bar, "Save to game", self.save_order, kind="primary", icon=T.I_CHECK).pack(
            side="right", padx=(4, 10))
        T.Button(self.order_bar, "Discard", self.discard_order, kind="ghost").pack(side="right")

        self.mods_body = tk.Frame(f, bg=T.BG)
        self.mods_body.pack(fill="both", expand=True)
        self.mod_detail = bordered(self.mods_body)
        self.mod_detail.configure(width=340)
        self.mod_detail.pack(side="right", fill="y", padx=(14, 0))
        self.mod_detail.pack_propagate(False)

        tf = bordered(self.mods_body)
        tf.pack(side="left", fill="both", expand=True)
        self.mod_tree = ttk.Treeview(tf, columns=[c[0] for c in self.MOD_COLS], show="headings", selectmode="browse")
        for c, t, w, stretch, anchor in self.MOD_COLS:
            self.mod_tree.heading(c, text=t, anchor=anchor, command=lambda c=c: self.sort_mods(c))
            self.mod_tree.column(c, width=w, minwidth=w if not stretch else 140, stretch=stretch, anchor=anchor)
        self.mod_tree.tag_configure("odd", background=T.STRIPE)
        self.mod_tree.tag_configure("inactive", foreground=T.MUTED)
        self.mod_tree.tag_configure("disabled", foreground=T.FAINT)
        self.mod_tree.tag_configure("outdated", foreground=T.ACCENT)
        self.mod_tree.tag_configure("missing", foreground=T.DANGER)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.mod_tree.yview)
        self.mod_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mod_tree.pack(fill="both", expand=True)
        self.mod_tree.bind("<<TreeviewSelect>>", lambda e: self.show_mod_detail())
        self.mod_tree.bind("<Alt-Up>", lambda e: (self.move_mod(-1), "break")[1])
        self.mod_tree.bind("<Alt-Down>", lambda e: (self.move_mod(1), "break")[1])
        self.mod_empty = tk.Label(tf, bg=T.SURFACE, fg=T.MUTED, font=T.UI)
        self.mod_rows = {}
        self.show_mod_detail()
        return f

    def refresh_mods(self):
        """Scan in the background: Workshop folders can be large and titles come from the Steam API."""
        if self.order_dirty() and not T.confirm(self, "Discard load order changes?",
                                                "You have unsaved load order changes. Rescanning throws them away.",
                                                ok="Discard", tone=T.DANGER):
            return
        self.mods_loaded = True
        self._mods_gen += 1
        gen, g = self._mods_gen, core.GAMES[self.mod_game.get()]
        profile = self.profile(g.key)
        self.mod_tree.delete(*self.mod_tree.get_children())
        self.mod_empty.configure(text="Scanning mods…")
        self.mod_empty.place(relx=0.5, rely=0.5, anchor="center")
        self.mods_counts.config(text="")

        def work():
            try:
                found = mods.all_mods(g)
                try:
                    cache = mods.fetch_workshop_details([m.workshop_id for m in found if m.workshop_id])
                except Exception:  # offline: fall back to whatever titles were cached before
                    cache = mods.load_workshop_cache()
                mods.apply_workshop_titles(found, cache)
                sii, order, order_err = None, [], None
                try:
                    sii = loadorder.find_profile_sii(profile) if profile else None
                    if sii:
                        order = loadorder.read_order(sii)[1]
                    else:
                        order_err = "No profile.sii found - launch the game once with this profile."
                except Exception as e:
                    order_err = str(e)
                self._mods_results[gen] = (found, mods.game_version(g), None, sii, order, order_err)
            except Exception as e:
                self._mods_results[gen] = ([], None, e, None, [], None)
        threading.Thread(target=work, daemon=True).start()
        self._await_mods(gen)

    def _await_mods(self, gen):
        if gen != self._mods_gen:
            return
        res = self._mods_results.pop(gen, None)
        if res is None:
            self.after(120, self._await_mods, gen)
            return
        self.mod_list, self.game_ver, err, self.mod_sii, order, self.order_err = res
        self.mod_order, self.mod_order_saved = list(order), list(order)
        self._add_missing_rows()
        self.render_mods()
        if err:
            T.error(self, "Couldn't read mods", str(err))

    def _add_missing_rows(self):
        """Mods the profile still lists as active but that aren't installed (e.g. unsubscribed)."""
        known = {m.package for m in self.mod_list}
        g = core.GAMES[self.mod_game.get()]
        for e in self.mod_order:
            if e.package not in known:
                self.mod_list.append(mods.Mod(g, "missing", Path(e.package), name=e.display, display=e.display,
                                              pkg_id=e.package))
                known.add(e.package)

    # load order helpers
    def order_pos(self, m):
        return next((i for i, e in enumerate(self.mod_order) if e.package == m.package), None)

    def order_dirty(self):
        return self.mod_order != self.mod_order_saved

    def mod_status(self, m):
        if m.source == "missing":
            return "Missing"
        if not m.enabled:
            return "Parked"
        return "Active" if self.order_pos(m) is not None else "Off"

    def sort_mods(self, col):
        cur, desc = self.mod_sort
        self.mod_sort = (col, not desc if col == cur else col == "size")
        self.render_mods(keep=getattr(self.current_mod(), "path", None))

    def _sort_key(self, col):
        order_n = len(self.mod_order)
        return {
            "order": lambda m: (p if (p := self.order_pos(m)) is not None else order_n, m.name.lower()),
            "name": lambda m: m.name.lower(),
            "source": lambda m: (m.source, m.name.lower()),
            "version": lambda m: (m.version or "~", m.name.lower()),
            "compat": lambda m: ({"outdated": 0, "unknown": 1, "ok": 2}[m.compat(self.game_ver)], m.name.lower()),
            "size": lambda m: m.size,
            "status": lambda m: ({"Missing": 0, "Active": 1, "Off": 2, "Parked": 3}[self.mod_status(m)], m.name.lower()),
        }[col]

    def render_mods(self, keep=None):
        if not hasattr(self, "game_ver"):
            return
        self.mod_tree.delete(*self.mod_tree.get_children())
        self.mod_rows = {}
        col, desc = self.mod_sort
        for c, t, *_ in self.MOD_COLS:
            self.mod_tree.heading(c, text=t + ("  ▼" if desc else "  ▲") * (c == col))
        q = self.mod_query.get().strip().lower()
        for m in sorted(self.mod_list, key=self._sort_key(col), reverse=desc):
            if q and not any(q in s.lower() for s in (m.name, m.author, m.path.name, " ".join(m.categories))):
                continue
            pos, status = self.order_pos(m), self.mod_status(m)
            if self.mod_active_only.get() and pos is None:
                continue
            c = m.compat(self.game_ver)
            tags = ["odd"] if len(self.mod_rows) % 2 else []
            tags.append({"Missing": "missing", "Parked": "disabled", "Off": "inactive"}.get(status, ""))
            if status == "Active" and c == "outdated":
                tags.append("outdated")
            iid = self.mod_tree.insert("", "end", tags=tags, values=(
                "" if pos is None else pos + 1, m.name,
                {"workshop": "Workshop", "local": "Local", "missing": "—"}[m.source], m.version or "—",
                {"ok": "✓  Compatible", "outdated": "⚠  Outdated", "unknown": "—"}[c],
                "—" if m.source == "missing" else mods.fmt_size(m.size), status))
            self.mod_rows[iid] = m
            if keep is not None and m.path == keep:
                self.mod_tree.selection_set(iid)
                self.mod_tree.see(iid)
        if self.mod_rows:
            self.mod_empty.place_forget()
        else:
            self.mod_empty.configure(text="No mods match that filter." if q or self.mod_active_only.get() else
                                     "No mods installed for this game yet.  Use Install mod… to add a .scs file.")
            self.mod_empty.place(relx=0.5, rely=0.5, anchor="center")
        installed = [m for m in self.mod_list if m.source != "missing"]
        local = [m for m in installed if m.source == "local"]
        outdated = sum(1 for m in installed if self.order_pos(m) is not None and m.compat(self.game_ver) == "outdated")
        ver = mods.short_version(self.game_ver)
        self.mods_counts.config(
            text=f"Game version {ver}   ·   {len(self.mod_order)} active in game   ·   {len(local)} local "
                 f"({sum(not m.enabled for m in local)} parked)   ·   {len(installed) - len(local)} Workshop   ·   "
                 f"{mods.fmt_size(sum(m.size for m in installed))} on disk"
                 + (f"   ·   {outdated} active may not work with {ver}" if outdated else "")
                 + (f"   ·   Load order unavailable: {self.order_err}" if self.order_err else "")
                 + ("" if self.game_ver else "   ·   launch the game once so its version can be detected"))
        self.render_order_bar()
        self.btn_autosort.set_enabled(self.mod_sii is not None and not self.order_err and len(self.mod_order) > 1)
        if keep is None:
            self.show_mod_detail()

    def render_order_bar(self):
        if self.order_dirty():
            saved = {e.package for e in self.mod_order_saved}
            now = {e.package for e in self.mod_order}
            parts = [f"{len(now - saved)} turned on" if now - saved else "",
                     f"{len(saved - now)} turned off" if saved - now else "",
                     "order changed" if [e for e in self.mod_order if e.package in saved] !=
                                        [e for e in self.mod_order_saved if e.package in now] else ""]
            self.order_bar_text.config(text="Unsaved load order:  " + ",  ".join(p for p in parts if p)
                                            + ".   Close the game before saving.")
            if not self.order_bar.winfo_ismapped():
                self.order_bar.pack(fill="x", pady=(0, 10), before=self.mods_body)
        else:
            self.order_bar.pack_forget()

    def current_mod(self):
        sel = self.mod_tree.selection()
        return self.mod_rows.get(sel[0]) if sel else None

    def show_mod_detail(self):
        d = self.mod_detail
        for w in d.winfo_children():
            w.destroy()
        m = self.current_mod()
        if not m:
            tk.Label(d, text=T.I_PUZZLE, font=(T.ICON_FONT[0], 34), bg=T.SURFACE, fg=T.FAINT).pack(pady=(90, 12))
            tk.Label(d, text="Select a mod to see its details.", bg=T.SURFACE, fg=T.MUTED, font=T.UI).pack()
            tk.Label(d, text="Click a column header to sort.\nAlt + ↑ / ↓ moves the selected mod.", bg=T.SURFACE,
                     fg=T.FAINT, font=T.SMALL, justify="center").pack(pady=(10, 0))
            return
        inner = tk.Frame(d, bg=T.SURFACE, padx=20, pady=20)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=m.name, font=T.H2, bg=T.SURFACE, fg=T.TEXT, wraplength=290, justify="left",
                 anchor="w").pack(fill="x")
        badges = tk.Frame(inner, bg=T.SURFACE)
        badges.pack(fill="x", pady=(8, 14))
        c, pos, status = m.compat(self.game_ver), self.order_pos(m), self.mod_status(m)
        for text, bg, fg in (({"workshop": "WORKSHOP", "local": "LOCAL", "missing": "NOT INSTALLED"}[m.source],
                              T.RAISED, T.DANGER if m.source == "missing" else T.MUTED),
                             (f"ACTIVE  #{pos + 1}" if pos is not None else status.upper(), T.RAISED,
                              T.TEXT if pos is not None else T.FAINT),
                             *([("OUTDATED", T.ACCENT_DIM, T.ACCENT)] if c == "outdated" else [])):
            tk.Label(badges, text=text, font=T.BADGE, bg=bg, fg=fg, padx=7, pady=2).pack(side="left", padx=(0, 6))

        if m.source != "missing":
            group, why = loadorder.classify(m.name, m.categories)
            gl = tk.Frame(inner, bg=T.SURFACE)
            gl.pack(fill="x", pady=(0, 10))
            tk.Label(gl, text=T.I_SORT, font=(T.ICON_FONT[0], 10), bg=T.SURFACE, fg=T.ACCENT).pack(side="left", anchor="n")
            tk.Label(gl, text=f"{group.title}  ·  {why}", font=T.SMALL, bg=T.SURFACE, fg=T.MUTED, wraplength=270,
                     justify="left", anchor="w").pack(side="left", padx=(8, 0), fill="x")
        if notes := loadorder.author_notes(m.description):
            box = tk.Frame(inner, bg=T.ACCENT_DIM, padx=10, pady=8)
            box.pack(fill="x", pady=(0, 12))
            tk.Label(box, text="AUTHOR'S LOAD ORDER NOTE", font=T.CAPS, bg=T.ACCENT_DIM, fg=T.ACCENT).pack(anchor="w")
            for n in notes:
                tk.Label(box, text=n, font=T.SMALL, bg=T.ACCENT_DIM, fg=T.TEXT, wraplength=270, justify="left",
                         anchor="w").pack(fill="x", pady=(4, 0))

        grid = tk.Frame(inner, bg=T.SURFACE)
        grid.pack(fill="x")
        works = ", ".join(v.rstrip(".*") for v in m.compatible[:8]) + (" …" if len(m.compatible) > 8 else "")
        facts = (("Author", m.author or "—"), ("Version", m.version or "—"),
                 ("Categories", ", ".join(m.categories) or "—"),
                 ("Works with", "any version" if m.universal else (works or "not declared")),
                 ("Size", mods.fmt_size(m.size)),
                 ("File", m.path.name))
        if m.source == "missing":
            facts = (("Package", m.package), ("Why", "Still listed as active in your profile, but the mod isn't "
                                                     "installed any more. Turn it off to tidy the list."))
        for i, (k, v) in enumerate(facts):
            tk.Label(grid, text=k, bg=T.SURFACE, fg=T.FAINT, font=T.SMALL, anchor="nw").grid(
                row=i, column=0, sticky="nw", pady=2)
            tk.Label(grid, text=v, bg=T.SURFACE, fg=T.TEXT, font=T.SMALL, anchor="w", justify="left",
                     wraplength=210).grid(row=i, column=1, sticky="w", padx=(12, 0), pady=2)

        actions = tk.Frame(inner, bg=T.SURFACE)
        actions.pack(side="bottom", fill="x", pady=(14, 0))
        can_order = self.mod_sii is not None and not self.order_err
        if status == "Parked":
            T.Button(actions, "Unpark file", lambda: self.toggle_mod(m), kind="primary").pack(fill="x", pady=(0, 6))
            tk.Label(actions, text="Parked files sit in mod_disabled, where the game can't see them.",
                     bg=T.SURFACE, fg=T.FAINT, font=T.SMALL, wraplength=290, justify="left").pack(fill="x", pady=(0, 6))
        elif can_order and pos is None:
            T.Button(actions, "Turn on in game", lambda: self.set_active(m, True), kind="primary",
                     icon=T.I_CHECK).pack(fill="x", pady=(0, 6))
        elif can_order:
            moves = tk.Frame(actions, bg=T.SURFACE)
            moves.pack(fill="x", pady=(0, 6))
            for text, fn in (("Top", lambda: self.move_mod(-10**6)), ("Up", lambda: self.move_mod(-1)),
                             ("Down", lambda: self.move_mod(1)), ("Bottom", lambda: self.move_mod(10**6))):
                T.Button(moves, text, fn, kind="secondary", padx=6, pady=5).pack(side="left", fill="x", expand=True,
                                                                                 padx=(0, 4))
            T.Button(actions, "Turn off in game", lambda: self.set_active(m, False), kind="secondary").pack(
                fill="x", pady=(0, 6))
        small = tk.Frame(actions, bg=T.SURFACE)
        small.pack(fill="x")
        links = []
        if m.source == "workshop":
            links.append(("Workshop", lambda: os.startfile(f"steam://url/CommunityFilePage/{m.workshop_id}"),
                          T.I_GLOBE))
        if m.source != "missing":
            links.append(("Explorer", lambda: os.startfile(m.path.parent if m.path.is_file() else m.path),
                          T.I_FOLDER))
        if m.source == "local" and m.enabled:
            links.append(("Park file", lambda: self.toggle_mod(m), None))
        for text, fn, icon in links:
            T.Button(small, text, fn, kind="ghost", icon=icon, padx=6, pady=5).pack(side="left", fill="x",
                                                                                   expand=True)
        if m.source in ("local", "workshop"):
            T.Button(actions, "Unsubscribe" if m.source == "workshop" else "Move to Recycle Bin",
                     lambda: self.remove_mod(m), kind="ghost", icon=T.I_DELETE, pady=5).pack(fill="x", pady=(4, 0))

        if m.description:
            tk.Label(inner, text="DESCRIPTION", font=T.CAPS, bg=T.SURFACE, fg=T.FAINT).pack(anchor="w", pady=(16, 6))
            txt = tk.Text(inner, bg=T.RAISED, fg=T.MUTED, font=T.SMALL, wrap="word", relief="flat", bd=0,
                          padx=10, pady=8, height=6, highlightthickness=0, cursor="arrow")
            txt.insert("1.0", m.description)
            txt.configure(state="disabled")
            txt.pack(fill="both", expand=True)

    def _refresh_after_order_change(self, m):
        self.render_mods(keep=m.path)
        self.show_mod_detail()

    def set_active(self, m, on):
        if on:
            self.mod_order.insert(0, loadorder.Entry(m.package, m.display or m.name))
            self.say(f"{m.name} turned on at the top of the load order.  Save to apply it in the game.")
        else:
            self.mod_order = [e for e in self.mod_order if e.package != m.package]
            if m.source == "missing":
                self.mod_list.remove(m)
            self.say(f"{m.name} turned off.  Save to apply it in the game.")
        self._refresh_after_order_change(m)

    def move_mod(self, delta):
        m = self.current_mod()
        pos = self.order_pos(m) if m else None
        if pos is None:
            return
        new = max(0, min(len(self.mod_order) - 1, pos + delta))
        if new != pos:
            self.mod_order.insert(new, self.mod_order.pop(pos))
            self.mod_sort = ("order", False)  # show the move where it happened
            self._refresh_after_order_change(m)

    def auto_sort(self):
        if self.mod_sii is None or self.order_err:
            T.info(self, "Load order unavailable", self.order_err or "No profile.sii found for this game.")
            return
        by_pkg = {m.package: m for m in self.mod_list}
        new = loadorder.recommended_order(
            self.mod_order, lambda e: by_pkg[e.package].categories if e.package in by_pkg else [])
        if new == self.mod_order:
            self.say("Load order already follows the recommended groups.  Nothing to change.")
            return
        moved = sum(a != b for a, b in zip(new, self.mod_order))
        self.mod_order = new
        self.mod_sort = ("order", False)
        self.render_mods(keep=getattr(self.current_mod(), "path", None))
        self.show_mod_detail()
        self.say(f"Auto-sorted: {moved} position(s) changed.  Mods keep their relative order inside each group; "
                 "check any author notes, then Save to game.")

    def show_order_guide(self):
        win = tk.Toplevel(self, bg=T.SURFACE)
        win.withdraw()
        win.title("Load order guide")
        win.transient(self)
        win.resizable(False, False)
        tk.Frame(win, bg=T.ACCENT, height=3).pack(fill="x")
        body = tk.Frame(win, bg=T.SURFACE, padx=26, pady=22)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="How mod load order works", font=T.H2, bg=T.SURFACE, fg=T.TEXT).pack(anchor="w")
        tk.Label(body, text="The mod at the top of the in-game Mod Manager (# 1 here) has the highest priority: when two "
                            "mods change the same file, the higher one wins. Order only matters when mods overlap. "
                            "Auto-sort uses the groups below, top to bottom, and keeps your own order inside each group.",
                 font=T.UI, bg=T.SURFACE, fg=T.MUTED, wraplength=620, justify="left").pack(anchor="w", pady=(6, 14))
        groups = tk.Frame(body, bg=T.RAISED, padx=14, pady=10)
        groups.pack(fill="x")
        for i, g in enumerate(loadorder.GROUPS, 1):
            tk.Label(groups, text=f"{i:>2}", font=T.BADGE, bg=T.RAISED, fg=T.ACCENT).grid(row=i, column=0, sticky="e")
            tk.Label(groups, text=g.title, font=T.SMALL_BOLD, bg=T.RAISED, fg=T.TEXT).grid(
                row=i, column=1, sticky="w", padx=(10, 16), pady=1)
            tk.Label(groups, text=g.examples, font=T.SMALL, bg=T.RAISED, fg=T.MUTED).grid(row=i, column=2, sticky="w")
        tk.Label(body, text="Rules that beat the groups:  follow each mod author's instructions (shown on the mod's "
                            "detail panel), keep compatibility patches above the mods they patch, and load map combos "
                            "exactly in the order the combo's guide gives.",
                 font=T.SMALL, bg=T.SURFACE, fg=T.TEXT, wraplength=620, justify="left").pack(anchor="w", pady=(14, 12))
        tk.Label(body, text="SOURCES & FURTHER READING", font=T.CAPS, bg=T.SURFACE, fg=T.FAINT).pack(anchor="w")
        for title, where, url in loadorder.GUIDES:
            row = tk.Frame(body, bg=T.SURFACE, cursor="hand2")
            row.pack(fill="x", pady=(6, 0))
            a = tk.Label(row, text=title, font=T.SMALL_BOLD, bg=T.SURFACE, fg=T.ACCENT, cursor="hand2")
            a.pack(side="left")
            tk.Label(row, text=f"  ·  {where}", font=T.SMALL, bg=T.SURFACE, fg=T.MUTED).pack(side="left")
            for w in (row, a):
                w.bind("<ButtonRelease-1>", lambda e, u=url: webbrowser.open(u))
        bar = tk.Frame(win, bg=T.BG, padx=18, pady=14)
        bar.pack(fill="x")
        T.Button(bar, "Close", win.destroy, kind="primary").pack(side="right")
        win.bind("<Escape>", lambda e: win.destroy())
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_reqwidth()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_reqheight()) // 3
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        win.deiconify()
        T.dark_titlebar(win)

    def save_order(self):
        g = core.GAMES[self.mod_game.get()]

        def run():
            dest = loadorder.write_order(self.mod_sii, g, self.mod_order)
            self.mod_order_saved = list(self.mod_order)
            self.render_mods(keep=getattr(self.current_mod(), "path", None))
            self.say(f"Load order saved to {g.title}.  The previous profile.sii is backed up in {dest}.")
        self.guard(run)

    def discard_order(self):
        self.mod_order = list(self.mod_order_saved)
        self.mod_list = [m for m in self.mod_list if m.source != "missing"]
        self._add_missing_rows()
        self.render_mods()
        self.say("Load order changes discarded.")

    def toggle_mod(self, m):
        def run():
            dest = mods.set_enabled(m, not m.enabled)
            m.path, m.enabled = dest, not m.enabled
            if not m.enabled:  # a parked file can't load, so take it out of the game's list too
                self.mod_order = [e for e in self.mod_order if e.package != m.package]
            self.render_mods(keep=dest)
            self.show_mod_detail()
            self.say(f"{'Unparked' if m.enabled else 'Parked'} {m.name}."
                     + ("" if m.enabled else f"  Moved to {mods.disabled_dir(m.game)} so the game ignores it."))
        self.guard(run)

    def remove_mod(self, m):
        workshop = m.source == "workshop"
        if not T.confirm(self, "Unsubscribe?" if workshop else "Remove mod?",
                         f"You'll be unsubscribed from {m.name} and Steam will delete its files. Steam may show the "
                         "game as running for a few seconds while this happens." if workshop else
                         f"{m.name} will be moved to the Recycle Bin. "
                         "You can restore it from there if you change your mind.",
                         ok="Unsubscribe" if workshop else "Move to Recycle Bin", tone=T.DANGER,
                         detail=f"Workshop item {m.workshop_id}" if workshop else str(m.path)):
            return
        self.say(f"Unsubscribing from {m.name}…" if workshop else "")
        self.update_idletasks()

        def run():
            if workshop:
                steamugc.unsubscribe(m.game, [m.workshop_id])
            else:
                mods.remove(m)
            self.mod_list.remove(m)
            was_active = self.order_pos(m) is not None
            self.mod_order = [e for e in self.mod_order if e.package != m.package]
            self.render_mods()
            self.say(("Unsubscribed from " if workshop else "Moved to the Recycle Bin: ") + m.name + "."
                     + ("  It was active, so save the load order to drop it from the game's list." if was_active else ""))
        self.guard(run)

    def install_mod(self):
        g = core.GAMES[self.mod_game.get()]
        paths = filedialog.askopenfilenames(parent=self, title=f"Install mods for {g.title}",
                                            filetypes=[("SCS mods", "*.scs *.zip"), ("All files", "*.*")])
        if not paths:
            return

        def run():
            done = [mods.install(g, Path(p)).name for p in paths]
            self.refresh_mods()
            self.say(f"Installed {', '.join(done)} into {mods.mod_dir(g)}. Turn it on here or in the game.")
        self.guard(run)

    def open_mod_folder(self):
        d = mods.mod_dir(core.GAMES[self.mod_game.get()])
        d.mkdir(parents=True, exist_ok=True)
        os.startfile(d)

    # ----- cleanup page -----
    def _build_cleanup(self, parent):
        f = tk.Frame(parent, bg=T.BG, padx=32, pady=26)
        self.page_header(f, "Cleanup", "Cloud-sync conflicts leave copies like “controls (# Name clash …).sii” and "
                                       "“controls - Copy.sii” in your game folders. Quarantine moves them out of the "
                                       "way. Nothing is deleted.")
        tk.Label(f, text="PROFILE HEALTH", font=T.CAPS, bg=T.BG, fg=T.FAINT).pack(anchor="w", pady=(22, 8))
        self.health = bordered(f)
        self.health.pack(fill="x")

        bar = tk.Frame(f, bg=T.BG)
        bar.pack(fill="x", pady=(22, 12))
        self.clutter_count = tk.Label(bar, bg=T.BG, fg=T.MUTED, font=T.UI)
        self.clutter_count.pack(side="left")
        T.Button(bar, "Open quarantine", self.open_quarantine, kind="ghost", icon=T.I_FOLDER).pack(side="right")
        T.Button(bar, "Rescan", self.refresh_cleanup, kind="ghost", icon=T.I_REFRESH).pack(side="right", padx=4)
        self.btn_q_sel = T.Button(bar, "Quarantine selected", lambda: self.quarantine(False))
        self.btn_q_sel.pack(side="right", padx=4)
        self.btn_q_all = T.Button(bar, "Quarantine all", lambda: self.quarantine(True), kind="primary",
                                  icon=T.I_REPAIR)
        self.btn_q_all.pack(side="right", padx=4)

        tf = bordered(f)
        tf.pack(fill="both", expand=True)
        cols = (("game", "GAME", 70, False, "w"), ("file", "FILE", 560, True, "w"),
                ("size", "SIZE", 90, False, "e"), ("modified", "MODIFIED", 190, False, "w"))
        self.clutter_tree = ttk.Treeview(tf, columns=[c[0] for c in cols], show="headings", selectmode="extended")
        for c, t, w, stretch, anchor in cols:
            self.clutter_tree.heading(c, text=t, anchor=anchor)
            self.clutter_tree.column(c, width=w, minwidth=60, stretch=stretch, anchor=anchor)
        self.clutter_tree.tag_configure("odd", background=T.STRIPE)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.clutter_tree.yview)
        self.clutter_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.clutter_tree.pack(fill="both", expand=True)
        self.clutter_tree.bind("<<TreeviewSelect>>", lambda e: self.btn_q_sel.set_enabled(
            bool(self.clutter_tree.selection())))
        self.clutter_empty = tk.Label(tf, bg=T.SURFACE, fg=T.MUTED, font=T.UI,
                                      text="All clean.  No sync-conflict leftovers in your game folders.")
        return f

    def refresh_cleanup(self):
        for w in self.health.winfo_children():
            w.destroy()
        for i, k in enumerate(core.GAMES):
            p = self.profile(k)
            row = tk.Frame(self.health, bg=T.SURFACE, padx=16, pady=10)
            row.pack(fill="x")
            if i:
                tk.Frame(self.health, bg=T.BORDER, height=1).pack(fill="x", before=row)
            tk.Label(row, text=k.upper(), bg=T.GAME_COLOR[k], fg="#0d0f12", font=T.BADGE, padx=7,
                     pady=1).pack(side="left", anchor="n", pady=(2, 0))
            msgs = tk.Frame(row, bg=T.SURFACE)
            msgs.pack(side="left", fill="x", expand=True, padx=(14, 0))
            items = cleanup.profile_health(p) if p else [("warn", "No profile found.")]
            for level, text in items:
                line = tk.Frame(msgs, bg=T.SURFACE)
                line.pack(fill="x")
                color = {"ok": "#3ecf8e", "warn": T.ACCENT, "bad": T.DANGER}[level]
                tk.Label(line, text="●", fg=color, bg=T.SURFACE, font=T.SMALL).pack(side="left", anchor="n")
                tk.Label(line, text=text, fg=T.TEXT if level == "bad" else T.MUTED, bg=T.SURFACE, font=T.SMALL,
                         justify="left", anchor="w", wraplength=900).pack(side="left", padx=(8, 0))

        self.clutter = [c for g in core.GAMES.values() for c in cleanup.find_clutter(g)]
        self.clutter_tree.delete(*self.clutter_tree.get_children())
        for i, c in enumerate(self.clutter):
            self.clutter_tree.insert("", "end", iid=str(i), tags=["odd"] if i % 2 else [], values=(
                c.game.key.upper(), c.rel, mods.fmt_size(c.size),
                datetime.fromtimestamp(c.modified).strftime("%b %d, %Y  ·  %H:%M")))
        if self.clutter:
            self.clutter_empty.place_forget()
        else:
            self.clutter_empty.place(relx=0.5, rely=0.5, anchor="center")
        total = mods.fmt_size(sum(c.size for c in self.clutter))
        self.clutter_count.config(text=f"{len(self.clutter)} leftover file(s), {total}" if self.clutter
                                  else "Nothing to clean up.")
        self.nav["cleanup"].set_badge(str(len(self.clutter)) if self.clutter else "")
        self.btn_q_all.set_enabled(bool(self.clutter))
        self.btn_q_sel.set_enabled(False)

    def quarantine(self, everything):
        items = self.clutter if everything else [self.clutter[int(i)] for i in self.clutter_tree.selection()]
        if not items:
            return
        if not T.confirm(self, f"Quarantine {len(items)} file(s)?",
                         f"They'll be moved to {cleanup.QUARANTINE} with a manifest listing where each one "
                         "came from, so anything can be put back by hand.", ok="Quarantine"):
            return

        def run():
            dest = cleanup.quarantine(items)
            self.refresh_cleanup()
            self.say(f"Moved {len(items)} file(s) to {dest}.")
        self.guard(run)

    def open_quarantine(self):
        cleanup.QUARANTINE.mkdir(parents=True, exist_ok=True)
        os.startfile(cleanup.QUARANTINE)

    # ----- startup -----
    def startup_check(self):
        """Baseline-snapshot new profiles; warn if a game's controls drifted since the last snapshot."""
        warnings = []
        for k in core.GAMES:
            p = self.profile(k)
            if not p:
                continue
            snaps = core.list_snapshots(p)
            if not snaps:
                core.take_snapshot(p, "baseline")
                continue
            rows, other = core.diff_snapshot(snaps[0], p)
            rows = [r for r in rows if r.mapped]  # unmapped churn isn't worth a warning
            if rows or other:
                warnings.append(f"{k.upper()}: {len(rows)} binding(s) changed since the last snapshot "
                                f"({when(snaps[0].created)})")
        if warnings:
            self.banner_text.config(text="\n".join(warnings) + "\nIf that was you, take a new snapshot.")
            self.banner.pack(fill="x", padx=32, pady=(22, 0), before=self.pages_host)


if __name__ == "__main__":
    App().mainloop()
