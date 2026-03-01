import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import uuid
from datetime import datetime, timedelta
import json
import traceback
from pathlib import Path
from collections import defaultdict

try:
    from . import storage
    from .time_utils import format_min, generate_time_slots
except Exception: 
    import storage
    from time_utils import format_min, generate_time_slots


class StudyPlannerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Study Planner")
        self.root.configure(bg="#f5f5f5")
        self.root.geometry("1400x900")
        self.error_log_path = Path(__file__).parent / "study_planner_errors.log"
        self.root.report_callback_exception = self._handle_tk_exception
        self.sessions = []
        self.sent_reminders = {}
        
        self.dark_mode = False
        self.current_filter = None
        self.session_templates = self._load_templates()
        self.study_goals = {"weekly_hours": 20.0}
        self.current_week_offset = 0
        self.drag_enabled = False
        self.drag_source = None
        
        self.colors = {
            "bg": "#f5f5f5",
            "header_bg": "#2c3e50",
            "header_fg": "#ffffff",
            "button_bg": "#3498db",
            "button_hover": "#2980b9",
            "day_label_bg": "#34495e",
            "day_label_fg": "#ffffff",
            "cell_bg": "#ffffff",
            "cell_border": "#bdc3c7",
            "time_label_fg": "#7f8c8d"
        }

        self.days = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]

        self._create_menu_bar()
        self._create_header()
        self._create_toolbar()
        self._create_calendar_grid()
        self._setup_keyboard_shortcuts()

        try:
            self.sessions = storage.load_sessions()
        except Exception as exc:
            self._show_user_error(
                "Load Error",
                "Your schedule file could not be loaded. A blank schedule was opened instead.",
                exc,
            )
            self.sessions = []

        self.sessions = self._sanitize_sessions(self.sessions, show_warning=True, source="saved schedule")

        self.render_sessions()
        self._check_reminders()
        
        self._update_time_indicator()

    def _log_exception(self, context: str, exc: Exception) -> None:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            with open(self.error_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"[{timestamp}] {context}\n{details}\n")
        except Exception:
            pass

    def _show_user_error(self, title: str, message: str, exc: Exception | None = None) -> None:
        if exc is not None:
            self._log_exception(title, exc)
        try:
            messagebox.showerror(title, message)
        except tk.TclError:
            pass

    def _handle_tk_exception(self, exc_type, exc_value, exc_traceback):
        error = exc_value if isinstance(exc_value, Exception) else Exception(str(exc_value))
        self._log_exception("Unhandled UI callback error", error)
        try:
            messagebox.showerror(
                "Unexpected Error",
                "Something went wrong, but the app is still running. Please try again."
            )
        except tk.TclError:
            pass

    def _parse_time_to_minutes(self, time_value: str) -> int:
        if not isinstance(time_value, str):
            raise ValueError("Time must be text in HH:MM format.")

        parts = time_value.strip().split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format.")

        try:
            hours = int(parts[0])
            minutes = int(parts[1])
        except ValueError as exc:
            raise ValueError("Time must contain only numbers.") from exc

        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Time must be between 00:00 and 23:59.")

        return hours * 60 + minutes

    def _is_valid_color(self, color_value: str) -> bool:
        if not isinstance(color_value, str):
            return False
        cleaned = color_value.strip()
        return len(cleaned) == 7 and cleaned.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in cleaned[1:])

    def _normalize_session(self, session: dict) -> dict:
        if not isinstance(session, dict):
            raise ValueError("Session must be an object.")

        subject = str(session.get("subject", "")).strip()
        day = str(session.get("day", "")).strip()
        start = str(session.get("start", "")).strip()
        end = str(session.get("end", "")).strip()

        if not subject:
            raise ValueError("Session subject is required.")
        if day not in self.days:
            raise ValueError("Session day is invalid.")

        start_minutes = self._parse_time_to_minutes(start)
        end_minutes = self._parse_time_to_minutes(end)
        if end_minutes <= start_minutes:
            raise ValueError("End time must be after start time.")

        color = str(session.get("color", "")).strip()
        if not self._is_valid_color(color):
            color = "#AED6F1"

        normalized: dict[str, object] = {
            "id": str(session.get("id") or uuid.uuid4()),
            "subject": subject,
            "day": day,
            "start": f"{start_minutes // 60:02d}:{start_minutes % 60:02d}",
            "end": f"{end_minutes // 60:02d}:{end_minutes % 60:02d}",
            "color": color,
            "notes": str(session.get("notes", "")).strip(),
        }

        tasks = session.get("tasks", [])
        if isinstance(tasks, list):
            normalized_tasks = []
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                task_text = str(task.get("text", "")).strip()
                if not task_text:
                    continue
                normalized_tasks.append({
                    "text": task_text,
                    "completed": bool(task.get("completed", False)),
                })
            if normalized_tasks:
                normalized["tasks"] = normalized_tasks

        return normalized

    def _sanitize_sessions(self, sessions, show_warning: bool = False, source: str = "data"):
        if not isinstance(sessions, list):
            if show_warning:
                messagebox.showwarning(
                    "Schedule Reset",
                    f"Some {source} was invalid and could not be used."
                )
            return []

        cleaned = []
        dropped_count = 0

        for session in sessions:
            try:
                cleaned.append(self._normalize_session(session))
            except Exception as exc:
                dropped_count += 1
                self._log_exception(f"Invalid session skipped from {source}", exc)

        if show_warning and dropped_count:
            messagebox.showwarning(
                "Some Sessions Skipped",
                f"{dropped_count} invalid session(s) in your {source} were skipped to keep the app stable."
            )

        return cleaned

    def _safe_save_sessions(self, show_error: bool = True) -> bool:
        try:
            storage.save_sessions(self.sessions)
            return True
        except Exception as exc:
            if show_error:
                self._show_user_error(
                    "Save Error",
                    "Your changes could not be saved to disk. Please try again.",
                    exc,
                )
            return False

    def _create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export as JSON", command=self._export_json, accelerator="Ctrl+E")
        file_menu.add_command(label="Import from JSON", command=self._import_json)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Statistics Dashboard", command=self._show_statistics, accelerator="Ctrl+S")
        view_menu.add_command(label="Toggle Dark Mode", command=self._toggle_dark_mode, accelerator="Ctrl+D")
        view_menu.add_separator()
        view_menu.add_command(label="Current Week", command=lambda: self._change_week(0))
        view_menu.add_command(label="Next Week", command=lambda: self._change_week(1), accelerator="Ctrl+Right")
        view_menu.add_command(label="Previous Week", command=lambda: self._change_week(-1), accelerator="Ctrl+Left")
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Session Templates", command=self._manage_templates)
        tools_menu.add_command(label="Study Goals", command=self._manage_goals)
        tools_menu.add_command(label="Break Reminder Settings", command=self._break_reminder_settings)
        tools_menu.add_separator()
        tools_menu.add_command(label="Archive/History", command=self._show_archive)
        tools_menu.add_checkbutton(label="Enable Drag & Drop", command=self._toggle_drag_drop)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _setup_keyboard_shortcuts(self):
        self.root.bind('<Control-n>', lambda e: self.add_session_popup())
        self.root.bind('<Control-e>', lambda e: self._export_json())
        self.root.bind('<Control-s>', lambda e: self._show_statistics())
        self.root.bind('<Control-d>', lambda e: self._toggle_dark_mode())
        self.root.bind('<Control-f>', lambda e: self._show_filter_dialog())
        self.root.bind('<Control-Left>', lambda e: self._change_week(-1))
        self.root.bind('<Control-Right>', lambda e: self._change_week(1))
        self.root.bind('<Delete>', lambda e: self._delete_selected_session())

    def _create_header(self):
        header_frame = tk.Frame(self.root, bg=self.colors["header_bg"], height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        # Title with icon
        self.title_label = tk.Label(
            header_frame,
            text="📚 Weekly Study Planner",
            font=("Segoe UI", 24, "bold"),
            bg=self.colors["header_bg"],
            fg=self.colors["header_fg"]
        )
        self.title_label.pack(side="left", padx=20, pady=15)
        
        # Subtitle
        subtitle = tk.Label(
            header_frame,
            text="Organize your study sessions efficiently",
            font=("Segoe UI", 10),
            bg=self.colors["header_bg"],
            fg="#95a5a6"
        )
        subtitle.pack(side="left", padx=(0, 20))

        # Modern styled button
        add_button = tk.Button(
            header_frame,
            text="➕ Add Session",
            command=self.add_session_popup,
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["button_bg"],
            fg="#ffffff",
            activebackground=self.colors["button_hover"],
            activeforeground="#ffffff",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            relief="flat"
        )
        add_button.pack(side="right", padx=20, pady=15)
        
        # Add hover effect
        def on_enter(e):
            add_button.config(bg=self.colors["button_hover"])
        def on_leave(e):
            add_button.config(bg=self.colors["button_bg"])
        add_button.bind("<Enter>", on_enter)
        add_button.bind("<Leave>", on_leave)
    
    def _create_toolbar(self):
        toolbar = tk.Frame(self.root, bg="#ecf0f1", height=50)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        
        # Filter section
        tk.Label(toolbar, text="Filter:", bg="#ecf0f1", font=("Segoe UI", 10)).pack(side="left", padx=(15, 5))
        
        self.filter_var = tk.StringVar(value="All")
        filter_btn = ttk.Button(toolbar, text="📋 By Subject", command=self._show_filter_dialog)
        filter_btn.pack(side="left", padx=5)
        
        self.filter_label = tk.Label(toolbar, text="(All subjects)", bg="#ecf0f1", fg="#7f8c8d", font=("Segoe UI", 9))
        self.filter_label.pack(side="left", padx=5)
        
        if self.current_filter:
            clear_filter = ttk.Button(toolbar, text="✕", command=self._clear_filter, width=3)
            clear_filter.pack(side="left", padx=2)
        
        # Week navigation
        tk.Label(toolbar, text="|", bg="#ecf0f1", fg="#bdc3c7").pack(side="left", padx=10)
        
        self.week_label = tk.Label(toolbar, text="Current Week", bg="#ecf0f1", font=("Segoe UI", 10, "bold"))
        self.week_label.pack(side="left", padx=10)
        
        prev_btn = ttk.Button(toolbar, text="◄ Prev", command=lambda: self._change_week(-1))
        prev_btn.pack(side="left", padx=2)
        
        today_btn = ttk.Button(toolbar, text="Today", command=lambda: self._change_week(0))
        today_btn.pack(side="left", padx=2)
        
        next_btn = ttk.Button(toolbar, text="Next ►", command=lambda: self._change_week(1))
        next_btn.pack(side="left", padx=2)
        
        # Right side - stats button
        stats_btn = tk.Button(
            toolbar,
            text="📊 Statistics",
            command=self._show_statistics,
            bg="#27ae60",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0,
            padx=15,
            pady=5,
            cursor="hand2"
        )
        stats_btn.pack(side="right", padx=15)
    
    def _create_calendar_grid(self):
        # Wrapper for padding and background
        wrapper = tk.Frame(self.root, bg=self.colors["bg"])
        wrapper.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.calendar_frame = tk.Frame(wrapper, bg=self.colors["bg"])
        self.calendar_frame.pack(fill="both", expand=True)

        # Create day labels (column headers) with modern styling + today indicator
        today_name = datetime.now().strftime("%A")
        for column_index, day_name in enumerate(self.days):
            is_today = (day_name == today_name and self.current_week_offset == 0)
            day_frame = tk.Frame(
                self.calendar_frame,
                bg="#e74c3c" if is_today else self.colors["day_label_bg"],
                height=40
            )
            day_frame.grid(row=0, column=column_index, padx=2, pady=(0, 8), sticky="ew")
            day_frame.grid_propagate(False)
            
            day_text = f"⭐ {day_name}" if is_today else day_name
            label = tk.Label(
                day_frame,
                text=day_text,
                font=("Segoe UI", 13, "bold"),
                bg="#e74c3c" if is_today else self.colors["day_label_bg"],
                fg=self.colors["day_label_fg"]
            )
            label.pack(expand=True)

        self.time_slots = generate_time_slots()

        self.slot_frames = []
        for row_offset, (slot_start, slot_end) in enumerate(self.time_slots, start=1):
            row_frames = []

            for column_index in range(7):
                cell = tk.Frame(
                    self.calendar_frame,
                    width=140,
                    height=65,
                    bg=self.colors["cell_bg"],
                    highlightbackground=self.colors["cell_border"],
                    highlightthickness=1
                )
                cell.grid(
                    row=row_offset,
                    column=column_index,
                    padx=2,
                    pady=2,
                    sticky="nsew"
                )

                self.calendar_frame.grid_columnconfigure(column_index, weight=1)
                self.calendar_frame.grid_rowconfigure(row_offset, weight=1)
                displayed_time = f"{format_min(slot_start)}-{format_min(slot_end)}"
                time_label = tk.Label(
                    cell, 
                    text=displayed_time, 
                    font=("Segoe UI", 8),
                    bg=self.colors["cell_bg"],
                    fg=self.colors["time_label_fg"]
                )
                time_label.place(x=4, y=3)
                setattr(time_label, "is_time_label", True)

                row_frames.append(cell)

            self.slot_frames.append(row_frames)
        
        self.time_indicator_line = None
    
    def _update_time_indicator(self):
        try:
            now = datetime.now()
            today_name = now.strftime("%A")

            if self.current_week_offset == 0 and today_name in self.days:
                current_minutes = now.hour * 60 + now.minute
                day_index = self.days.index(today_name)

                for row_idx, (slot_start, slot_end) in enumerate(self.time_slots):
                    if slot_start <= current_minutes < slot_end:
                        cell = self.slot_frames[row_idx][day_index]

                        if self.time_indicator_line:
                            try:
                                self.time_indicator_line.destroy()
                            except tk.TclError:
                                self.time_indicator_line = None

                        progress = (current_minutes - slot_start) / (slot_end - slot_start)
                        y_pos = int(progress * 65)

                        self.time_indicator_line = tk.Frame(
                            cell,
                            bg="#e74c3c",
                            height=3
                        )
                        self.time_indicator_line.place(x=0, y=y_pos, relwidth=1)
                        break
        except Exception as exc:
            self._log_exception("Time indicator update failed", exc)
        finally:
            self.root.after(60000, self._update_time_indicator)
  
    def add_session_popup(self, template=None):
        popup = tk.Toplevel(self.root)
        popup.title("Add Study Session")
        popup.geometry("450x800")  # Increased height for new fields
        popup.configure(bg="#f5f5f5")
        popup.resizable(False, False)
        
        # Center the popup window
        popup.transient(self.root)
        popup.grab_set()
        
        # Use grid on the toplevel so header, body, footer align reliably
        popup.grid_rowconfigure(1, weight=1)
        popup.grid_columnconfigure(0, weight=1)

        # Header section
        header = tk.Frame(popup, bg=self.colors["header_bg"], height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        
        header_label = tk.Label(
            header,
            text="📝 Add Study Session",
            font=("Segoe UI", 18, "bold"),
            bg=self.colors["header_bg"],
            fg=self.colors["header_fg"]
        )
        header_label.pack(pady=20)
        
        # Main form container
        form_frame = tk.Frame(popup, bg="#f5f5f5")
        form_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)

        # --- Subject ---
        subject_label = tk.Label(
            form_frame,
            text="Subject",
            font=("Segoe UI", 11, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        )
        subject_label.pack(anchor="w", pady=(10, 5))
        
        subject_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        subject_frame.pack(fill="x", pady=(0, 15))
        
        subject_entry = tk.Entry(
            subject_frame,
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#2c3e50",
            bd=0,
            relief="flat"
        )
        subject_entry.pack(fill="x", padx=10, pady=8)

        # --- Day ---
        day_label = tk.Label(
            form_frame,
            text="Day of Week",
            font=("Segoe UI", 11, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        )
        day_label.pack(anchor="w", pady=(10, 5))
        
        selected_day = tk.StringVar()
        day_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        day_frame.pack(fill="x", pady=(0, 15))
        
        day_dropdown = ttk.Combobox(
            day_frame,
            textvariable=selected_day,
            values=self.days,
            state="readonly",
            font=("Segoe UI", 11)
        )
        day_dropdown.pack(fill="x", padx=8, pady=6)

        # --- Start Time ---
        start_label = tk.Label(
            form_frame,
            text="Start Time (HH:MM)",
            font=("Segoe UI", 11, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        )
        start_label.pack(anchor="w", pady=(10, 5))
        
        start_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        start_frame.pack(fill="x", pady=(0, 15))
        
        start_entry = tk.Entry(
            start_frame,
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#2c3e50",
            bd=0,
            relief="flat"
        )
        start_entry.pack(fill="x", padx=10, pady=8)
        start_entry.insert(0, "15:30")

        # --- End Time ---
        end_label = tk.Label(
            form_frame,
            text="End Time (HH:MM)",
            font=("Segoe UI", 11, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        )
        end_label.pack(anchor="w", pady=(10, 5))
        
        end_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        end_frame.pack(fill="x", pady=(0, 15))
        
        end_entry = tk.Entry(
            end_frame,
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#2c3e50",
            bd=0,
            relief="flat"
        )
        end_entry.pack(fill="x", padx=10, pady=8)
        end_entry.insert(0, "17:00")

        # --- Colour Selection ---
        color_label = tk.Label(
            form_frame,
            text="Session Color",
            font=("Segoe UI", 11, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        )
        color_label.pack(anchor="w", pady=(10, 5))
        
        # Color picker container
        color_container = tk.Frame(form_frame, bg="#f5f5f5")
        color_container.pack(fill="x", pady=(0, 15))
        
        colour_entry = tk.Entry(
            color_container,
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#2c3e50",
            bd=1,
            relief="solid",
            width=12
        )
        colour_entry.insert(0, "#AED6F1")
        colour_entry.pack(side="left")
        
        # Color preview box
        color_preview = tk.Label(
            color_container,
            text="   ",
            bg="#AED6F1",
            width=4,
            relief="solid",
            bd=1
        )
        color_preview.pack(side="left", padx=10)
        
        # Update color preview when entry changes
        def update_preview(*args):
            try:
                color = colour_entry.get()
                color_preview.config(bg=color)
            except tk.TclError:
                pass
        
        colour_entry.bind("<KeyRelease>", update_preview)
        
        # Preset color buttons
        preset_colors = [
            "#AED6F1", "#F8B4B4", "#B4E7B4", "#F9E79F",
            "#D7BDE2", "#FAD7A0", "#A9DFBF", "#F5CBA7"
        ]
        
        preset_frame = tk.Frame(form_frame, bg="#f5f5f5")
        preset_frame.pack(fill="x", pady=(0, 10))
        
        preset_label = tk.Label(
            preset_frame,
            text="Quick colors:",
            font=("Segoe UI", 9),
            bg="#f5f5f5",
            fg="#7f8c8d"
        )
        preset_label.pack(side="left", padx=(0, 8))
        
        for color in preset_colors:
            def make_color_setter(c):
                return lambda: (colour_entry.delete(0, tk.END), 
                               colour_entry.insert(0, c),
                               color_preview.config(bg=c))
            
            btn = tk.Button(
                preset_frame,
                bg=color,
                width=2,
                height=1,
                bd=1,
                relief="solid",
                cursor="hand2",
                command=make_color_setter(color)
            )
            btn.pack(side="left", padx=2)

        # --- Notes Field ---
        notes_label = tk.Label(
            form_frame,
            text="Notes (optional)",
            font=("Segoe UI", 11, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        )
        notes_label.pack(anchor="w", pady=(10, 5))
        
        notes_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        notes_frame.pack(fill="x", pady=(0, 15))
        
        notes_text = tk.Text(
            notes_frame,
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#2c3e50",
            bd=0,
            relief="flat",
            height=3,
            wrap="word"
        )
        notes_text.pack(fill="both", padx=10, pady=8)
        
        # --- Recurring Option ---
        recurring_var = tk.BooleanVar(value=False)
        recurring_check = tk.Checkbutton(
            form_frame,
            text="Create on multiple days (recurring)",
            variable=recurring_var,
            font=("Segoe UI", 10),
            bg="#f5f5f5",
            fg="#2c3e50",
            activebackground="#f5f5f5"
        )
        recurring_check.pack(anchor="w", pady=(5, 5))
        
        # Recurring days selection (initially hidden)
        recurring_frame = tk.Frame(form_frame, bg="#f5f5f5")
        recurring_days_vars = {}
        
        def toggle_recurring():
            if recurring_var.get():
                recurring_frame.pack(fill="x", pady=(0, 15))
            else:
                recurring_frame.pack_forget()
        
        recurring_var.trace_add("write", lambda *args: toggle_recurring())
        
        tk.Label(
            recurring_frame,
            text="Select days:",
            font=("Segoe UI", 9),
            bg="#f5f5f5",
            fg="#7f8c8d"
        ).pack(anchor="w", padx=(20, 0))
        
        days_check_frame = tk.Frame(recurring_frame, bg="#f5f5f5")
        days_check_frame.pack(fill="x", padx=20)
        
        for day in self.days:
            var = tk.BooleanVar(value=False)
            recurring_days_vars[day] = var
            cb = tk.Checkbutton(
                days_check_frame,
                text=day,
                variable=var,
                font=("Segoe UI", 9),
                bg="#f5f5f5"
            )
            cb.pack(side="left")

        # --- Internal function for saving ---
        def save_session():
            subject = subject_entry.get().strip()
            day = selected_day.get()
            start = start_entry.get().strip()
            end = end_entry.get().strip()
            colour = colour_entry.get().strip()
            notes = notes_text.get("1.0", "end-1c").strip()

            if not subject:
                messagebox.showerror("Missing Subject", "Please enter a subject name.")
                return

            try:
                self._parse_time_to_minutes(start)
                self._parse_time_to_minutes(end)
                self._normalize_session({
                    "subject": subject,
                    "day": self.days[0],
                    "start": start,
                    "end": end,
                    "color": colour,
                    "notes": notes,
                })
            except ValueError as exc:
                messagebox.showerror("Invalid Time", str(exc))
                return

            # Determine which days to create sessions for
            days_to_create = []
            if recurring_var.get():
                days_to_create = [d for d, var in recurring_days_vars.items() if var.get()]
                if not days_to_create:
                    messagebox.showerror("Error", "Please select at least one day for recurring session.")
                    return
            else:
                # Field validation
                if not day:
                    messagebox.showerror("Error", "Please complete all fields.")
                    return
                days_to_create = [day]
            
            # Time conflict detection
            conflicts = self._check_time_conflicts(days_to_create, start, end)
            if conflicts:
                conflict_msg = "Time conflicts detected:\n\n" + "\n".join(conflicts)
                conflict_msg += "\n\nDo you want to add anyway?"
                if not messagebox.askyesno("Conflict Warning", conflict_msg):
                    return

            previous_sessions = list(self.sessions)

            # Create sessions for each selected day
            for target_day in days_to_create:
                try:
                    new_session = self._normalize_session({
                        "subject": subject,
                        "day": target_day,
                        "start": start,
                        "end": end,
                        "color": colour,
                        "notes": notes,
                        "id": str(uuid.uuid4())
                    })
                    self.sessions.append(new_session)
                except ValueError as exc:
                    self.sessions = previous_sessions
                    messagebox.showerror("Invalid Session", str(exc))
                    return

            # Save session to disk
            if not self._safe_save_sessions(show_error=True):
                self.sessions = previous_sessions
                return

            # Update calendar immediately
            self.render_sessions()
            messagebox.showinfo("Saved", "Study session added successfully.")
            popup.destroy()

        # Footer bar pinned to bottom for consistent buttons layout
        footer = tk.Frame(popup, bg="#ecf0f1", highlightthickness=1, highlightbackground="#dfe6e9")
        footer.grid(row=2, column=0, sticky="ew")

        buttons = tk.Frame(footer, bg="#ecf0f1")
        buttons.pack(fill="x", padx=20, pady=12)

        # Two equal-width columns
        buttons.grid_columnconfigure(0, weight=1)
        buttons.grid_columnconfigure(1, weight=1)

        # Save button
        save_btn = tk.Button(
            buttons,
            text="✓ Save Session",
            command=save_session,
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["button_bg"],
            fg="#ffffff",
            activebackground=self.colors["button_hover"],
            activeforeground="#ffffff",
            bd=0,
            padx=30,
            pady=12,
            cursor="hand2",
            relief="flat"
        )
        save_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        # Cancel button
        cancel_btn = tk.Button(
            buttons,
            text="✕ Cancel",
            command=popup.destroy,
            font=("Segoe UI", 12, "bold"),
            bg="#95a5a6",
            fg="#ffffff",
            activebackground="#7f8c8d",
            activeforeground="#ffffff",
            bd=0,
            padx=30,
            pady=12,
            cursor="hand2",
            relief="flat"
        )
        cancel_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        
        # Add hover effects
        def on_save_enter(e):
            save_btn.config(bg=self.colors["button_hover"])
        def on_save_leave(e):
            save_btn.config(bg=self.colors["button_bg"])
        def on_cancel_enter(e):
            cancel_btn.config(bg="#7f8c8d")
        def on_cancel_leave(e):
            cancel_btn.config(bg="#95a5a6")
            
        save_btn.bind("<Enter>", on_save_enter)
        save_btn.bind("<Leave>", on_save_leave)
        cancel_btn.bind("<Enter>", on_cancel_enter)
        cancel_btn.bind("<Leave>", on_cancel_leave)
        
        # Set focus to subject entry
        subject_entry.focus()
   
  
    def render_sessions(self):
        # Clear all widgets except the internal time labels
        for row in self.slot_frames:
            for cell in row:
                for child in cell.winfo_children():
                    if getattr(child, "is_time_label", False):
                        continue
                    child.destroy()

        # Filter sessions if filter is active
        sessions_to_render = self.sessions
        if self.current_filter:
            sessions_to_render = [s for s in self.sessions if s.get("subject") == self.current_filter]

        # Place each valid session onto the calendar
        for session in sessions_to_render:
            try:
                normalized_session = self._normalize_session(session)
                day_index = self.days.index(str(normalized_session["day"]))
                start_minutes = self._parse_time_to_minutes(str(normalized_session["start"]))
                end_minutes = self._parse_time_to_minutes(str(normalized_session["end"]))
            except (ValueError, TypeError):
                continue

            # Check session-slot overlap and render
            for slot_index, (slot_start, slot_end) in enumerate(self.time_slots):
                if start_minutes < slot_end and end_minutes > slot_start:
                    parent_cell = self.slot_frames[slot_index][day_index]
                    colour = normalized_session.get("color", "#AED6F1")

                    # Create event frame with rounded appearance
                    event_frame = tk.Frame(
                        parent_cell, 
                        bg=colour,
                        highlightbackground=self._darken_color(colour),
                        highlightthickness=2
                    )
                    event_frame.place(relx=0.02, rely=0.18, relwidth=0.96, relheight=0.80)

                    subject_label = tk.Label(
                        event_frame,
                        text=normalized_session.get("subject", ""),
                        bg=colour,
                        fg=self._get_contrast_color(colour),
                        font=("Segoe UI", 10, "bold"),
                        wraplength=120
                    )
                    subject_label.pack(expand=True, fill="both", padx=5, pady=2)
                    # Attach metadata for callbacks
                    session_id = str(normalized_session["id"])
                    setattr(event_frame, "session_id", session_id)
                    setattr(event_frame, "slot_index", slot_index)

                    # Bind right-click to menu and double-click to edit directly
                    def make_edit_handler(sid):
                        return lambda e: self.edit_session_popup(sid)
                    
                    def make_menu_handler(sid, sidx):
                        return lambda e: self._show_delete_popup(sid, sidx)

                    event_frame.bind("<Button-3>", make_menu_handler(session_id, slot_index))
                    event_frame.bind("<Double-Button-1>", make_edit_handler(session_id))
                    subject_label.bind("<Button-3>", make_menu_handler(session_id, slot_index))
                    subject_label.bind("<Double-Button-1>", make_edit_handler(session_id))
                    
                    # Add hover effect
                    def on_hover_enter(e, frame=event_frame):
                        frame.config(highlightthickness=3)
                    def on_hover_leave(e, frame=event_frame):
                        frame.config(highlightthickness=2)
                    event_frame.bind("<Enter>", on_hover_enter)
                    event_frame.bind("<Leave>", on_hover_leave)
                    subject_label.bind("<Enter>", on_hover_enter)
                    subject_label.bind("<Leave>", on_hover_leave)

                    # Add a small visible options/delete button in the corner
                    try:
                        del_btn = tk.Button(
                            event_frame,
                            text="⋮",
                            bg=colour,
                            fg=self._get_contrast_color(colour),
                            bd=0,
                            font=("Segoe UI", 10, "bold"),
                            activebackground=self._darken_color(colour),
                            cursor="hand2",
                            command=lambda sid=session_id, sidx=slot_index: self._show_delete_popup(sid, sidx)
                        )
                        del_btn.place(relx=0.85, rely=0.02, relwidth=0.13, relheight=0.20)
                    except tk.TclError as exc:
                        self._log_exception("Failed to create session options button", exc)

    def _darken_color(self, hex_color: str, factor: float = 0.7) -> str:
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            r, g, b = int(r * factor), int(g * factor), int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except (AttributeError, ValueError):
            return "#2c3e50"
    
    def _get_contrast_color(self, hex_color: str) -> str:
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if brightness > 128 else "#ffffff"
        except (AttributeError, ValueError):
            return "#000000"

    def _show_delete_popup(self, session_id: str, slot_index: int):
        # Find the session object
        session = next((s for s in self.sessions if s.get("id") == session_id), None)
        if session is None:
            messagebox.showerror("Not found", "Session not found (it may have been deleted).")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Session Options")
        popup.geometry("340x270")
        popup.transient(self.root)
        popup.grab_set()

        info = f"Subject: {session.get('subject')}\nDay: {session.get('day')}\nBlock: {format_min(self.time_slots[slot_index][0])} - {format_min(self.time_slots[slot_index][1])}"
        tk.Label(popup, text=info, font=("Segoe UI", 10), justify="left").pack(pady=15, padx=20)

        # Edit session
        def edit_sess():
            popup.destroy()
            self.edit_session_popup(session_id)
        
        # Manage tasks
        def manage_tasks():
            popup.destroy()
            self._manage_session_tasks(session_id)

        # Remove this block only
        def remove_block():
            self._remove_block_from_session(session_id, slot_index)
            popup.destroy()

        # Remove full session
        def remove_all():
            if messagebox.askyesno("Confirm Delete", "Delete this entire session?"):
                self._remove_session(session_id)
                popup.destroy()

        tk.Button(popup, text="✏️ Edit Session", command=edit_sess, font=("Segoe UI", 10, "bold"),
                 bg=self.colors["button_bg"], fg="#ffffff", width=25, pady=8).pack(pady=3)
        tk.Button(popup, text="📝 Manage Tasks", command=manage_tasks, font=("Segoe UI", 10, "bold"),
                 bg="#27ae60", fg="#ffffff", width=25, pady=8).pack(pady=3)
        tk.Button(popup, text="🗑️ Remove this block", command=remove_block, font=("Segoe UI", 10),
                 width=25, pady=8).pack(pady=3)
        tk.Button(popup, text="❌ Remove entire session", command=remove_all, font=("Segoe UI", 10),
                 bg="#e74c3c", fg="#ffffff", width=25, pady=8).pack(pady=3)
        tk.Button(popup, text="Cancel", command=popup.destroy, font=("Segoe UI", 10),
                 width=25, pady=8).pack(pady=3)

    def _remove_session(self, session_id: str):
        previous_sessions = list(self.sessions)
        self.sessions = [s for s in self.sessions if s.get("id") != session_id]
        if not self._safe_save_sessions(show_error=True):
            self.sessions = previous_sessions
            return
        self.render_sessions()

    def _remove_block_from_session(self, session_id: str, slot_index: int):
        session = next((s for s in self.sessions if s.get("id") == session_id), None)
        if session is None:
            return

        try:
            s_min = self._parse_time_to_minutes(session.get("start", "00:00"))
            e_min = self._parse_time_to_minutes(session.get("end", "00:00"))
        except ValueError:
            return

        block_start, block_end = self.time_slots[slot_index]

        # If the session is entirely within the block (or exactly equal) -> remove session
        if s_min >= block_start and e_min <= block_end:
            return self._remove_session(session_id)

        new_sessions = []

        # Left remainder
        if s_min < block_start:
            new_sessions.append({
                "id": str(uuid.uuid4()),
                "subject": session.get("subject"),
                "day": session.get("day"),
                "start": f"{s_min//60:02d}:{s_min%60:02d}",
                "end": f"{block_start//60:02d}:{block_start%60:02d}",
                "color": session.get("color")
            })

        # Right remainder
        if e_min > block_end:
            new_sessions.append({
                "id": str(uuid.uuid4()),
                "subject": session.get("subject"),
                "day": session.get("day"),
                "start": f"{block_end//60:02d}:{block_end%60:02d}",
                "end": f"{e_min//60:02d}:{e_min%60:02d}",
                "color": session.get("color")
            })

        # Replace original session with new parts (if any)
        previous_sessions = list(self.sessions)
        self.sessions = [s for s in self.sessions if s.get("id") != session_id]
        self.sessions.extend(new_sessions)

        if not self._safe_save_sessions(show_error=True):
            self.sessions = previous_sessions
            return

        self.render_sessions()

    def _check_reminders(self):
        # Check for upcoming sessions and send reminders at 1 hour, 30 min, and start time.
        try:
            now = datetime.now()
            current_day = now.strftime("%A")
            current_time_minutes = now.hour * 60 + now.minute

            for session in self.sessions:
                try:
                    normalized_session = self._normalize_session(session)
                except ValueError:
                    continue

                session_id = normalized_session.get("id")
                if normalized_session.get("day") != current_day:
                    continue

                session_start_minutes = self._parse_time_to_minutes(normalized_session.get("start", "00:00"))
                time_until = session_start_minutes - current_time_minutes

                if session_id not in self.sent_reminders:
                    self.sent_reminders[session_id] = set()

                if 59 <= time_until <= 61 and '60min' not in self.sent_reminders[session_id]:
                    self._send_reminder(normalized_session, "1 hour")
                    self.sent_reminders[session_id].add('60min')
                elif 29 <= time_until <= 31 and '30min' not in self.sent_reminders[session_id]:
                    self._send_reminder(normalized_session, "30 minutes")
                    self.sent_reminders[session_id].add('30min')
                elif 0 <= time_until <= 1 and '0min' not in self.sent_reminders[session_id]:
                    self._send_reminder(normalized_session, "now")
                    self.sent_reminders[session_id].add('0min')
        except Exception as exc:
            self._log_exception("Reminder check failed", exc)
        finally:
            self.root.after(60000, self._check_reminders)
    
    def _send_reminder(self, session, time_label):
        # Display a reminder notification for a session.
        subject = session.get("subject", "Unknown")
        start = session.get("start", "")
        end = session.get("end", "")
        
        if time_label == "now":
            message = f"Your {subject} session is starting now!\n\nTime: {start} - {end}"
            title = "Session Starting!"
        else:
            message = f"Your {subject} session starts in {time_label}.\n\nTime: {start} - {end}"
            title = f"Reminder: {time_label} until session"
        
        try:
            messagebox.showinfo(title, message)
        except tk.TclError as exc:
            self._log_exception("Reminder dialog failed", exc)
    
    def edit_session_popup(self, session_id: str):
        # Open popup to edit an existing session.
        session = next((s for s in self.sessions if s.get("id") == session_id), None)
        if session is None:
            messagebox.showerror("Error", "Session not found.")
            return
        
        popup = tk.Toplevel(self.root)
        popup.title("Edit Study Session")
        popup.geometry("450x780")
        popup.configure(bg="#f5f5f5")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        
        popup.grid_rowconfigure(1, weight=1)
        popup.grid_columnconfigure(0, weight=1)

        # Header
        header = tk.Frame(popup, bg=self.colors["header_bg"], height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        
        header_label = tk.Label(
            header,
            text="✏️ Edit Study Session",
            font=("Segoe UI", 18, "bold"),
            bg=self.colors["header_bg"],
            fg=self.colors["header_fg"]
        )
        header_label.pack(pady=20)
        
        # Form
        form_frame = tk.Frame(popup, bg="#f5f5f5")
        form_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)

        # Subject
        tk.Label(form_frame, text="Subject", font=("Segoe UI", 11, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(anchor="w", pady=(10, 5))
        subject_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        subject_frame.pack(fill="x", pady=(0, 15))
        subject_entry = tk.Entry(subject_frame, font=("Segoe UI", 11), bg="#ffffff", fg="#2c3e50", bd=0, relief="flat")
        subject_entry.insert(0, session.get("subject", ""))
        subject_entry.pack(fill="x", padx=10, pady=8)

        # Day
        tk.Label(form_frame, text="Day of Week", font=("Segoe UI", 11, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(anchor="w", pady=(10, 5))
        day_var = tk.StringVar(value=session.get("day", ""))
        day_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        day_frame.pack(fill="x", pady=(0, 15))
        day_dropdown = ttk.Combobox(day_frame, textvariable=day_var, values=self.days, state="readonly", font=("Segoe UI", 11))
        day_dropdown.pack(fill="x", padx=8, pady=6)

        # Start Time
        tk.Label(form_frame, text="Start Time (HH:MM)", font=("Segoe UI", 11, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(anchor="w", pady=(10, 5))
        start_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        start_frame.pack(fill="x", pady=(0, 15))
        start_entry = tk.Entry(start_frame, font=("Segoe UI", 11), bg="#ffffff", fg="#2c3e50", bd=0, relief="flat")
        start_entry.insert(0, session.get("start", ""))
        start_entry.pack(fill="x", padx=10, pady=8)

        # End Time
        tk.Label(form_frame, text="End Time (HH:MM)", font=("Segoe UI", 11, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(anchor="w", pady=(10, 5))
        end_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        end_frame.pack(fill="x", pady=(0, 15))
        end_entry = tk.Entry(end_frame, font=("Segoe UI", 11), bg="#ffffff", fg="#2c3e50", bd=0, relief="flat")
        end_entry.insert(0, session.get("end", ""))
        end_entry.pack(fill="x", padx=10, pady=8)

        # Color
        tk.Label(form_frame, text="Session Color", font=("Segoe UI", 11, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(anchor="w", pady=(10, 5))
        color_container = tk.Frame(form_frame, bg="#f5f5f5")
        color_container.pack(fill="x", pady=(0, 15))
        colour_entry = tk.Entry(color_container, font=("Segoe UI", 11), bg="#ffffff", fg="#2c3e50", bd=1, relief="solid", width=12)
        colour_entry.insert(0, session.get("color", "#AED6F1"))
        colour_entry.pack(side="left")
        color_preview = tk.Label(color_container, text="   ", bg=session.get("color", "#AED6F1"), width=4, relief="solid", bd=1)
        color_preview.pack(side="left", padx=10)
        
        def update_preview(*args):
            try:
                color_preview.config(bg=colour_entry.get())
            except tk.TclError:
                pass
        colour_entry.bind("<KeyRelease>", update_preview)

        # Notes
        tk.Label(form_frame, text="Notes (optional)", font=("Segoe UI", 11, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(anchor="w", pady=(10, 5))
        notes_frame = tk.Frame(form_frame, bg="#ffffff", highlightbackground="#bdc3c7", highlightthickness=1)
        notes_frame.pack(fill="x", pady=(0, 15))
        notes_text = tk.Text(notes_frame, font=("Segoe UI", 10), bg="#ffffff", fg="#2c3e50", bd=0, relief="flat", height=3, wrap="word")
        notes_text.insert("1.0", session.get("notes", ""))
        notes_text.pack(fill="both", padx=10, pady=8)

        def save_changes():
            candidate = {
                "id": session.get("id"),
                "subject": subject_entry.get().strip(),
                "day": day_var.get().strip(),
                "start": start_entry.get().strip(),
                "end": end_entry.get().strip(),
                "color": colour_entry.get().strip(),
                "notes": notes_text.get("1.0", "end-1c").strip(),
                "tasks": session.get("tasks", []),
            }

            if not (candidate["subject"] and candidate["day"] and candidate["start"] and candidate["end"]):
                messagebox.showerror("Error", "Please complete all required fields.")
                return

            try:
                normalized = self._normalize_session(candidate)
            except ValueError as exc:
                messagebox.showerror("Invalid Session", str(exc))
                return

            previous_session = dict(session)
            session.clear()
            session.update(normalized)

            try:
                storage.save_sessions(self.sessions)
                self.render_sessions()
                messagebox.showinfo("Saved", "Session updated successfully.")
                popup.destroy()
            except Exception as exc:
                session.clear()
                session.update(previous_session)
                self._show_user_error("Save Error", "Could not save your changes.", exc)

        # Footer
        footer = tk.Frame(popup, bg="#ecf0f1", highlightthickness=1, highlightbackground="#dfe6e9")
        footer.grid(row=2, column=0, sticky="ew")
        buttons = tk.Frame(footer, bg="#ecf0f1")
        buttons.pack(fill="x", padx=20, pady=12)
        buttons.grid_columnconfigure(0, weight=1)
        buttons.grid_columnconfigure(1, weight=1)
        
        save_btn = tk.Button(buttons, text="✓ Save Changes", command=save_changes, font=("Segoe UI", 12, "bold"),
                            bg=self.colors["button_bg"], fg="#ffffff", bd=0, padx=30, pady=12, cursor="hand2")
        save_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        
        cancel_btn = tk.Button(buttons, text="✕ Cancel", command=popup.destroy, font=("Segoe UI", 12, "bold"),
                              bg="#95a5a6", fg="#ffffff", bd=0, padx=30, pady=12, cursor="hand2")
        cancel_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))
    
    def _check_time_conflicts(self, days, start_str, end_str, exclude_id=None):
        try:
            new_start = self._parse_time_to_minutes(start_str)
            new_end = self._parse_time_to_minutes(end_str)
        except ValueError:
            return []
        
        conflicts = []
        for session in self.sessions:
            if exclude_id and session.get("id") == exclude_id:
                continue
            if session.get("day") not in days:
                continue
            
            try:
                existing_start = self._parse_time_to_minutes(session.get("start", "00:00"))
                existing_end = self._parse_time_to_minutes(session.get("end", "00:00"))
            except ValueError:
                continue
            
            # Check overlap
            if new_start < existing_end and new_end > existing_start:
                conflicts.append(
                    f"{session.get('day')}: {session.get('subject')} "
                    f"({session.get('start')}-{session.get('end')})"
                )
        
        return conflicts
    
    def _show_filter_dialog(self):
        # Show dialog to filter sessions by subject.
        subjects = sorted(set(s.get("subject", "") for s in self.sessions if s.get("subject")))
        if not subjects:
            messagebox.showinfo("No Subjects", "No sessions to filter.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Filter by Subject")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Select a subject to filter:", font=("Segoe UI", 11, "bold")).pack(pady=10)
        
        listbox = tk.Listbox(dialog, font=("Segoe UI", 10), height=15)
        listbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        for subject in subjects:
            listbox.insert(tk.END, subject)
        
        def apply_filter():
            selection = listbox.curselection()
            if selection:
                self.current_filter = listbox.get(selection[0])
                self.filter_label.config(text=f"(Showing: {self.current_filter})")
                self.render_sessions()
                dialog.destroy()
        
        tk.Button(dialog, text="Apply Filter", command=apply_filter, font=("Segoe UI", 10, "bold"),
                 bg=self.colors["button_bg"], fg="#ffffff", padx=20, pady=8).pack(pady=5)
        tk.Button(dialog, text="Clear Filter", command=lambda: [self._clear_filter(), dialog.destroy()],
                 font=("Segoe UI", 10)).pack(pady=5)
    
    def _clear_filter(self):
        # Clear the current subject filter.
        self.current_filter = None
        self.filter_label.config(text="(All subjects)")
        self.render_sessions()
    
    def _show_statistics(self):
        # Display statistics about study sessions.
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Study Statistics")
        stats_window.geometry("600x700")
        stats_window.configure(bg="#f5f5f5")
        
        # Header
        header = tk.Frame(stats_window, bg=self.colors["header_bg"], height=70)
        header.pack(fill="x")
        tk.Label(header, text="📊 Study Statistics", font=("Segoe UI", 20, "bold"),
                bg=self.colors["header_bg"], fg="#ffffff").pack(pady=15)
        
        # Content area
        content = tk.Frame(stats_window, bg="#f5f5f5")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Calculate statistics
        total_sessions = len(self.sessions)
        subjects_count = len(set(s.get("subject") for s in self.sessions))
        
        # Total hours
        total_minutes = 0
        subject_minutes = defaultdict(int)
        day_minutes = defaultdict(int)
        
        for session in self.sessions:
            try:
                start_minutes = self._parse_time_to_minutes(session.get("start", "00:00"))
                end_minutes = self._parse_time_to_minutes(session.get("end", "00:00"))
                duration = end_minutes - start_minutes
                if duration > 0:
                    total_minutes += duration
                    subject_minutes[session.get("subject", "Unknown")] += duration
                    day_minutes[session.get("day", "Unknown")] += duration
            except ValueError:
                continue
        
        total_hours = total_minutes / 60
        
        # Display stats
        stats_frame = tk.LabelFrame(content, text="Overview", font=("Segoe UI", 12, "bold"),
                                   bg="#ffffff", fg="#2c3e50", padx=20, pady=15)
        stats_frame.pack(fill="x", pady=10)
        
        tk.Label(stats_frame, text=f"Total Sessions: {total_sessions}", font=("Segoe UI", 11),
                bg="#ffffff", anchor="w").pack(fill="x", pady=3)
        tk.Label(stats_frame, text=f"Unique Subjects: {subjects_count}", font=("Segoe UI", 11),
                bg="#ffffff", anchor="w").pack(fill="x", pady=3)
        tk.Label(stats_frame, text=f"Total Study Time: {total_hours:.1f} hours", font=("Segoe UI", 11),
                bg="#ffffff", anchor="w").pack(fill="x", pady=3)
        tk.Label(stats_frame, text=f"Average per Session: {total_hours/total_sessions if total_sessions else 0:.1f} hours",
                font=("Segoe UI", 11), bg="#ffffff", anchor="w").pack(fill="x", pady=3)
        
        # Goal progress
        goal_hours = self.study_goals.get("weekly_hours", 20)
        progress = (total_hours / goal_hours) * 100 if goal_hours > 0 else 0
        
        goal_frame = tk.LabelFrame(content, text=f"Weekly Goal: {goal_hours} hours",
                                  font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#2c3e50", padx=20, pady=15)
        goal_frame.pack(fill="x", pady=10)
        
        progress_bar_bg = tk.Frame(goal_frame, bg="#ecf0f1", height=30)
        progress_bar_bg.pack(fill="x", pady=5)
        
        progress_width = min(progress / 100, 1.0)
        progress_color = "#27ae60" if progress >= 100 else "#3498db" if progress >= 50 else "#e74c3c"
        progress_bar = tk.Frame(progress_bar_bg, bg=progress_color, height=30)
        progress_bar.place(x=0, y=0, relwidth=progress_width, relheight=1)
        
        tk.Label(goal_frame, text=f"{progress:.0f}% Complete ({total_hours:.1f} / {goal_hours} hours)",
                font=("Segoe UI", 10, "bold"), bg="#ffffff").pack()
        
        # By subject
        subject_frame = tk.LabelFrame(content, text="Time by Subject", font=("Segoe UI", 12, "bold"),
                                     bg="#ffffff", fg="#2c3e50", padx=20, pady=15)
        subject_frame.pack(fill="both", expand=True, pady=10)
        
        subject_text = tk.Text(subject_frame, font=("Segoe UI", 10), bg="#ffffff", height=8, wrap="word")
        subject_text.pack(fill="both", expand=True)
        
        for subject, mins in sorted(subject_minutes.items(), key=lambda x: x[1], reverse=True):
            hours = mins / 60
            subject_text.insert(tk.END, f"{subject}: {hours:.1f} hours\n")
        subject_text.config(state="disabled")
        
        # Close button
        tk.Button(stats_window, text="Close", command=stats_window.destroy,
                 font=("Segoe UI", 11, "bold"), bg="#95a5a6", fg="#ffffff",
                 padx=30, pady=10).pack(pady=10)
    
    def _toggle_dark_mode(self):
        # Toggle between light and dark color schemes.
        self.dark_mode = not self.dark_mode
        
        if self.dark_mode:
            self.colors = {
                "bg": "#2c3e50",
                "header_bg": "#1a252f",
                "header_fg": "#ecf0f1",
                "button_bg": "#2980b9",
                "button_hover": "#3498db",
                "day_label_bg": "#34495e",
                "day_label_fg": "#ecf0f1",
                "cell_bg": "#34495e",
                "cell_border": "#7f8c8d",
                "time_label_fg": "#95a5a6"
            }
        else:
            self.colors = {
                "bg": "#f5f5f5",
                "header_bg": "#2c3e50",
                "header_fg": "#ffffff",
                "button_bg": "#3498db",
                "button_hover": "#2980b9",
                "day_label_bg": "#34495e",
                "day_label_fg": "#ffffff",
                "cell_bg": "#ffffff",
                "cell_border": "#bdc3c7",
                "time_label_fg": "#7f8c8d"
            }
        
        # Recreate UI with new colors
        messagebox.showinfo("Dark Mode", "Please restart the app to see full dark mode changes.\n(Dynamic switching requires UI rebuild)")
    
    def _change_week(self, offset):
        # Change which week is being displayed.
        if offset == 0:
            self.current_week_offset = 0
        else:
            self.current_week_offset += offset
        
        # Update week label
        if self.current_week_offset == 0:
            self.week_label.config(text="Current Week")
        elif self.current_week_offset > 0:
            self.week_label.config(text=f"+{self.current_week_offset} Week{'s' if self.current_week_offset > 1 else ''}")
        else:
            self.week_label.config(text=f"{self.current_week_offset} Week{'s' if self.current_week_offset < -1 else ''}")
        
        self.render_sessions()
    
    def _load_templates(self):
        # Load session templates from file.
        template_file = Path(__file__).parent / "session_templates.json"
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                return [item for item in loaded if isinstance(item, dict)]
            return []
        except FileNotFoundError:
            return []
        except Exception as exc:
            self._log_exception("Template load failed", exc)
            return []
    
    def _save_templates(self):
        # Save session templates to file.
        template_file = Path(__file__).parent / "session_templates.json"
        try:
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(self.session_templates, f, indent=2)
        except Exception as e:
            self._show_user_error("Template Error", "Could not save templates.", e)
    
    def _manage_templates(self):
        # Dialog for managing session templates.
        dialog = tk.Toplevel(self.root)
        dialog.title("Session Templates")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        
        tk.Label(dialog, text="Session Templates", font=("Segoe UI", 14, "bold")).pack(pady=10)
        tk.Label(dialog, text="Save frequently used session configurations", font=("Segoe UI", 9)).pack()
        
        listbox = tk.Listbox(dialog, font=("Segoe UI", 10), height=10)
        listbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        for template in self.session_templates:
            listbox.insert(tk.END, f"{template.get('name')} - {template.get('subject')}")
        
        def use_template():
            selection = listbox.curselection()
            if selection:
                template = self.session_templates[selection[0]]
                self.add_session_popup(template)
                dialog.destroy()
        
        def save_new_template():
            # Simple dialog to save current session as template
            name = simpledialog.askstring("Template Name", "Enter a name for this template:", parent=dialog)
            if name:
                template = {
                    "name": name,
                    "subject": "New Subject",
                    "duration": "1:30",
                    "color": "#AED6F1"
                }
                self.session_templates.append(template)
                self._save_templates()
                listbox.insert(tk.END, f"{name} - New Subject")
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Use Template", command=use_template, font=("Segoe UI", 10),
                 bg=self.colors["button_bg"], fg="#ffffff", padx=15, pady=5).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save New", command=save_new_template, font=("Segoe UI", 10),
                 padx=15, pady=5).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Close", command=dialog.destroy, font=("Segoe UI", 10),
                 padx=15, pady=5).pack(side="left", padx=5)
    
    def _manage_goals(self):
        # Dialog for setting study goals.
        dialog = tk.Toplevel(self.root)
        dialog.title("Study Goals")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Set Your Study Goals", font=("Segoe UI", 14, "bold")).pack(pady=15)
        
        frame = tk.Frame(dialog)
        frame.pack(pady=20)
        
        tk.Label(frame, text="Weekly Study Hours Goal:", font=("Segoe UI", 11)).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        
        hours_var = tk.StringVar(value=str(self.study_goals.get("weekly_hours", 20)))
        hours_entry = tk.Entry(frame, textvariable=hours_var, font=("Segoe UI", 11), width=10)
        hours_entry.grid(row=0, column=1, padx=10, pady=10)
        
        def save_goals():
            try:
                hours = float(hours_var.get())
                if hours <= 0:
                    raise ValueError
                self.study_goals["weekly_hours"] = hours
                messagebox.showinfo("Saved", "Study goals updated successfully!")
                dialog.destroy()
            except (TypeError, ValueError):
                messagebox.showerror("Error", "Please enter a valid positive number.")
        
        tk.Button(dialog, text="Save Goals", command=save_goals, font=("Segoe UI", 11, "bold"),
                 bg=self.colors["button_bg"], fg="#ffffff", padx=30, pady=10).pack(pady=10)
    
    def _export_json(self):
        # Export sessions to JSON file.
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Sessions"
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self._sanitize_sessions(self.sessions), f, indent=2)
                messagebox.showinfo("Export Successful", f"Sessions exported to {file_path}")
        except Exception as exc:
            self._show_user_error("Export Error", "Could not export your schedule.", exc)
    
    def _import_json(self):
        # Import sessions from JSON file.
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Import Sessions"
            )
            if not file_path:
                return

            with open(file_path, "r", encoding="utf-8") as f:
                imported = json.load(f)

            if not isinstance(imported, list):
                messagebox.showerror("Import Error", "This file does not contain a valid session list.")
                return

            cleaned_import = self._sanitize_sessions(imported, source="import file")
            skipped = len(imported) - len(cleaned_import)
            if not cleaned_import:
                messagebox.showerror("Import Error", "No valid sessions were found in that file.")
                return

            previous_sessions = list(self.sessions)
            self.sessions.extend(cleaned_import)
            if not self._safe_save_sessions(show_error=True):
                self.sessions = previous_sessions
                return

            self.render_sessions()
            summary = f"Imported {len(cleaned_import)} session(s)."
            if skipped:
                summary += f" Skipped {skipped} invalid session(s)."
            messagebox.showinfo("Import Successful", summary)
        except Exception as exc:
            self._show_user_error("Import Error", "Could not import sessions from that file.", exc)
    
    def _break_reminder_settings(self):
        # Dialog for break reminder configuration.
        dialog = tk.Toplevel(self.root)
        dialog.title("Break Reminder Settings")
        dialog.geometry("450x300")
        dialog.transient(self.root)
        
        tk.Label(dialog, text="Break Reminder Settings", font=("Segoe UI", 14, "bold")).pack(pady=15)
        tk.Label(dialog, text="Get reminders to take breaks during long study sessions",
                font=("Segoe UI", 9)).pack()
        
        frame = tk.Frame(dialog)
        frame.pack(pady=20)
        
        enable_var = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="Enable break reminders", variable=enable_var,
                      font=("Segoe UI", 10)).pack(anchor="w", pady=5)
        
        tk.Label(frame, text="Remind me every (minutes):", font=("Segoe UI", 10)).pack(anchor="w", pady=5)
        interval_var = tk.StringVar(value="50")
        tk.Entry(frame, textvariable=interval_var, font=("Segoe UI", 10), width=10).pack(anchor="w", padx=20)
        
        tk.Label(frame, text="Break duration (minutes):", font=("Segoe UI", 10)).pack(anchor="w", pady=5)
        duration_var = tk.StringVar(value="10")
        tk.Entry(frame, textvariable=duration_var, font=("Segoe UI", 10), width=10).pack(anchor="w", padx=20)
        
        tk.Button(dialog, text="Save Settings", command=dialog.destroy,
                 font=("Segoe UI", 11, "bold"), bg=self.colors["button_bg"],
                 fg="#ffffff", padx=30, pady=10).pack(pady=15)
    
    def _show_shortcuts(self):
        # Display keyboard shortcuts help.
        dialog = tk.Toplevel(self.root)
        dialog.title("Keyboard Shortcuts")
        dialog.geometry("450x500")
        dialog.transient(self.root)
        
        tk.Label(dialog, text="⌨️ Keyboard Shortcuts", font=("Segoe UI", 14, "bold")).pack(pady=15)
        
        shortcuts_text = tk.Text(dialog, font=("Segoe UI", 10), wrap="word", bg="#f5f5f5")
        shortcuts_text.pack(fill="both", expand=True, padx=20, pady=10)
        
        shortcuts = [
            ("Ctrl+N", "Add new session"),
            ("Ctrl+E", "Export sessions"),
            ("Ctrl+S", "Show statistics"),
            ("Ctrl+D", "Toggle dark mode"),
            ("Ctrl+F", "Filter by subject"),
            ("Ctrl+Left", "Previous week"),
            ("Ctrl+Right", "Next week"),
            ("Delete", "Delete selected session"),
            ("Double-click session", "Edit session"),
            ("Right-click session", "Context menu"),
        ]
        
        for key, description in shortcuts:
            shortcuts_text.insert(tk.END, f"{key:20} - {description}\n")
        
        shortcuts_text.config(state="disabled")
        
        tk.Button(dialog, text="Close", command=dialog.destroy, font=("Segoe UI", 11),
                 padx=30, pady=8).pack(pady=10)
    
    def _show_about(self):
        # Display about dialog.
        messagebox.showinfo(
            "About Study Planner",
            "📚 Weekly Study Planner v2.0\n\n"
            "A comprehensive study scheduling application\n"
            "with advanced features including:\n\n"
            "• Session editing & recurring events\n"
            "• Statistics & goal tracking\n"
            "• Time conflict detection\n"
            "• Dark mode & multi-week view\n"
            "• Session templates & notes\n"
            "• Export/Import capabilities\n\n"
            "Built with Python & Tkinter"
        )
    
    def _delete_selected_session(self):
        # Delete currently selected/focused session (placeholder for future selection feature).
        messagebox.showinfo("Delete Session", "Right-click or double-click a session on the calendar to delete or edit it.")
    
    def _manage_session_tasks(self, session_id: str):
        # Manage tasks/checklist for a specific session.
        session = next((s for s in self.sessions if s.get("id") == session_id), None)
        if session is None:
            messagebox.showerror("Error", "Session not found.")
            return
        
        # Initialize tasks if not exists
        if "tasks" not in session:
            session["tasks"] = []
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Tasks for {session.get('subject', 'Session')}")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        header = tk.Frame(dialog, bg=self.colors["header_bg"], height=70)
        header.pack(fill="x")
        tk.Label(
            header,
            text=f"📝 Tasks for {session.get('subject', 'Session')}",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors["header_bg"],
            fg="#ffffff"
        ).pack(pady=15)
        
        # Info
        info_frame = tk.Frame(dialog, bg="#f5f5f5")
        info_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(
            info_frame,
            text=f"{session.get('day')} • {session.get('start')} - {session.get('end')}",
            font=("Segoe UI", 10),
            bg="#f5f5f5",
            fg="#7f8c8d"
        ).pack()
        
        # Tasks list frame
        tasks_frame = tk.LabelFrame(dialog, text="Tasks / To-Do Items", font=("Segoe UI", 11, "bold"),
                                   bg="#ffffff", padx=15, pady=15)
        tasks_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Scrollable frame for tasks
        canvas = tk.Canvas(tasks_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(tasks_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Render tasks
        task_vars = []
        
        def render_tasks():
            # Clear existing
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            task_vars.clear()
            
            # Add each task
            for i, task in enumerate(session["tasks"]):
                task_frame = tk.Frame(scrollable_frame, bg="#ffffff", pady=5)
                task_frame.pack(fill="x", padx=5, pady=2)
                
                var = tk.BooleanVar(value=task.get("completed", False))
                task_vars.append((i, var))
                
                def make_toggle(idx, v):
                    return lambda: toggle_task(idx, v)
                
                cb = tk.Checkbutton(
                    task_frame,
                    text=task.get("text", ""),
                    variable=var,
                    font=("Segoe UI", 10),
                    bg="#ffffff",
                    command=make_toggle(i, var),
                    wraplength=350,
                    justify="left"
                )
                cb.pack(side="left", fill="x", expand=True)
                
                def make_delete(idx):
                    return lambda: delete_task(idx)
                
                del_btn = tk.Button(
                    task_frame,
                    text="🗑",
                    command=make_delete(i),
                    font=("Segoe UI", 9),
                    bg="#e74c3c",
                    fg="#ffffff",
                    bd=0,
                    width=3,
                    cursor="hand2"
                )
                del_btn.pack(side="right")
        
        def toggle_task(idx, var):
            session["tasks"][idx]["completed"] = var.get()
            self._safe_save_sessions(show_error=True)
        
        def delete_task(idx):
            if messagebox.askyesno("Delete Task", "Remove this task?"):
                session["tasks"].pop(idx)
                self._safe_save_sessions(show_error=True)
                render_tasks()
        
        def add_task():
            task_text = simpledialog.askstring("New Task", "Enter task description:", parent=dialog)
            if task_text:
                session["tasks"].append({
                    "text": task_text,
                    "completed": False
                })
                self._safe_save_sessions(show_error=True)
                render_tasks()
        
        render_tasks()
        
        # Add task button
        add_btn = tk.Button(
            dialog,
            text="➕ Add Task",
            command=add_task,
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["button_bg"],
            fg="#ffffff",
            padx=20,
            pady=10,
            cursor="hand2"
        )
        add_btn.pack(pady=10)
        
        # Close button
        tk.Button(
            dialog,
            text="Close",
            command=dialog.destroy,
            font=("Segoe UI", 10),
            padx=30,
            pady=8
        ).pack(pady=5)
    
    def _show_archive(self):
        # Show archived/past sessions.
        # Filter sessions that are in the past (for simplicity, show all sessions with date/week info)
        dialog = tk.Toplevel(self.root)
        dialog.title("Session History")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        
        # Header
        header = tk.Frame(dialog, bg=self.colors["header_bg"], height=70)
        header.pack(fill="x")
        tk.Label(
            header,
            text="📚 Session History",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors["header_bg"],
            fg="#ffffff"
        ).pack(pady=15)
        
        # Info
        tk.Label(
            dialog,
            text="All your study sessions organized by subject",
            font=("Segoe UI", 10),
            bg="#f5f5f5",
            fg="#7f8c8d"
        ).pack(pady=10)
        
        # Sessions list
        list_frame = tk.Frame(dialog, bg="#ffffff")
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create treeview for better display
        tree = ttk.Treeview(
            list_frame,
            columns=("subject", "day", "time", "duration", "notes"),
            show="headings",
            height=20
        )
        tree.heading("subject", text="Subject")
        tree.heading("day", text="Day")
        tree.heading("time", text="Time")
        tree.heading("duration", text="Duration")
        tree.heading("notes", text="Notes")
        
        tree.column("subject", width=120)
        tree.column("day", width=100)
        tree.column("time", width=120)
        tree.column("duration", width=80)
        tree.column("notes", width=250)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Populate with sessions
        for session in sorted(self.sessions, key=lambda s: (s.get("day", ""), s.get("start", ""))):
            try:
                start_minutes = self._parse_time_to_minutes(session.get("start", "00:00"))
                end_minutes = self._parse_time_to_minutes(session.get("end", "00:00"))
                duration_mins = end_minutes - start_minutes
                duration_str = f"{duration_mins // 60}h {duration_mins % 60}m"
            except ValueError:
                duration_str = "N/A"
            
            notes = session.get("notes", "")[:50] + ("..." if len(session.get("notes", "")) > 50 else "")
            
            tree.insert("", "end", values=(
                session.get("subject", ""),
                session.get("day", ""),
                f"{session.get('start', '')} - {session.get('end', '')}",
                duration_str,
                notes
            ))
        
        # Stats
        stats_text = f"Total sessions: {len(self.sessions)} • Subjects: {len(set(s.get('subject') for s in self.sessions))}"
        tk.Label(
            dialog,
            text=stats_text,
            font=("Segoe UI", 9, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        ).pack(pady=5)
        
        # Export button
        def export_history():
            self._export_json()
        
        btn_frame = tk.Frame(dialog, bg="#f5f5f5")
        btn_frame.pack(pady=10)
        
        tk.Button(
            btn_frame,
            text="Export History",
            command=export_history,
            font=("Segoe UI", 10),
            bg=self.colors["button_bg"],
            fg="#ffffff",
            padx=20,
            pady=8
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="Close",
            command=dialog.destroy,
            font=("Segoe UI", 10),
            padx=20,
            pady=8
        ).pack(side="left", padx=5)
    
    def _toggle_drag_drop(self):
        # Toggle drag-and-drop functionality.
        self.drag_enabled = not self.drag_enabled
        status = "enabled" if self.drag_enabled else "disabled"
        messagebox.showinfo(
            "Drag & Drop",
            f"Drag & Drop is now {status}.\n\n"
            f"{'Click and drag sessions to move them to different time slots or days.' if self.drag_enabled else 'Feature disabled.'}"
        )
        
        if self.drag_enabled:
            # Re-render with drag bindings
            self._setup_drag_bindings()
    
    def _setup_drag_bindings(self):
        # Setup drag and drop event bindings (simplified version).
        # This is a placeholder for full drag-and-drop implementation
        # Full implementation would require tracking mouse events and updating position
        messagebox.showinfo(
            "Drag & Drop",
            "Full drag-and-drop is a complex feature.\n\n"
            "Current implementation: Use Edit Session to change times/days.\n\n"
            "For advanced drag-and-drop, consider using a canvas-based calendar."
        )
if __name__ == "__main__":
    root = None
    try:
        root = tk.Tk()
        StudyPlannerApp(root)
        root.mainloop()
    except Exception as exc:
        if root is None:
            root = tk.Tk()
            root.withdraw()
        messagebox.showerror("Startup Error", f"The app could not start correctly.\n\nError: {exc}")
