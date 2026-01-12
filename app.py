import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import uuid
from datetime import datetime, timedelta

try:
    from . import storage
    from .time_utils import format_min, generate_time_slots
except Exception: 
    import storage
    from time_utils import format_min, generate_time_slots


class StudyPlannerApp:

    def __init__(self, root):
        # Initialise core attributes
        self.root = root
        self.root.title("Study Planner")
        self.root.configure(bg="#f5f5f5")
        self.root.geometry("1400x900")  # Larger default size
        self.sessions = []  # Stores all study sessions as dictionaries
        
        # Reminder tracking: stores which notifications have been sent
        # Format: {session_id: set(['60min', '30min', '0min'])}
        self.sent_reminders = {}
        
        # Modern color scheme
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

        # Days of the week displayed in the calendar
        self.days = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]

        # Build graphical interface
        self._create_header()
        self._create_calendar_grid()

        # Load previous sessions from file (if available)
        try:
            self.sessions = storage.load_sessions()
        except Exception as exc:  # Unexpected problems reading the file
            messagebox.showerror("Load Error", f"Could not load sessions: {exc}")
            self.sessions = []


        self.render_sessions()
        
        # Start the reminder checking loop
        self._check_reminders()


# (Main runner moved to bottom so the StudyPlannerApp class contains all its methods)

    # ------------------------------------------------------
    # 1. HEADER SECTION
    # ------------------------------------------------------
    def _create_header(self):
        header_frame = tk.Frame(self.root, bg=self.colors["header_bg"], height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        # Title with icon
        title_label = tk.Label(
            header_frame,
            text="📚 Weekly Study Planner",
            font=("Segoe UI", 24, "bold"),
            bg=self.colors["header_bg"],
            fg=self.colors["header_fg"]
        )
        title_label.pack(side="left", padx=20, pady=15)
        
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

    # ------------------------------------------------------
    # 2. CALENDAR GRID CREATION
    # ------------------------------------------------------
    def _create_calendar_grid(self):
        # Wrapper for padding and background
        wrapper = tk.Frame(self.root, bg=self.colors["bg"])
        wrapper.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.calendar_frame = tk.Frame(wrapper, bg=self.colors["bg"])
        self.calendar_frame.pack(fill="both", expand=True)

        # Create day labels (column headers) with modern styling
        for column_index, day_name in enumerate(self.days):
            day_frame = tk.Frame(
                self.calendar_frame,
                bg=self.colors["day_label_bg"],
                height=40
            )
            day_frame.grid(row=0, column=column_index, padx=2, pady=(0, 8), sticky="ew")
            day_frame.grid_propagate(False)
            
            label = tk.Label(
                day_frame,
                text=day_name,
                font=("Segoe UI", 13, "bold"),
                bg=self.colors["day_label_bg"],
                fg=self.colors["day_label_fg"]
            )
            label.pack(expand=True)

        self.time_slots = generate_time_slots()

        # Create 7 columns x N time-slot grid cells
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
                time_label.is_time_label = True  # Mark so we don't delete it later

                row_frames.append(cell)

            self.slot_frames.append(row_frames)

    # ------------------------------------------------------
    # 3. ADD SESSION POPUP WINDOW
    # ------------------------------------------------------
    def add_session_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add Study Session")
        popup.geometry("450x620")
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
            except:
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

        # --- Internal function for saving ---
        def save_session():
            subject = subject_entry.get()
            day = selected_day.get()
            start = start_entry.get()
            end = end_entry.get()
            colour = colour_entry.get()

            # Field validation
            if not (subject and day and start and end):
                messagebox.showerror("Error", "Please complete all fields.")
                return

            new_session = {
                "subject": subject,
                "day": day,
                "start": start,
                "end": end,
                "color": colour,
                "id": str(uuid.uuid4())
            }

            self.sessions.append(new_session)

            # Save session to disk
            try:
                storage.save_sessions(self.sessions)
            except Exception as exc:
                messagebox.showerror("Save Error", f"Could not save sessions: {exc}")

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


    # ------------------------------------------------------
    # 4. SESSION RENDERING INTO THE GRID
    # ------------------------------------------------------
    def render_sessions(self):
        # Clear all widgets except the internal time labels
        for row in self.slot_frames:
            for cell in row:
                for child in cell.winfo_children():
                    if getattr(child, "is_time_label", False):
                        continue
                    child.destroy()

        # Place each valid session onto the calendar
        for session in self.sessions:
            try:
                day_index = self.days.index(session.get("day"))
            except ValueError:
                continue  # Skip invalid day strings

            # Convert times to minutes
            try:
                sh, sm = map(int, session.get("start", "00:00").split(":"))
                eh, em = map(int, session.get("end", "00:00").split(":"))
            except Exception:
                continue

            start_minutes = sh * 60 + sm
            end_minutes = eh * 60 + em

            # Check session-slot overlap and render
            for slot_index, (slot_start, slot_end) in enumerate(self.time_slots):
                if start_minutes < slot_end and end_minutes > slot_start:
                    parent_cell = self.slot_frames[slot_index][day_index]
                    colour = session.get("color", "#AED6F1")

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
                        text=session.get("subject", ""),
                        bg=colour,
                        fg=self._get_contrast_color(colour),
                        font=("Segoe UI", 10, "bold"),
                        wraplength=120
                    )
                    subject_label.pack(expand=True, fill="both", padx=5, pady=2)
                    # Attach metadata for callbacks
                    event_frame.session_id = session.get("id")
                    event_frame.slot_index = slot_index

                    # Bind right-click and double-click to open delete popup
                    def make_handler(sid, sidx):
                        return lambda e: self._show_delete_popup(sid, sidx)

                    event_frame.bind("<Button-3>", make_handler(session.get("id"), slot_index))
                    event_frame.bind("<Double-Button-1>", make_handler(session.get("id"), slot_index))
                    subject_label.bind("<Button-3>", make_handler(session.get("id"), slot_index))
                    subject_label.bind("<Double-Button-1>", make_handler(session.get("id"), slot_index))
                    
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
                            command=lambda sid=session.get("id"), sidx=slot_index: self._show_delete_popup(sid, sidx)
                        )
                        del_btn.place(relx=0.85, rely=0.02, relwidth=0.13, relheight=0.20)
                    except Exception:
                        pass

    # ------------------------------------------------------
    # 5. UTILITY METHODS FOR STYLING
    # ------------------------------------------------------
    def _darken_color(self, hex_color: str, factor: float = 0.7) -> str:
        """Darken a hex color by a given factor."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            r, g, b = int(r * factor), int(g * factor), int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return "#2c3e50"
    
    def _get_contrast_color(self, hex_color: str) -> str:
        """Return black or white text color based on background brightness."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if brightness > 128 else "#ffffff"
        except:
            return "#000000"

    # ------------------------------------------------------
    # 6. DELETE / SPLIT SESSION HANDLERS
    # ------------------------------------------------------
    def _show_delete_popup(self, session_id: str, slot_index: int):
        # Find the session object
        session = next((s for s in self.sessions if s.get("id") == session_id), None)
        if session is None:
            messagebox.showerror("Not found", "Session not found (it may have been deleted).")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Remove session block")
        popup.geometry("320x160")

        info = f"Subject: {session.get('subject')}\nDay: {session.get('day')}\nBlock: {format_min(self.time_slots[slot_index][0])} - {format_min(self.time_slots[slot_index][1])}"
        ttk.Label(popup, text=info).pack(pady=8)

        # Remove this block only
        def remove_block():
            self._remove_block_from_session(session_id, slot_index)
            popup.destroy()

        # Remove full session
        def remove_all():
            self._remove_session(session_id)
            popup.destroy()

        ttk.Button(popup, text="Remove this block", command=remove_block).pack(pady=5)
        ttk.Button(popup, text="Remove entire session", command=remove_all).pack(pady=5)
        ttk.Button(popup, text="Cancel", command=popup.destroy).pack(pady=5)

    def _remove_session(self, session_id: str):
        self.sessions = [s for s in self.sessions if s.get("id") != session_id]
        try:
            storage.save_sessions(self.sessions)
        except Exception:
            pass
        self.render_sessions()

    def _remove_block_from_session(self, session_id: str, slot_index: int):
        session = next((s for s in self.sessions if s.get("id") == session_id), None)
        if session is None:
            return

        try:
            sh, sm = map(int, session.get("start", "00:00").split(":"))
            eh, em = map(int, session.get("end", "00:00").split(":"))
        except Exception:
            return

        s_min = sh * 60 + sm
        e_min = eh * 60 + em

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
        self.sessions = [s for s in self.sessions if s.get("id") != session_id]
        self.sessions.extend(new_sessions)

        try:
            storage.save_sessions(self.sessions)
        except Exception:
            pass

        self.render_sessions()

    # ------------------------------------------------------
    # 7. REMINDER SYSTEM
    # ------------------------------------------------------
    def _check_reminders(self):
        """Check for upcoming sessions and send reminders at 1 hour, 30 min, and start time."""
        now = datetime.now()
        current_day = now.strftime("%A")  # e.g., "Monday"
        current_time_minutes = now.hour * 60 + now.minute
        
        for session in self.sessions:
            session_id = session.get("id")
            session_day = session.get("day")
            
            # Only check sessions for today
            if session_day != current_day:
                continue
            
            # Parse session start time
            try:
                start_time = session.get("start", "00:00")
                sh, sm = map(int, start_time.split(":"))
                session_start_minutes = sh * 60 + sm
            except Exception:
                continue
            
            # Calculate time until session starts (in minutes)
            time_until = session_start_minutes - current_time_minutes
            
            # Initialize reminder tracking for this session if needed
            if session_id not in self.sent_reminders:
                self.sent_reminders[session_id] = set()
            
            # Check for 60-minute reminder
            if 59 <= time_until <= 61 and '60min' not in self.sent_reminders[session_id]:
                self._send_reminder(session, "1 hour")
                self.sent_reminders[session_id].add('60min')
            
            # Check for 30-minute reminder
            elif 29 <= time_until <= 31 and '30min' not in self.sent_reminders[session_id]:
                self._send_reminder(session, "30 minutes")
                self.sent_reminders[session_id].add('30min')
            
            # Check for start time reminder
            elif 0 <= time_until <= 1 and '0min' not in self.sent_reminders[session_id]:
                self._send_reminder(session, "now")
                self.sent_reminders[session_id].add('0min')
        
        # Check again in 60 seconds (1 minute)
        self.root.after(60000, self._check_reminders)
    
    def _send_reminder(self, session, time_label):
        """Display a reminder notification for a session."""
        subject = session.get("subject", "Unknown")
        start = session.get("start", "")
        end = session.get("end", "")
        
        if time_label == "now":
            message = f"Your {subject} session is starting now!\n\nTime: {start} - {end}"
            title = "Session Starting!"
        else:
            message = f"Your {subject} session starts in {time_label}.\n\nTime: {start} - {end}"
            title = f"Reminder: {time_label} until session"
        
        messagebox.showinfo(title, message)


# Main runner
if __name__ == "__main__":
    root = tk.Tk()
    app = StudyPlannerApp(root)
    root.mainloop()
