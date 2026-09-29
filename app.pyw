"""Truck Config Manager - snapshot, restore and sync ETS2/ATS controller bindings."""
import os
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from truckcfg import core

EMPTY = "(not bound in this game)"


def fmt(v):
    return EMPTY if v is None else v


class DiffTable(ttk.Frame):
    def __init__(self, master, left_title, right_title):
        super().__init__(master)
        cols = ("action", "left", "right")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="extended")
        for c, title, w in zip(cols, ("Action", left_title, right_title), (170, 380, 380)):
            self.tree.heading(c, text=title)
            self.tree.column(c, width=w, stretch=c != "action")
        self.tree.tag_configure("missing", foreground="#888")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.rows = {}

    def set_titles(self, left, right):
        self.tree.heading("left", text=left)
        self.tree.heading("right", text=right)

    def load(self, rows, show_unmapped=True):
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        for r in rows:
            missing = r.left is None or r.right is None
            if not show_unmapped and not r.mapped:
                continue
            label = r.name if r.kind == "mix" else f"{r.name} [{r.kind}]"
            iid = self.tree.insert("", "end", values=(label, fmt(r.left), fmt(r.right)),
                                   tags=("missing",) if missing else ())
            self.rows[iid] = r

    def selected(self):
        return [self.rows[i] for i in self.tree.selection()]

    def all(self):
        return list(self.rows.values())


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Truck Config Manager")
        self.geometry("1100x650")
        self.minsize(800, 450)
        self.profiles = {k: core.find_profiles(g) for k, g in core.GAMES.items()}
        self.profile_var = {k: tk.StringVar() for k in core.GAMES}

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        for k, g in core.GAMES.items():
            ttk.Label(top, text=g.title + " profile:").pack(side="left")
            cb = ttk.Combobox(top, state="readonly", width=28, textvariable=self.profile_var[k],
                              values=[p.label for p in self.profiles[k]])
            cb.pack(side="left", padx=(4, 18))
            cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_all())
            if self.profiles[k]:
                cb.current(0)
        self.show_unmapped = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Show unmapped actions", variable=self.show_unmapped,
                        command=lambda: (self.refresh_compare(), self.show_snapshot_diff())).pack(side="right")

        self.banner = ttk.Label(self, foreground="#b35c00", padding=(8, 0))
        self.banner.pack(fill="x")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        nb.add(self._build_compare(nb), text="Compare games")
        nb.add(self._build_snapshots(nb), text="Snapshots")

        self.status = ttk.Label(self, relief="sunken", anchor="w", padding=(6, 2))
        self.status.pack(fill="x", side="bottom")

        self.startup_check()
        self.refresh_all()

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
            messagebox.showerror("Truck Config Manager", str(e))

    def refresh_all(self):
        self.refresh_compare()
        self.refresh_snapshots()

    # ----- compare tab -----
    def _build_compare(self, nb):
        f = ttk.Frame(nb, padding=6)
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="Copy ALL  ETS2 → ATS", command=lambda: self.copy("ets2", "ats", True)).pack(side="right")
        ttk.Button(bar, text="Copy selected  ATS → ETS2", command=lambda: self.copy("ats", "ets2")).pack(side="right", padx=4)
        ttk.Button(bar, text="Copy selected  ETS2 → ATS", command=lambda: self.copy("ets2", "ats")).pack(side="right")
        self.cmp = DiffTable(f, "ETS2", "ATS")
        self.cmp.pack(fill="both", expand=True)
        return f

    def refresh_compare(self):
        e, a = self.profile("ets2"), self.profile("ats")
        if not (e and a):
            self.cmp.load([])
            return
        rows = core.diff_bindings(core.parse_bindings(core.read_text(e.path / "controls.sii")),
                                  core.parse_bindings(core.read_text(a.path / "controls.sii")))
        self.cmp.load(rows, self.show_unmapped.get())
        mapped = [r for r in rows if r.mapped]
        shared = sum(1 for r in mapped if r.left is not None and r.right is not None)
        hidden = "" if self.show_unmapped.get() else f"  {len(rows) - len(mapped)} unmapped difference(s) hidden."
        self.say(f"{shared} mapped binding(s) differ between ETS2 and ATS, "
                 f"{len(mapped) - shared} mapped action(s) exist in only one game.{hidden}")

    def copy(self, src_key, dst_key, everything=False):
        src, dst = self.profile(src_key), self.profile(dst_key)
        rows = self.cmp.all() if everything else self.cmp.selected()
        rows = [r for r in rows if r.left is not None and r.right is not None]
        if not rows:
            messagebox.showinfo("Copy", "Select one or more rows that exist in both games.")
            return
        names = ", ".join(r.name for r in rows[:12]) + (" …" if len(rows) > 12 else "")
        if not messagebox.askyesno("Copy bindings", f"Copy {len(rows)} binding(s) from {src.game.title} "
                                   f"into {dst.game.title}?\n\n{names}\n\nA snapshot of {dst_key.upper()} "
                                   f"is taken first so you can undo from the Snapshots tab."):
            return

        def run():
            n, missing = core.copy_bindings(src, dst, [(r.kind, r.name) for r in rows])
            self.refresh_all()
            self.say(f"Copied {n} binding(s) {src_key.upper()} → {dst_key.upper()}."
                     + (f" Skipped (not in target): {missing}" if missing else ""))
        self.guard(run)

    # ----- snapshots tab -----
    def _build_snapshots(self, nb):
        f = ttk.Frame(nb, padding=6)
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 6))
        self.snap_game = tk.StringVar(value="ats")
        for k in core.GAMES:
            ttk.Radiobutton(bar, text=k.upper(), value=k, variable=self.snap_game,
                            command=self.refresh_snapshots).pack(side="left")
        ttk.Button(bar, text="Open folder", command=self.open_folder).pack(side="right")
        ttk.Button(bar, text="Restore to game", command=self.restore).pack(side="right", padx=4)
        ttk.Button(bar, text="Take snapshot", command=self.snapshot).pack(side="right")

        pw = ttk.PanedWindow(f, orient="vertical")
        pw.pack(fill="both", expand=True)
        lf = ttk.Frame(pw)
        self.snaps = ttk.Treeview(lf, columns=("created", "label", "files"), show="headings",
                                  selectmode="browse", height=7)
        for c, t, w in (("created", "Taken", 170), ("label", "Label", 260), ("files", "Files", 500)):
            self.snaps.heading(c, text=t)
            self.snaps.column(c, width=w)
        self.snaps.pack(fill="both", expand=True)
        self.snaps.bind("<<TreeviewSelect>>", lambda e: self.show_snapshot_diff())
        pw.add(lf, weight=1)

        df = ttk.Frame(pw)
        self.snap_info = ttk.Label(df, padding=(0, 4))
        self.snap_info.pack(fill="x")
        self.snap_diff = DiffTable(df, "Snapshot", "Current")
        self.snap_diff.pack(fill="both", expand=True)
        pw.add(df, weight=2)
        self.snap_list = []
        return f

    def refresh_snapshots(self):
        p = self.profile(self.snap_game.get())
        self.snaps.delete(*self.snaps.get_children())
        self.snap_list = core.list_snapshots(p) if p else []
        for i, s in enumerate(self.snap_list):
            self.snaps.insert("", "end", iid=str(i), values=(s.created.replace("T", "  "), s.label,
                                                             ", ".join(s.meta.get("files", []))))
        self.snap_diff.load([])
        self.snap_info.config(text="Select a snapshot to see what changed since it was taken.")

    def current_snapshot(self):
        sel = self.snaps.selection()
        return self.snap_list[int(sel[0])] if sel else None

    def show_snapshot_diff(self):
        s, p = self.current_snapshot(), self.profile(self.snap_game.get())
        if not (s and p):
            return
        rows, other = core.diff_snapshot(s, p)
        self.snap_diff.load(rows, self.show_unmapped.get())
        if not self.show_unmapped.get():
            rows = [r for r in rows if r.mapped]
        msg = f"{len(rows)} binding(s) differ between this snapshot and the game right now."
        if other:
            msg += f"  Other changed files: {', '.join(other)}"
        self.snap_info.config(text=msg)

    def snapshot(self):
        p = self.profile(self.snap_game.get())
        label = simpledialog.askstring("Take snapshot", "Label (optional):", parent=self)
        if label is None:
            return
        self.guard(lambda: (core.take_snapshot(p, label), self.refresh_snapshots(),
                            self.say(f"Snapshot saved for {p.game.title}.")))

    def restore(self):
        s, p = self.current_snapshot(), self.profile(self.snap_game.get())
        if not s:
            messagebox.showinfo("Restore", "Select a snapshot first.")
            return
        if not messagebox.askyesno("Restore snapshot", f"Overwrite {p.game.title} controls with the snapshot "
                                   f"from {s.created.replace('T', ' ')}?\n\nThe current files are snapshotted first."):
            return
        self.guard(lambda: (core.restore_snapshot(s, p), self.refresh_all(),
                            self.say(f"Restored {p.game.title} controls from {s.created}.")))

    def open_folder(self):
        s = self.current_snapshot()
        p = self.profile(self.snap_game.get())
        target = s.path if s else (core.snapshot_root(p) if p else core.STORE)
        target.mkdir(parents=True, exist_ok=True)
        os.startfile(target)

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
                warnings.append(f"{k.upper()}: {len(rows)} binding(s) changed since last snapshot "
                                f"({snaps[0].created.replace('T', ' ')})")
        self.banner.config(text=("⚠ " + "   |   ".join(warnings) + "  — check the Snapshots tab. "
                                 "Take a new snapshot if the change was yours.") if warnings else "")


if __name__ == "__main__":
    App().mainloop()
