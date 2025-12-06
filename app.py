import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import uuid

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
        self.sessions = []  # Stores all study sessions as dictionaries

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


# (Main runner moved to bottom so the StudyPlannerApp class contains all its methods)

    # ------------------------------------------------------
    # 1. HEADER SECTION
    # ------------------------------------------------------
    def _create_header(self):
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill="x")

        title_label = ttk.Label(
            header_frame,
            text="Weekly Study Planner",
            font=("Arial", 18, "bold")
        )
        title_label.pack(side="left")

        add_button = ttk.Button(
            header_frame,
            text="Add Session",
            command=self.add_session_popup
        )
        add_button.pack(side="right")

    # ------------------------------------------------------
    # 2. CALENDAR GRID CREATION
    # ------------------------------------------------------
    def _create_calendar_grid(self):
        self.calendar_frame = ttk.Frame(self.root, padding=10)
        self.calendar_frame.pack(fill="both", expand=True)

        # Create day labels (column headers)
        for column_index, day_name in enumerate(self.days):
            label = ttk.Label(
                self.calendar_frame,
                text=day_name,
                font=("Arial", 12, "bold")
            )
            label.grid(row=0, column=column_index, padx=5, pady=5)

        # Generate time slots (helper function)
        self.time_slots = generate_time_slots()

        # Create 7 columns x N time-slot grid cells
        self.slot_frames = []
        for row_offset, (slot_start, slot_end) in enumerate(self.time_slots, start=1):
            row_frames = []

            for column_index in range(7):
                cell = ttk.Frame(
                    self.calendar_frame,
                    width=120,
                    height=60,
                    relief="ridge"
                )
                cell.grid(
                    row=row_offset,
                    column=column_index,
                    padx=3,
                    pady=3,
                    sticky="nsew"
                )

                # Ensure rows/columns expand nicely
                self.calendar_frame.grid_columnconfigure(column_index, weight=1)
                self.calendar_frame.grid_rowconfigure(row_offset, weight=1)

                # Insert time label inside each cell
                displayed_time = f"{format_min(slot_start)}-{format_min(slot_end)}"
                time_label = ttk.Label(cell, text=displayed_time, font=("Arial", 8))
                time_label.place(x=3, y=2)
                time_label.is_time_label = True  # Mark so we don't delete it later

                row_frames.append(cell)

            self.slot_frames.append(row_frames)

    # ------------------------------------------------------
    # 3. ADD SESSION POPUP WINDOW
    # ------------------------------------------------------
    def add_session_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add Study Session")
        popup.geometry("300x350")

        # --- Subject ---
        ttk.Label(popup, text="Subject:").pack(pady=5)
        subject_entry = ttk.Entry(popup)
        subject_entry.pack()

        # --- Day ---
        ttk.Label(popup, text="Day:").pack(pady=5)
        selected_day = tk.StringVar()
        day_dropdown = ttk.Combobox(
            popup,
            textvariable=selected_day,
            values=self.days,
            state="readonly"
        )
        day_dropdown.pack()

        # --- Start Time ---
        ttk.Label(popup, text="Start Time (HH:MM):").pack(pady=5)
        start_entry = ttk.Entry(popup)
        start_entry.pack()

        # --- End Time ---
        ttk.Label(popup, text="End Time (HH:MM):").pack(pady=5)
        end_entry = ttk.Entry(popup)
        end_entry.pack()

        # --- Colour Selection ---
        ttk.Label(popup, text="Color (hex):").pack(pady=5)
        colour_entry = ttk.Entry(popup)
        colour_entry.insert(0, "#AED6F1")
        colour_entry.pack()

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

        ttk.Button(popup, text="Save Session", command=save_session).pack(pady=15)

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

                    event_frame = tk.Frame(parent_cell, bg=colour)
                    event_frame.place(relx=0, rely=0.15, relwidth=1, relheight=0.85)

                    subject_label = tk.Label(
                        event_frame,
                        text=session.get("subject", ""),
                        bg=colour,
                        wraplength=110
                    )
                    subject_label.pack(expand=True, fill="both")
                    # Attach metadata for callbacks
                    event_frame.session_id = session.get("id")
                    event_frame.slot_index = slot_index

                    # Bind right-click and double-click to open delete popup
                    def make_handler(sid, sidx):
                        return lambda e: self._show_delete_popup(sid, sidx)

                    event_frame.bind("<Button-3>", make_handler(session.get("id"), slot_index))
                    event_frame.bind("<Double-Button-1>", make_handler(session.get("id"), slot_index))

                    # Add a small visible options/delete button in the corner so users can discover deletion
                    try:
                        # Small, flat button that matches background color for a subtle control
                        del_btn = tk.Button(
                            event_frame,
                            text="⋯",
                            bg=colour,
                            fg="#333",
                            bd=0,
                            activebackground=colour,
                            command=lambda sid=session.get("id"), sidx=slot_index: self._show_delete_popup(sid, sidx)
                        )
                        # place top-right corner of the event frame
                        del_btn.place(relx=0.78, rely=0.02, relwidth=0.2, relheight=0.18)
                    except Exception:
                        # If placing a button fails for any reason, ignore — interaction via right-click/double-click still works
                        pass

    # ------------------------------------------------------
    # 5. DELETE / SPLIT SESSION HANDLERS
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
