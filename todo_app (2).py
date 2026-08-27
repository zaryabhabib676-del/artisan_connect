"""
==============================================================================
 To-Do List Desktop Application  —  EXTREME ADVANCED EDITION
 Built with: Python + Tkinter + JSON
 Week 05 Project (Python Internship)
==============================================================================
CORE REQUIREMENTS (assignment):
    - Add / View / Update / Delete / Delete All / Mark Complete
    - Auto Save & Auto Load tasks using JSON (tasks.json)
    - User-friendly GUI with full Input Validation

BONUS / ADVANCED FEATURES:
    - 4 switchable themes: Light, Dark, Ocean Blue, Solarized
    - Priority levels (High / Medium / Low) - color coded
    - Due Date field with overdue highlighting
    - Category / Tag field
    - Live search & filter, sort by Priority / Due / Name / Status / Manual
    - Progress bar + live statistics
    - Undo last delete (Ctrl+Z), keyboard shortcuts
    - Right-click context menu, double-click to toggle complete
    - Export tasks to a readable .txt report

EXTREME BONUS FEATURES:
    - Tabbed workspace: Tasks / Calendar / Analytics / Pomodoro
    - Subtasks (checklist) inside every task
    - Recurring tasks (Daily / Weekly / Monthly) - auto-regenerate on complete
    - Drag & drop manual reordering of tasks
    - Calendar view with due-date highlighting, click a day to see its tasks
    - Analytics dashboard with hand-drawn bar & pie charts (no dependencies)
    - Pomodoro focus timer linked to a task, with work/break cycles
    - Optional PIN lock screen to protect the app on shared computers
==============================================================================
"""

import json
import os
import hashlib
import calendar as cal_module
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Constants / file paths
# ---------------------------------------------------------------------------
DATA_FILE = "tasks.json"
SETTINGS_FILE = "app_settings.json"

PRIORITIES = ["High", "Medium", "Low"]
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
RECURRENCE_OPTIONS = ["None", "Daily", "Weekly", "Monthly"]
SORT_OPTIONS = ["Manual", "Priority", "Due Date", "Name (A-Z)", "Status"]

THEMES = {
    "Light": {
        "bg": "#f4f6f8", "fg": "#1e1e1e", "panel": "#ffffff",
        "accent": "#2d6cdf", "accent_fg": "#ffffff",
        "tree_bg": "#ffffff", "tree_fg": "#1e1e1e",
        "tree_sel": "#2d6cdf", "tree_sel_fg": "#ffffff", "entry_bg": "#ffffff",
        "done": "#8a8a8a", "high": "#d64545",
        "medium": "#c98a1f", "low": "#2f9e44",
        "overdue": "#ff5252", "grid": "#d8dde3", "canvas_bg": "#ffffff",
    },
    "Dark": {
        "bg": "#1e1f26", "fg": "#f0f0f0", "panel": "#2a2b33",
        "accent": "#5c8dff", "accent_fg": "#ffffff",
        "tree_bg": "#2a2b33", "tree_fg": "#f0f0f0",
        "tree_sel": "#5c8dff", "tree_sel_fg": "#ffffff", "entry_bg": "#33343d",
        "done": "#7d7d7d", "high": "#ff6b6b",
        "medium": "#f5b942", "low": "#4fd67a",
        "overdue": "#ff4444", "grid": "#3a3b45", "canvas_bg": "#2a2b33",
    },
    "Ocean Blue": {
        "bg": "#e6f2f8", "fg": "#0b2b3c", "panel": "#ffffff",
        "accent": "#0077b6", "accent_fg": "#ffffff",
        "tree_bg": "#ffffff", "tree_fg": "#0b2b3c",
        "tree_sel": "#0077b6", "tree_sel_fg": "#ffffff", "entry_bg": "#ffffff",
        "done": "#7a97a3", "high": "#e63946",
        "medium": "#f4a261", "low": "#2a9d8f",
        "overdue": "#e63946", "grid": "#cfe3ec", "canvas_bg": "#ffffff",
    },
    "Solarized": {
        "bg": "#fdf6e3", "fg": "#586e75", "panel": "#eee8d5",
        "accent": "#268bd2", "accent_fg": "#fdf6e3",
        "tree_bg": "#eee8d5", "tree_fg": "#586e75",
        "tree_sel": "#268bd2", "tree_sel_fg": "#fdf6e3", "entry_bg": "#fdf6e3",
        "done": "#93a1a1", "high": "#dc322f",
        "medium": "#b58900", "low": "#859900",
        "overdue": "#cb4b16", "grid": "#e4dcc4", "canvas_bg": "#eee8d5",
    },
}

DEFAULT_SETTINGS = {
    "theme": "Light",
    "pin_hash": None,
    "pomodoro_work_min": 25,
    "pomodoro_break_min": 5,
    "pomodoro_sessions_done": 0,
}


# =============================================================================
# Small reusable helpers
# =============================================================================
def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def add_interval(date_str: str, recurrence: str) -> str:
    """Given a YYYY-MM-DD date and a recurrence type, return the next date."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    if recurrence == "Daily":
        d = d + timedelta(days=1)
    elif recurrence == "Weekly":
        d = d + timedelta(weeks=1)
    elif recurrence == "Monthly":
        month = d.month + 1
        year = d.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        day = min(d.day, cal_module.monthrange(year, month)[1])
        d = d.replace(year=year, month=month, day=day)
    return d.strftime("%Y-%m-%d")


# =============================================================================
# Main Application
# =============================================================================
class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("To-Do List App - Week 05 (Extreme Advanced Edition)")
        self.root.geometry("1180x760")
        self.root.minsize(1000, 640)

        self.tasks = []
        self.undo_stack = []
        self.next_id = 1
        self.selected_index = None
        self.settings = dict(DEFAULT_SETTINGS)

        self.calendar_year = datetime.now().year
        self.calendar_month = datetime.now().month
        self.calendar_filter_day = None

        # Pomodoro state
        self.pomo_running = False
        self.pomo_mode = "Work"          # "Work" or "Break"
        self.pomo_seconds_left = 0
        self.pomo_after_id = None
        self.pomo_linked_task_id = None

        self.load_settings()
        self.load_tasks()
        self.current_theme = self.settings.get("theme", "Light")

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        # Show PIN lock first if configured, otherwise build straight away
        if self.settings.get("pin_hash"):
            self.build_lock_screen()
        else:
            self.build_main_app()

    # =========================================================================
    # PIN LOCK SCREEN
    # =========================================================================
    def build_lock_screen(self):
        self.lock_frame = tk.Frame(self.root)
        self.lock_frame.pack(fill="both", expand=True)

        t = THEMES[self.current_theme]
        self.lock_frame.configure(bg=t["bg"])

        card = tk.Frame(self.lock_frame, bg=t["panel"], bd=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=340, height=260)

        tk.Label(card, text="🔒", font=("Segoe UI", 36), bg=t["panel"], fg=t["fg"]).pack(pady=(24, 6))
        tk.Label(card, text="Enter PIN to unlock", font=("Segoe UI", 13, "bold"),
                 bg=t["panel"], fg=t["fg"]).pack(pady=(0, 14))

        self.pin_entry = tk.Entry(card, show="●", font=("Segoe UI", 16), justify="center", width=14)
        self.pin_entry.pack(pady=4)
        self.pin_entry.focus_set()
        self.pin_entry.bind("<Return>", lambda e: self.try_unlock())

        self.lock_error = tk.Label(card, text="", fg=t["overdue"], bg=t["panel"], font=("Segoe UI", 9))
        self.lock_error.pack(pady=(4, 4))

        tk.Button(card, text="Unlock", width=16, bg=t["accent"], fg=t["accent_fg"],
                  relief="flat", cursor="hand2", command=self.try_unlock).pack(pady=8)
        tk.Button(card, text="Forgot PIN? Reset", relief="flat", bg=t["panel"], fg=t["fg"],
                  cursor="hand2", command=self.reset_pin_from_lock).pack()

    def try_unlock(self):
        entered = self.pin_entry.get().strip()
        if hash_pin(entered) == self.settings.get("pin_hash"):
            self.lock_frame.destroy()
            self.build_main_app()
        else:
            self.lock_error.configure(text="Incorrect PIN. Try again.")
            self.pin_entry.delete(0, tk.END)

    def reset_pin_from_lock(self):
        confirm = messagebox.askyesno(
            "Reset PIN",
            "This will remove the PIN lock completely.\nDo you want to continue?"
        )
        if confirm:
            self.settings["pin_hash"] = None
            self.save_settings()
            self.lock_frame.destroy()
            self.build_main_app()

    # =========================================================================
    # MAIN APP BUILD
    # =========================================================================
    def build_main_app(self):
        self.build_top_bar()
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        self.tasks_tab = tk.Frame(self.notebook)
        self.calendar_tab = tk.Frame(self.notebook)
        self.analytics_tab = tk.Frame(self.notebook)
        self.pomodoro_tab = tk.Frame(self.notebook)

        self.notebook.add(self.tasks_tab, text="📋 Tasks")
        self.notebook.add(self.calendar_tab, text="📅 Calendar")
        self.notebook.add(self.analytics_tab, text="📊 Analytics")
        self.notebook.add(self.pomodoro_tab, text="⏱️ Pomodoro")

        self.build_tasks_tab()
        self.build_calendar_tab()
        self.build_analytics_tab()
        self.build_pomodoro_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # keyboard shortcuts
        self.root.bind("<Return>", self._on_enter_pressed)
        self.root.bind("<Delete>", lambda e: self.delete_task())
        self.root.bind("<Control-z>", lambda e: self.undo_delete())

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.apply_theme(self.current_theme)
        self.refresh_table()
        self.draw_calendar()

    def _on_enter_pressed(self, event):
        # Only trigger add-task shortcut while the Tasks tab is visible,
        # so Enter doesn't misfire from other tabs / dialogs.
        try:
            if self.notebook.index(self.notebook.select()) == 0:
                self.add_task()
        except Exception:
            pass

    # -------------------------------------------------------------------
    # TOP BAR (title, theme switcher, settings / PIN)
    # -------------------------------------------------------------------
    def build_top_bar(self):
        self.top_bar = tk.Frame(self.root)
        self.top_bar.pack(fill="x", padx=12, pady=(10, 0))

        self.title_label = tk.Label(
            self.top_bar, text="📝 My To-Do List — Extreme Edition", font=("Segoe UI", 18, "bold")
        )
        self.title_label.pack(side="left")

        right_frame = tk.Frame(self.top_bar)
        right_frame.pack(side="right")

        self.btn_settings = tk.Button(right_frame, text="⚙️ Settings", relief="flat",
                                       cursor="hand2", command=self.open_settings_dialog)
        self.btn_settings.pack(side="right", padx=(10, 0))

        self.theme_label = tk.Label(right_frame, text="Theme:", font=("Segoe UI", 10))
        self.theme_label.pack(side="left", padx=(0, 6))
        self.theme_var = tk.StringVar(value=self.current_theme)
        theme_menu = ttk.Combobox(
            right_frame, textvariable=self.theme_var, values=list(THEMES.keys()),
            state="readonly", width=12
        )
        theme_menu.pack(side="left")
        theme_menu.bind("<<ComboboxSelected>>", lambda e: self.apply_theme(self.theme_var.get()))

    def open_settings_dialog(self):
        t = THEMES[self.current_theme]
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("320x230")
        win.configure(bg=t["panel"])
        win.transient(self.root)
        win.grab_set()

        has_pin = bool(self.settings.get("pin_hash"))
        tk.Label(win, text="🔒 App Lock (PIN)", font=("Segoe UI", 12, "bold"),
                 bg=t["panel"], fg=t["fg"]).pack(pady=(16, 6))
        status_text = "PIN is currently ENABLED" if has_pin else "PIN is currently DISABLED"
        tk.Label(win, text=status_text, bg=t["panel"], fg=t["fg"]).pack(pady=(0, 12))

        def set_or_change_pin():
            new_pin = simpledialog.askstring("Set PIN", "Enter a new 4+ digit PIN:", show="●", parent=win)
            if new_pin is None:
                return
            if len(new_pin.strip()) < 4:
                messagebox.showwarning("Invalid PIN", "PIN must be at least 4 characters.", parent=win)
                return
            confirm_pin = simpledialog.askstring("Confirm PIN", "Re-enter the PIN to confirm:", show="●", parent=win)
            if confirm_pin != new_pin:
                messagebox.showwarning("Mismatch", "PINs did not match. Try again.", parent=win)
                return
            self.settings["pin_hash"] = hash_pin(new_pin.strip())
            self.save_settings()
            messagebox.showinfo("Saved", "PIN has been set successfully.", parent=win)
            win.destroy()

        def remove_pin():
            if not has_pin:
                return
            confirm = messagebox.askyesno("Remove PIN", "Remove the current PIN lock?", parent=win)
            if confirm:
                self.settings["pin_hash"] = None
                self.save_settings()
                messagebox.showinfo("Removed", "PIN lock has been disabled.", parent=win)
                win.destroy()

        tk.Button(win, text="Set / Change PIN", width=22, bg=t["accent"], fg=t["accent_fg"],
                  relief="flat", cursor="hand2", command=set_or_change_pin).pack(pady=4)
        tk.Button(win, text="Remove PIN", width=22, relief="flat", cursor="hand2",
                  command=remove_pin).pack(pady=4)
        tk.Button(win, text="Close", width=22, relief="flat", cursor="hand2",
                  command=win.destroy).pack(pady=(12, 4))

    # =========================================================================
    # TASKS TAB
    # =========================================================================
    def build_tasks_tab(self):
        parent = self.tasks_tab

        # ---- Input panel ----
        self.input_panel = tk.Frame(parent, bd=1, relief="groove")
        self.input_panel.pack(fill="x", padx=4, pady=10)
        pad = {"padx": 6, "pady": 8}

        tk.Label(self.input_panel, text="Task:").grid(row=0, column=0, sticky="w", **pad)
        self.task_entry = tk.Entry(self.input_panel, width=26)
        self.task_entry.grid(row=0, column=1, sticky="we", **pad)

        tk.Label(self.input_panel, text="Priority:").grid(row=0, column=2, sticky="w", **pad)
        self.priority_var = tk.StringVar(value="Medium")
        ttk.Combobox(self.input_panel, textvariable=self.priority_var, values=PRIORITIES,
                     state="readonly", width=9).grid(row=0, column=3, sticky="w", **pad)

        tk.Label(self.input_panel, text="Due (YYYY-MM-DD):").grid(row=0, column=4, sticky="w", **pad)
        self.due_entry = tk.Entry(self.input_panel, width=12)
        self.due_entry.grid(row=0, column=5, sticky="w", **pad)

        tk.Label(self.input_panel, text="Repeat:").grid(row=0, column=6, sticky="w", **pad)
        self.recurrence_var = tk.StringVar(value="None")
        ttk.Combobox(self.input_panel, textvariable=self.recurrence_var, values=RECURRENCE_OPTIONS,
                     state="readonly", width=9).grid(row=0, column=7, sticky="w", **pad)

        tk.Label(self.input_panel, text="Category:").grid(row=1, column=0, sticky="w", **pad)
        self.category_entry = tk.Entry(self.input_panel, width=26)
        self.category_entry.grid(row=1, column=1, sticky="we", **pad)

        btn_frame = tk.Frame(self.input_panel)
        btn_frame.grid(row=1, column=2, columnspan=6, sticky="e", **pad)

        self.btn_add = tk.Button(btn_frame, text="➕ Add Task", width=11, command=self.add_task)
        self.btn_add.grid(row=0, column=0, padx=3)
        self.btn_update = tk.Button(btn_frame, text="✏️ Update", width=10, command=self.update_task)
        self.btn_update.grid(row=0, column=1, padx=3)
        self.btn_complete = tk.Button(btn_frame, text="✅ Complete", width=11, command=self.toggle_complete)
        self.btn_complete.grid(row=0, column=2, padx=3)
        self.btn_subtasks = tk.Button(btn_frame, text="☑️ Subtasks", width=10, command=self.open_subtasks_dialog)
        self.btn_subtasks.grid(row=0, column=3, padx=3)
        self.btn_delete = tk.Button(btn_frame, text="🗑️ Delete", width=9, command=self.delete_task)
        self.btn_delete.grid(row=0, column=4, padx=3)
        self.btn_delete_all = tk.Button(btn_frame, text="🧹 Delete All", width=11, command=self.delete_all_tasks)
        self.btn_delete_all.grid(row=1, column=0, padx=3, pady=4)
        self.btn_undo = tk.Button(btn_frame, text="↩️ Undo", width=9, command=self.undo_delete)
        self.btn_undo.grid(row=1, column=1, padx=3, pady=4)
        self.btn_export = tk.Button(btn_frame, text="📤 Export", width=9, command=self.export_tasks)
        self.btn_export.grid(row=1, column=2, padx=3, pady=4)
        self.btn_clear_form = tk.Button(btn_frame, text="🔄 Clear", width=9, command=self.clear_form)
        self.btn_clear_form.grid(row=1, column=3, padx=3, pady=4)
        self.btn_clear_filter = tk.Button(btn_frame, text="✖ Day Filter", width=10, command=self.clear_day_filter)
        self.btn_clear_filter.grid(row=1, column=4, padx=3, pady=4)

        self.input_panel.columnconfigure(1, weight=1)

        # ---- Search + sort/filter bar ----
        search_frame = tk.Frame(parent)
        search_frame.pack(fill="x", padx=4)

        tk.Label(search_frame, text="🔍 Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_table())
        tk.Entry(search_frame, textvariable=self.search_var, width=26).pack(side="left", padx=(4, 20))

        tk.Label(search_frame, text="Sort by:").pack(side="left")
        self.sort_var = tk.StringVar(value="Manual")
        sort_box = ttk.Combobox(search_frame, textvariable=self.sort_var, values=SORT_OPTIONS,
                                 state="readonly", width=13)
        sort_box.pack(side="left", padx=6)
        sort_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())

        self.filter_var = tk.StringVar(value="All")
        filter_box = ttk.Combobox(search_frame, textvariable=self.filter_var,
                                   values=["All", "Pending", "Completed"], state="readonly", width=11)
        filter_box.pack(side="left", padx=6)
        filter_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())

        self.day_filter_label = tk.Label(search_frame, text="", font=("Segoe UI", 9, "italic"))
        self.day_filter_label.pack(side="left", padx=10)

        tk.Label(search_frame, text="(Drag rows to reorder — works in Manual sort)",
                 font=("Segoe UI", 8, "italic")).pack(side="right")

        # ---- Table ----
        table_frame = tk.Frame(parent)
        table_frame.pack(fill="both", expand=True, padx=4, pady=10)

        columns = ("status", "task", "priority", "due", "repeat", "sub", "category")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headers = {"status": "Status", "task": "Task", "priority": "Priority", "due": "Due Date",
                   "repeat": "Repeat", "sub": "Subtasks", "category": "Category"}
        widths = {"status": 85, "task": 300, "priority": 80, "due": 100,
                  "repeat": 70, "sub": 75, "category": 130}
        for c in columns:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="center" if c != "task" else "w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)
        self.tree.bind("<Double-1>", lambda e: self.toggle_complete())
        self.tree.bind("<Button-3>", self.show_context_menu)

        # drag-to-reorder
        self._drag_start_index = None
        self.tree.bind("<ButtonPress-1>", self.on_drag_start, add="+")
        self.tree.bind("<B1-Motion>", self.on_drag_motion, add="+")
        self.tree.bind("<ButtonRelease-1>", self.on_drag_release, add="+")

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="✅ Toggle Complete", command=self.toggle_complete)
        self.context_menu.add_command(label="✏️ Load for Edit", command=self.load_selected_into_form)
        self.context_menu.add_command(label="☑️ Subtasks", command=self.open_subtasks_dialog)
        self.context_menu.add_command(label="⏱️ Focus with Pomodoro", command=self.link_selected_to_pomodoro)
        self.context_menu.add_command(label="🗑️ Delete", command=self.delete_task)

        # ---- Bottom bar ----
        bottom = tk.Frame(parent)
        bottom.pack(fill="x", padx=4, pady=(0, 4))
        self.progress = ttk.Progressbar(bottom, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(side="left")
        self.stats_label = tk.Label(bottom, text="", font=("Segoe UI", 10))
        self.stats_label.pack(side="left", padx=15)

    # -------------------------------------------------------------------
    # Drag & drop reordering
    # -------------------------------------------------------------------
    def on_drag_start(self, event):
        row_id = self.tree.identify_row(event.y)
        self._drag_start_index = self.tree.index(row_id) if row_id else None

    def on_drag_motion(self, event):
        if self._drag_start_index is None:
            return
        if self.sort_var.get() != "Manual" or self.filter_var.get() != "All" or self.search_var.get().strip():
            return  # only allow reordering in a clean, unsorted, unfiltered manual view
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        target_index = self.tree.index(row_id)
        if target_index != self._drag_start_index:
            self.tree.move(row_id, "", target_index)
            self._drag_start_index = target_index

    def on_drag_release(self, event):
        if self._drag_start_index is None:
            return
        if self.sort_var.get() == "Manual" and self.filter_var.get() == "All" and not self.search_var.get().strip():
            # persist the new visual order back into self.tasks / "order" field
            new_order_ids = [self.tree.item(row, "tags")[0] for row in self.tree.get_children()]
            id_to_task = {str(t["id"]): t for t in self.tasks}
            reordered = [id_to_task[i] for i in new_order_ids if i in id_to_task]
            # append anything not currently visible (shouldn't happen in clean view)
            visible_ids = set(new_order_ids)
            for t in self.tasks:
                if str(t["id"]) not in visible_ids:
                    reordered.append(t)
            for idx, t in enumerate(reordered):
                t["order"] = idx
            self.tasks = reordered
            self.save_tasks()
        self._drag_start_index = None
        self.refresh_table()

    # -------------------------------------------------------------------
    # Subtasks dialog
    # -------------------------------------------------------------------
    def open_subtasks_dialog(self):
        if self.selected_index is None:
            messagebox.showinfo("No Selection", "Please select a task first.")
            return
        task = self.tasks[self.selected_index]
        task.setdefault("subtasks", [])

        t = THEMES[self.current_theme]
        win = tk.Toplevel(self.root)
        win.title(f"Subtasks — {task['title']}")
        win.geometry("380x420")
        win.configure(bg=t["panel"])
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=f"☑️ Subtasks for: {task['title']}", font=("Segoe UI", 11, "bold"),
                 bg=t["panel"], fg=t["fg"], wraplength=340, justify="left").pack(pady=(14, 10), padx=10)

        list_frame = tk.Frame(win, bg=t["panel"])
        list_frame.pack(fill="both", expand=True, padx=14)

        check_vars = []

        def render_subtasks():
            for w in list_frame.winfo_children():
                w.destroy()
            check_vars.clear()
            if not task["subtasks"]:
                tk.Label(list_frame, text="No subtasks yet. Add one below.",
                         bg=t["panel"], fg=t["fg"]).pack(pady=8)
            for i, sub in enumerate(task["subtasks"]):
                row = tk.Frame(list_frame, bg=t["panel"])
                row.pack(fill="x", pady=2)
                var = tk.BooleanVar(value=sub["done"])

                def make_toggle(idx=i, v=var):
                    def _toggle():
                        task["subtasks"][idx]["done"] = v.get()
                        self.save_tasks()
                        self.refresh_table()
                    return _toggle

                cb = tk.Checkbutton(row, variable=var, bg=t["panel"], activebackground=t["panel"],
                                     command=make_toggle())
                cb.pack(side="left")
                check_vars.append(var)
                label_text = sub["text"]
                lbl = tk.Label(row, text=label_text, bg=t["panel"], fg=t["fg"], anchor="w",
                                wraplength=230, justify="left")
                lbl.pack(side="left", fill="x", expand=True)

                def make_delete(idx=i):
                    def _delete():
                        del task["subtasks"][idx]
                        self.save_tasks()
                        render_subtasks()
                        self.refresh_table()
                    return _delete

                tk.Button(row, text="✖", relief="flat", fg=t["overdue"], bg=t["panel"],
                          cursor="hand2", command=make_delete()).pack(side="right")

        render_subtasks()

        add_frame = tk.Frame(win, bg=t["panel"])
        add_frame.pack(fill="x", padx=14, pady=(10, 14))
        new_sub_entry = tk.Entry(add_frame, width=26)
        new_sub_entry.pack(side="left", fill="x", expand=True)

        def add_subtask():
            text = new_sub_entry.get().strip()
            if not text:
                messagebox.showwarning("Input Error", "Subtask text cannot be empty!", parent=win)
                return
            task["subtasks"].append({"text": text, "done": False})
            new_sub_entry.delete(0, tk.END)
            self.save_tasks()
            render_subtasks()
            self.refresh_table()

        new_sub_entry.bind("<Return>", lambda e: add_subtask())
        tk.Button(add_frame, text="Add", bg=t["accent"], fg=t["accent_fg"], relief="flat",
                  cursor="hand2", command=add_subtask).pack(side="left", padx=(6, 0))

        tk.Button(win, text="Close", relief="flat", cursor="hand2",
                  command=lambda: (win.destroy(), self.refresh_table())).pack(pady=(0, 12))

    # =========================================================================
    # THEME HANDLING
    # =========================================================================
    def apply_theme(self, theme_name):
        t = THEMES[theme_name]
        self.current_theme = theme_name
        self.settings["theme"] = theme_name
        self.save_settings()

        self.root.configure(bg=t["bg"])
        self.top_bar.configure(bg=t["bg"])
        self.title_label.configure(bg=t["bg"], fg=t["fg"])
        self.theme_label.configure(bg=t["bg"], fg=t["fg"])
        self.btn_settings.configure(bg=t["bg"], fg=t["fg"], activebackground=t["panel"])
        self.input_panel.configure(bg=t["panel"])

        for widget in self.input_panel.winfo_children():
            self._style_widget(widget, t)

        for tab in (self.tasks_tab, self.calendar_tab, self.analytics_tab, self.pomodoro_tab):
            tab.configure(bg=t["bg"])

        self.style.configure("Treeview", background=t["tree_bg"], fieldbackground=t["tree_bg"],
                              foreground=t["tree_fg"], rowheight=26)
        self.style.map("Treeview", background=[("selected", t["tree_sel"])],
                        foreground=[("selected", t["tree_sel_fg"])])
        self.style.configure("Treeview.Heading", background=t["accent"], foreground=t["accent_fg"],
                              font=("Segoe UI", 9, "bold"))
        self.style.configure("TNotebook.Tab", padding=(12, 6))

        for btn in (self.btn_add, self.btn_update, self.btn_complete, self.btn_subtasks,
                    self.btn_delete, self.btn_delete_all, self.btn_undo, self.btn_export,
                    self.btn_clear_form, self.btn_clear_filter):
            btn.configure(bg=t["accent"], fg=t["accent_fg"], activebackground=t["accent"],
                          relief="flat", cursor="hand2")

        self.stats_label.configure(bg=self.root["bg"], fg=t["fg"])
        self.day_filter_label.configure(bg=self.root["bg"], fg=t["accent"])

        self._style_recursive(self.calendar_tab, t)
        self._style_recursive(self.pomodoro_tab, t)

        self.refresh_table()
        self.draw_calendar()
        self.draw_analytics()
        self._style_pomodoro_theme(t)

    def _style_widget(self, widget, t):
        cls = widget.winfo_class()
        try:
            if cls == "Frame":
                widget.configure(bg=t["panel"])
                for child in widget.winfo_children():
                    self._style_widget(child, t)
            elif cls == "Label":
                widget.configure(bg=t["panel"], fg=t["fg"])
            elif cls == "Entry":
                widget.configure(bg=t["entry_bg"], fg=t["fg"], insertbackground=t["fg"])
        except tk.TclError:
            pass

    def _style_recursive(self, widget, t):
        cls = widget.winfo_class()
        try:
            if cls == "Frame":
                widget.configure(bg=t["bg"])
            elif cls == "Label":
                widget.configure(bg=t["bg"], fg=t["fg"])
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._style_recursive(child, t)

    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================
    def add_task(self):
        title = self.task_entry.get().strip()
        priority = self.priority_var.get()
        due = self.due_entry.get().strip()
        category = self.category_entry.get().strip()
        recurrence = self.recurrence_var.get()

        if not title:
            messagebox.showwarning("Input Error", "Task name cannot be empty!\nPlease enter a task.")
            return
        if due and not is_valid_date(due):
            messagebox.showwarning("Input Error", "Invalid due date format.\nPlease use YYYY-MM-DD (e.g. 2026-08-30).")
            return
        if recurrence != "None" and not due:
            messagebox.showwarning("Input Error", "A recurring task needs a due date to repeat from.")
            return

        task = {
            "id": self.next_id,
            "title": title,
            "priority": priority,
            "due": due,
            "category": category if category else "General",
            "done": False,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "order": len(self.tasks),
            "recurrence": recurrence,
            "subtasks": [],
        }
        self.next_id += 1
        self.tasks.append(task)
        self.save_tasks()
        self.clear_form()
        self.refresh_table()
        self.draw_calendar()
        self.draw_analytics()

    def update_task(self):
        if self.selected_index is None:
            messagebox.showinfo("No Selection", "Please select a task from the table first to update it.")
            return

        title = self.task_entry.get().strip()
        due = self.due_entry.get().strip()
        recurrence = self.recurrence_var.get()

        if not title:
            messagebox.showwarning("Input Error", "Task name cannot be empty!")
            return
        if due and not is_valid_date(due):
            messagebox.showwarning("Input Error", "Invalid due date format. Please use YYYY-MM-DD.")
            return
        if recurrence != "None" and not due:
            messagebox.showwarning("Input Error", "A recurring task needs a due date to repeat from.")
            return

        task = self.tasks[self.selected_index]
        task["title"] = title
        task["priority"] = self.priority_var.get()
        task["due"] = due
        task["category"] = self.category_entry.get().strip() or "General"
        task["recurrence"] = recurrence

        self.save_tasks()
        self.clear_form()
        self.refresh_table()
        self.draw_calendar()
        self.draw_analytics()
        messagebox.showinfo("Updated", "Task updated successfully!")

    def delete_task(self):
        if self.selected_index is None:
            messagebox.showinfo("No Selection", "Please select a task first to delete it.")
            return

        task = self.tasks[self.selected_index]
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{task['title']}'?")
        if not confirm:
            return

        self.undo_stack.append((self.selected_index, task))
        del self.tasks[self.selected_index]
        self.selected_index = None
        self.save_tasks()
        self.clear_form()
        self.refresh_table()
        self.draw_calendar()
        self.draw_analytics()

    def delete_all_tasks(self):
        if not self.tasks:
            messagebox.showinfo("Empty", "The list is already empty.")
            return
        confirm = messagebox.askyesno("Confirm Delete All", "Are you sure you want to delete ALL tasks?\nThis bulk action cannot be undone.")
        if confirm:
            self.tasks.clear()
            self.undo_stack.clear()
            self.save_tasks()
            self.refresh_table()
            self.draw_calendar()
            self.draw_analytics()

    def toggle_complete(self):
        if self.selected_index is None:
            messagebox.showinfo("No Selection", "Please select a task first.")
            return
        task = self.tasks[self.selected_index]
        task["done"] = not task["done"]

        # if a recurring task was just marked complete, spawn the next occurrence
        if task["done"] and task.get("recurrence", "None") != "None" and task.get("due"):
            next_due = add_interval(task["due"], task["recurrence"])
            new_task = {
                "id": self.next_id,
                "title": task["title"],
                "priority": task["priority"],
                "due": next_due,
                "category": task["category"],
                "done": False,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "order": len(self.tasks),
                "recurrence": task["recurrence"],
                "subtasks": [{"text": s["text"], "done": False} for s in task.get("subtasks", [])],
            }
            self.next_id += 1
            self.tasks.append(new_task)
            messagebox.showinfo("Recurring Task", f"Nice work! Next occurrence created for {next_due}.")

        self.save_tasks()
        self.refresh_table()
        self.draw_calendar()
        self.draw_analytics()

    def undo_delete(self):
        if not self.undo_stack:
            messagebox.showinfo("Nothing to Undo", "There is nothing to undo.")
            return
        index, task = self.undo_stack.pop()
        index = min(index, len(self.tasks))
        self.tasks.insert(index, task)
        self.save_tasks()
        self.refresh_table()
        self.draw_calendar()
        self.draw_analytics()

    def link_selected_to_pomodoro(self):
        if self.selected_index is None:
            messagebox.showinfo("No Selection", "Please select a task first.")
            return
        task = self.tasks[self.selected_index]
        self.pomo_linked_task_id = task["id"]
        self.pomo_task_var.set(task["title"])
        self.notebook.select(self.pomodoro_tab)

    # -------------------------------------------------------------------
    # Selection / form helpers
    # -------------------------------------------------------------------
    def on_row_select(self, event):
        selection = self.tree.selection()
        if not selection:
            self.selected_index = None
            return
        item_id = selection[0]
        task_id = self.tree.item(item_id, "tags")[0]
        for i, t in enumerate(self.tasks):
            if str(t["id"]) == task_id:
                self.selected_index = i
                return
        self.selected_index = None

    def load_selected_into_form(self):
        if self.selected_index is None:
            return
        task = self.tasks[self.selected_index]
        self.clear_form(keep_selection=True)
        self.task_entry.insert(0, task["title"])
        self.priority_var.set(task["priority"])
        self.due_entry.insert(0, task["due"])
        self.category_entry.insert(0, task["category"])
        self.recurrence_var.set(task.get("recurrence", "None"))

    def clear_form(self, keep_selection=False):
        self.task_entry.delete(0, tk.END)
        self.due_entry.delete(0, tk.END)
        self.category_entry.delete(0, tk.END)
        self.priority_var.set("Medium")
        self.recurrence_var.set("None")
        if not keep_selection:
            self.selected_index = None

    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.on_row_select(None)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def clear_day_filter(self):
        self.calendar_filter_day = None
        self.day_filter_label.configure(text="")
        self.refresh_table()

    # =========================================================================
    # TABLE REFRESH / SEARCH / SORT / FILTER
    # =========================================================================
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        t = THEMES[self.current_theme]
        search_term = self.search_var.get().lower().strip()
        filter_mode = self.filter_var.get()
        sort_mode = self.sort_var.get()

        indexed_tasks = list(enumerate(self.tasks))

        if search_term:
            indexed_tasks = [
                (i, tk_) for i, tk_ in indexed_tasks
                if search_term in tk_["title"].lower() or search_term in tk_["category"].lower()
            ]

        if filter_mode == "Pending":
            indexed_tasks = [(i, tk_) for i, tk_ in indexed_tasks if not tk_["done"]]
        elif filter_mode == "Completed":
            indexed_tasks = [(i, tk_) for i, tk_ in indexed_tasks if tk_["done"]]

        if self.calendar_filter_day:
            indexed_tasks = [(i, tk_) for i, tk_ in indexed_tasks if tk_["due"] == self.calendar_filter_day]

        if sort_mode == "Priority":
            indexed_tasks.sort(key=lambda x: PRIORITY_ORDER.get(x[1]["priority"], 3))
        elif sort_mode == "Due Date":
            indexed_tasks.sort(key=lambda x: x[1]["due"] or "9999-99-99")
        elif sort_mode == "Name (A-Z)":
            indexed_tasks.sort(key=lambda x: x[1]["title"].lower())
        elif sort_mode == "Status":
            indexed_tasks.sort(key=lambda x: x[1]["done"])
        elif sort_mode == "Manual":
            indexed_tasks.sort(key=lambda x: x[1].get("order", 0))

        today = today_str()

        self.tree.tag_configure("done", foreground=t["done"])
        self.tree.tag_configure("high", foreground=t["high"])
        self.tree.tag_configure("medium", foreground=t["medium"])
        self.tree.tag_configure("low", foreground=t["low"])
        self.tree.tag_configure("overdue", foreground=t["overdue"])

        for original_index, task in indexed_tasks:
            status = "✅ Done" if task["done"] else "⏳ Pending"
            is_overdue = (not task["done"] and task["due"] and task["due"] < today)

            if task["done"]:
                tag = "done"
            elif is_overdue:
                tag = "overdue"
            else:
                tag = task["priority"].lower()

            subtasks = task.get("subtasks", [])
            sub_text = f"{sum(1 for s in subtasks if s['done'])}/{len(subtasks)}" if subtasks else "-"
            recurrence = task.get("recurrence", "None")
            repeat_text = "🔁" if recurrence != "None" else "-"

            self.tree.insert(
                "", "end",
                values=(status, task["title"], task["priority"],
                        task["due"] if task["due"] else "-", repeat_text, sub_text, task["category"]),
                tags=(str(task["id"]), tag)
            )

        self.update_stats()

    def update_stats(self):
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t["done"])
        pending = total - completed
        percent = int((completed / total) * 100) if total else 0

        self.progress["value"] = percent
        self.stats_label.configure(
            text=f"Total: {total}   |   ✅ Completed: {completed}   |   ⏳ Pending: {pending}   |   Progress: {percent}%"
        )

    def on_tab_changed(self, event):
        idx = self.notebook.index(self.notebook.select())
        if idx == 1:
            self.draw_calendar()
        elif idx == 2:
            self.draw_analytics()

    # =========================================================================
    # CALENDAR TAB
    # =========================================================================
    def build_calendar_tab(self):
        parent = self.calendar_tab

        nav = tk.Frame(parent)
        nav.pack(fill="x", pady=(14, 6))
        tk.Button(nav, text="◀ Prev", command=self.calendar_prev_month, relief="flat",
                  cursor="hand2").pack(side="left", padx=10)
        self.calendar_title_label = tk.Label(nav, text="", font=("Segoe UI", 14, "bold"))
        self.calendar_title_label.pack(side="left", expand=True)
        tk.Button(nav, text="Next ▶", command=self.calendar_next_month, relief="flat",
                  cursor="hand2").pack(side="right", padx=10)
        tk.Button(nav, text="Today", command=self.calendar_go_today, relief="flat",
                  cursor="hand2").pack(side="right", padx=4)

        self.calendar_grid_frame = tk.Frame(parent)
        self.calendar_grid_frame.pack(fill="both", expand=True, padx=14, pady=10)

        hint = tk.Label(parent, text="Click a day with due tasks to filter the Tasks tab by that date.",
                         font=("Segoe UI", 9, "italic"))
        hint.pack(pady=(0, 10))

    def calendar_prev_month(self):
        self.calendar_month -= 1
        if self.calendar_month < 1:
            self.calendar_month = 12
            self.calendar_year -= 1
        self.draw_calendar()

    def calendar_next_month(self):
        self.calendar_month += 1
        if self.calendar_month > 12:
            self.calendar_month = 1
            self.calendar_year += 1
        self.draw_calendar()

    def calendar_go_today(self):
        now = datetime.now()
        self.calendar_year, self.calendar_month = now.year, now.month
        self.draw_calendar()

    def draw_calendar(self):
        if not hasattr(self, "calendar_grid_frame"):
            return
        for w in self.calendar_grid_frame.winfo_children():
            w.destroy()

        t = THEMES[self.current_theme]
        self.calendar_grid_frame.configure(bg=t["bg"])
        self.calendar_title_label.configure(
            text=f"{cal_module.month_name[self.calendar_month]} {self.calendar_year}", bg=t["bg"], fg=t["fg"]
        )

        due_map = {}
        for task in self.tasks:
            if task["due"]:
                due_map.setdefault(task["due"], []).append(task)

        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for col, wd in enumerate(weekdays):
            tk.Label(self.calendar_grid_frame, text=wd, font=("Segoe UI", 10, "bold"),
                     bg=t["accent"], fg=t["accent_fg"], width=14, pady=6).grid(row=0, column=col, sticky="nsew", padx=1, pady=1)

        cal_module.setfirstweekday(cal_module.MONDAY)
        month_days = cal_module.monthcalendar(self.calendar_year, self.calendar_month)
        today = today_str()

        for r, week in enumerate(month_days, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    tk.Frame(self.calendar_grid_frame, bg=t["bg"]).grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                    continue
                date_str = f"{self.calendar_year:04d}-{self.calendar_month:02d}-{day:02d}"
                day_tasks = due_map.get(date_str, [])
                is_today = (date_str == today)

                cell_bg = t["panel"]
                if is_today:
                    cell_bg = t["accent"]
                elif day_tasks:
                    cell_bg = t["grid"]

                cell = tk.Frame(self.calendar_grid_frame, bg=cell_bg, bd=1, relief="ridge")
                cell.grid(row=r, column=c, sticky="nsew", padx=1, pady=1, ipady=6)

                fg_color = t["accent_fg"] if is_today else t["fg"]
                day_label = tk.Label(cell, text=str(day), bg=cell_bg, fg=fg_color, font=("Segoe UI", 10, "bold"))
                day_label.pack(anchor="nw", padx=4)

                if day_tasks:
                    pending_n = sum(1 for x in day_tasks if not x["done"])
                    done_n = len(day_tasks) - pending_n
                    summary = f"{pending_n} due" if pending_n else f"{done_n} done"
                    info_label = tk.Label(cell, text=summary, bg=cell_bg,
                                           fg=t["overdue"] if pending_n and date_str < today else t["fg"],
                                           font=("Segoe UI", 8))
                    info_label.pack(anchor="w", padx=4)

                    for widget in (cell, day_label, info_label):
                        widget.bind("<Button-1>", lambda e, d=date_str: self.on_calendar_day_click(d))
                        widget.configure(cursor="hand2")
                else:
                    day_label.bind("<Button-1>", lambda e, d=date_str: self.on_calendar_day_click(d))
                    day_label.configure(cursor="hand2")

        for c in range(7):
            self.calendar_grid_frame.columnconfigure(c, weight=1)
        for r in range(len(month_days) + 1):
            self.calendar_grid_frame.rowconfigure(r, weight=1)

    def on_calendar_day_click(self, date_str):
        self.calendar_filter_day = date_str
        self.day_filter_label.configure(text=f"📅 Filtered to: {date_str}")
        self.notebook.select(self.tasks_tab)
        self.refresh_table()

    # =========================================================================
    # ANALYTICS TAB
    # =========================================================================
    def build_analytics_tab(self):
        parent = self.analytics_tab

        top_row = tk.Frame(parent)
        top_row.pack(fill="x", pady=(14, 4), padx=14)
        self.analytics_summary_label = tk.Label(top_row, text="", font=("Segoe UI", 10), justify="left")
        self.analytics_summary_label.pack(side="left")
        tk.Button(top_row, text="🔄 Refresh", relief="flat", cursor="hand2",
                  command=self.draw_analytics).pack(side="right")

        charts_row = tk.Frame(parent)
        charts_row.pack(fill="both", expand=True, padx=14, pady=10)

        left_box = tk.Frame(charts_row)
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(left_box, text="Tasks by Priority", font=("Segoe UI", 11, "bold")).pack()
        self.priority_canvas = tk.Canvas(left_box, height=260, highlightthickness=0)
        self.priority_canvas.pack(fill="both", expand=True, pady=6)

        mid_box = tk.Frame(charts_row)
        mid_box.pack(side="left", fill="both", expand=True, padx=8)
        tk.Label(mid_box, text="Completion Status", font=("Segoe UI", 11, "bold")).pack()
        self.status_canvas = tk.Canvas(mid_box, height=260, highlightthickness=0)
        self.status_canvas.pack(fill="both", expand=True, pady=6)

        right_box = tk.Frame(charts_row)
        right_box.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(right_box, text="Tasks by Category", font=("Segoe UI", 11, "bold")).pack()
        self.category_canvas = tk.Canvas(right_box, height=260, highlightthickness=0)
        self.category_canvas.pack(fill="both", expand=True, pady=6)

        self.analytics_frames = [left_box, mid_box, right_box, charts_row]

    def draw_analytics(self):
        if not hasattr(self, "priority_canvas"):
            return
        t = THEMES[self.current_theme]
        for fr in self.analytics_frames:
            fr.configure(bg=t["bg"])
        for w in self.analytics_frames:
            for child in w.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=t["bg"], fg=t["fg"])
        self.analytics_summary_label.configure(bg=t["bg"], fg=t["fg"])

        total = len(self.tasks)
        completed = sum(1 for x in self.tasks if x["done"])
        pending = total - completed
        today = today_str()
        overdue = sum(1 for x in self.tasks if not x["done"] and x["due"] and x["due"] < today)
        rate = int((completed / total) * 100) if total else 0

        self.analytics_summary_label.configure(
            text=(f"Total tasks: {total}    Completed: {completed}    Pending: {pending}    "
                  f"Overdue: {overdue}    Completion rate: {rate}%")
        )

        # ---- Priority bar chart ----
        self._draw_bar_chart(
            self.priority_canvas, t,
            labels=PRIORITIES,
            values=[sum(1 for x in self.tasks if x["priority"] == p and not x["done"]) for p in PRIORITIES],
            colors=[t["high"], t["medium"], t["low"]],
        )

        # ---- Completion status pie chart ----
        self._draw_pie_chart(
            self.status_canvas, t,
            segments=[("Completed", completed, t["low"]), ("Pending", pending, t["accent"])],
        )

        # ---- Category bar chart ----
        cat_counts = {}
        for x in self.tasks:
            cat_counts[x["category"]] = cat_counts.get(x["category"], 0) + 1
        cats = list(cat_counts.keys())[:6]  # cap to keep it readable
        self._draw_bar_chart(
            self.category_canvas, t,
            labels=cats,
            values=[cat_counts[c] for c in cats],
            colors=[t["accent"]] * len(cats),
        )

    def _draw_bar_chart(self, canvas, t, labels, values, colors):
        canvas.delete("all")
        canvas.configure(bg=t["canvas_bg"])
        canvas.update_idletasks()
        w = max(canvas.winfo_width(), 200)
        h = max(canvas.winfo_height(), 200)

        if not labels or all(v == 0 for v in values):
            canvas.create_text(w / 2, h / 2, text="No data yet", fill=t["fg"], font=("Segoe UI", 10))
            return

        max_val = max(values) if max(values) > 0 else 1
        margin_bottom = 34
        margin_top = 16
        chart_h = h - margin_bottom - margin_top
        n = len(labels)
        bar_area_w = w / n

        for i, (label, val, color) in enumerate(zip(labels, values, colors)):
            bar_w = bar_area_w * 0.5
            x0 = i * bar_area_w + (bar_area_w - bar_w) / 2
            x1 = x0 + bar_w
            bar_h = (val / max_val) * chart_h if max_val else 0
            y1 = h - margin_bottom
            y0 = y1 - bar_h
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            canvas.create_text((x0 + x1) / 2, y0 - 10, text=str(val), fill=t["fg"], font=("Segoe UI", 9, "bold"))
            canvas.create_text((x0 + x1) / 2, h - margin_bottom + 14, text=label, fill=t["fg"],
                                font=("Segoe UI", 8), width=bar_area_w)

    def _draw_pie_chart(self, canvas, t, segments):
        canvas.delete("all")
        canvas.configure(bg=t["canvas_bg"])
        canvas.update_idletasks()
        w = max(canvas.winfo_width(), 200)
        h = max(canvas.winfo_height(), 200)

        total = sum(v for _, v, _ in segments)
        size = min(w, h) - 70
        x0 = (w - size) / 2
        y0 = 20
        x1, y1 = x0 + size, y0 + size

        if total == 0:
            canvas.create_oval(x0, y0, x1, y1, outline=t["fg"])
            canvas.create_text(w / 2, h / 2, text="No data yet", fill=t["fg"], font=("Segoe UI", 10))
            return

        start = 0
        for label, val, color in segments:
            extent = 360 * (val / total)
            if extent > 0:
                canvas.create_arc(x0, y0, x1, y1, start=start, extent=extent, fill=color, outline=t["canvas_bg"])
            start += extent

        legend_y = y1 + 16
        legend_x = 14
        for label, val, color in segments:
            canvas.create_rectangle(legend_x, legend_y, legend_x + 12, legend_y + 12, fill=color, outline="")
            canvas.create_text(legend_x + 18, legend_y + 6, anchor="w", fill=t["fg"],
                                text=f"{label}: {val}", font=("Segoe UI", 9))
            legend_y += 18

    # =========================================================================
    # POMODORO TAB
    # =========================================================================
    def build_pomodoro_tab(self):
        parent = self.pomodoro_tab

        wrap = tk.Frame(parent)
        wrap.pack(expand=True)

        tk.Label(wrap, text="⏱️ Pomodoro Focus Timer", font=("Segoe UI", 16, "bold")).pack(pady=(30, 10))

        self.pomo_task_var = tk.StringVar(value="No task linked")
        tk.Label(wrap, textvariable=self.pomo_task_var, font=("Segoe UI", 10, "italic")).pack(pady=(0, 16))

        self.pomo_time_label = tk.Label(wrap, text="25:00", font=("Segoe UI", 48, "bold"))
        self.pomo_time_label.pack(pady=10)

        self.pomo_mode_label = tk.Label(wrap, text="Work Session", font=("Segoe UI", 12))
        self.pomo_mode_label.pack(pady=(0, 20))

        controls = tk.Frame(wrap)
        controls.pack(pady=10)
        self.btn_pomo_start = tk.Button(controls, text="▶ Start", width=10, command=self.pomo_start)
        self.btn_pomo_start.grid(row=0, column=0, padx=6)
        self.btn_pomo_pause = tk.Button(controls, text="⏸ Pause", width=10, command=self.pomo_pause)
        self.btn_pomo_pause.grid(row=0, column=1, padx=6)
        self.btn_pomo_reset = tk.Button(controls, text="⟲ Reset", width=10, command=self.pomo_reset)
        self.btn_pomo_reset.grid(row=0, column=2, padx=6)

        settings_row = tk.Frame(wrap)
        settings_row.pack(pady=20)
        tk.Label(settings_row, text="Work (min):").grid(row=0, column=0, padx=4)
        self.pomo_work_var = tk.IntVar(value=self.settings.get("pomodoro_work_min", 25))
        tk.Spinbox(settings_row, from_=1, to=90, width=5, textvariable=self.pomo_work_var,
                   command=self.pomo_settings_changed).grid(row=0, column=1, padx=4)
        tk.Label(settings_row, text="Break (min):").grid(row=0, column=2, padx=4)
        self.pomo_break_var = tk.IntVar(value=self.settings.get("pomodoro_break_min", 5))
        tk.Spinbox(settings_row, from_=1, to=30, width=5, textvariable=self.pomo_break_var,
                   command=self.pomo_settings_changed).grid(row=0, column=3, padx=4)

        self.pomo_sessions_label = tk.Label(
            wrap, text=f"Sessions completed today: {self.settings.get('pomodoro_sessions_done', 0)}",
            font=("Segoe UI", 9)
        )
        self.pomo_sessions_label.pack(pady=(6, 0))

        self.pomo_widgets = [wrap, controls, settings_row]
        self.pomo_seconds_left = self.pomo_work_var.get() * 60
        self.update_pomo_display()

    def pomo_settings_changed(self):
        self.settings["pomodoro_work_min"] = self.pomo_work_var.get()
        self.settings["pomodoro_break_min"] = self.pomo_break_var.get()
        self.save_settings()
        if not self.pomo_running:
            self.pomo_reset()

    def _style_pomodoro_theme(self, t):
        if not hasattr(self, "pomo_widgets"):
            return
        for w in self.pomo_widgets:
            self._style_recursive(w, t)
        self.pomo_time_label.configure(bg=t["bg"], fg=t["accent"])
        self.pomo_mode_label.configure(bg=t["bg"], fg=t["fg"])
        self.pomo_task_var_label_fix(t)
        for btn in (self.btn_pomo_start, self.btn_pomo_pause, self.btn_pomo_reset):
            btn.configure(bg=t["accent"], fg=t["accent_fg"], relief="flat", cursor="hand2")
        self.pomo_sessions_label.configure(bg=t["bg"], fg=t["fg"])

    def pomo_task_var_label_fix(self, t):
        # the StringVar label needs its own restyle since it's created before theme apply
        for child in self.pomodoro_tab.winfo_children():
            pass  # styling handled generically via _style_recursive

    def pomo_start(self):
        if self.pomo_running:
            return
        self.pomo_running = True
        self._pomo_tick()

    def pomo_pause(self):
        self.pomo_running = False
        if self.pomo_after_id:
            self.root.after_cancel(self.pomo_after_id)
            self.pomo_after_id = None

    def pomo_reset(self):
        self.pomo_pause()
        self.pomo_mode = "Work"
        self.pomo_seconds_left = self.pomo_work_var.get() * 60
        self.update_pomo_display()

    def _pomo_tick(self):
        if not self.pomo_running:
            return
        if self.pomo_seconds_left <= 0:
            self._pomo_session_complete()
            return
        self.pomo_seconds_left -= 1
        self.update_pomo_display()
        self.pomo_after_id = self.root.after(1000, self._pomo_tick)

    def _pomo_session_complete(self):
        self.root.bell()
        if self.pomo_mode == "Work":
            self.settings["pomodoro_sessions_done"] = self.settings.get("pomodoro_sessions_done", 0) + 1
            self.save_settings()
            self.pomo_sessions_label.configure(
                text=f"Sessions completed today: {self.settings['pomodoro_sessions_done']}"
            )
            messagebox.showinfo("Pomodoro", "Work session complete! Time for a short break.")
            self.pomo_mode = "Break"
            self.pomo_seconds_left = self.pomo_break_var.get() * 60
        else:
            messagebox.showinfo("Pomodoro", "Break's over! Ready for another focused session?")
            self.pomo_mode = "Work"
            self.pomo_seconds_left = self.pomo_work_var.get() * 60
        self.update_pomo_display()
        self.pomo_after_id = self.root.after(1000, self._pomo_tick)

    def update_pomo_display(self):
        mins, secs = divmod(max(self.pomo_seconds_left, 0), 60)
        self.pomo_time_label.configure(text=f"{mins:02d}:{secs:02d}")
        self.pomo_mode_label.configure(
            text="Work Session 🎯" if self.pomo_mode == "Work" else "Break Time ☕"
        )
        task_title = "No task linked"
        if self.pomo_linked_task_id is not None:
            for task in self.tasks:
                if task["id"] == self.pomo_linked_task_id:
                    task_title = f"Focusing on: {task['title']}"
                    break
        self.pomo_task_var.set(task_title)

    # =========================================================================
    # PERSISTENCE (JSON)
    # =========================================================================
    def save_tasks(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save tasks:\n{e}")

    def load_tasks(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # backward-compatible: fill in any new fields for old task records
                for i, task in enumerate(loaded):
                    task.setdefault("id", i + 1)
                    task.setdefault("order", i)
                    task.setdefault("recurrence", "None")
                    task.setdefault("subtasks", [])
                self.tasks = loaded
                self.next_id = max((t["id"] for t in self.tasks), default=0) + 1
            except (json.JSONDecodeError, Exception):
                self.tasks = []
                self.next_id = 1
        else:
            self.tasks = []
            self.next_id = 1

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass  # settings are non-critical; never block the user on this

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                merged = dict(DEFAULT_SETTINGS)
                merged.update(loaded)
                self.settings = merged
            except (json.JSONDecodeError, Exception):
                self.settings = dict(DEFAULT_SETTINGS)
        else:
            self.settings = dict(DEFAULT_SETTINGS)

    def on_close(self):
        self.save_tasks()
        self.save_settings()
        self.root.destroy()

    # =========================================================================
    # EXPORT
    # =========================================================================
    def export_tasks(self):
        if not self.tasks:
            messagebox.showinfo("Empty", "There are no tasks to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            initialfile="tasks_report.txt"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("=" * 55 + "\n")
                f.write("               TO-DO LIST REPORT\n")
                f.write(f"        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("=" * 55 + "\n\n")
                for i, task in enumerate(self.tasks, start=1):
                    status = "DONE" if task["done"] else "PENDING"
                    f.write(f"{i}. [{status}] {task['title']}\n")
                    f.write(f"   Priority: {task['priority']}  |  Due: {task['due'] or '-'}  |  "
                            f"Category: {task['category']}  |  Repeat: {task.get('recurrence', 'None')}\n")
                    subs = task.get("subtasks", [])
                    if subs:
                        for s in subs:
                            mark = "x" if s["done"] else " "
                            f.write(f"     [{mark}] {s['text']}\n")
                    f.write("\n")
            messagebox.showinfo("Exported", f"Report saved successfully:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Export failed:\n{e}")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()
