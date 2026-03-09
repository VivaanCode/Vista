import sys
import os
import re
import io
import math
import threading
import webbrowser
import tkinter as tk
import json
from pathlib import Path
from datetime import datetime, timedelta
import customtkinter as ctk

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.profile",
]

def sign_in_google(credentials_path="credentials.json", token_path="token.json"):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "Install dependencies: pip install google-auth google-auth-oauthlib"
        )

    credentials_file = Path(credentials_path)
    token_file = Path(token_path)
    creds = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            token_file.unlink(missing_ok=True)
            creds = None

    if not creds or not creds.valid:
        if not credentials_file.exists():
            raise FileNotFoundError("Credentials file doesn't exist")

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0)

    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds

def is_signed_in(token_path="token.json"):
    return Path(token_path).exists()

def sign_out(token_path="token.json"):
    p = Path(token_path)
    if p.exists():
        p.unlink()

def get_user_profile(creds):
    try:
        from googleapiclient.discovery import build
        service = build("oauth2", "v2", credentials=creds)
        info = service.userinfo().get().execute()
        return info
    except Exception:
        return {}

def _download_photo(url):
    try:
        import urllib.request
        from PIL import Image
        data = urllib.request.urlopen(url).read()
        return Image.open(io.BytesIO(data))
    except Exception:
        return None

def get_filtered_events(creds):
    try:
        from googleapiclient.discovery import build
    except ModuleNotFoundError:
        raise ModuleNotFoundError("Install dependency: pip install google-api-python-client")

    service = build("calendar", "v3", credentials=creds)
    events = []

    now = datetime.utcnow().isoformat() + "Z"
    next_week = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

    calendars = service.calendarList().list().execute().get("items", [])
    for calendar in calendars:
        calendar_id = calendar.get("id")
        
        page_token = None
        while True:
            response = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    singleEvents=True,
                    maxResults=2500,
                    timeMin=now,
                    timeMax=next_week,
                    pageToken=page_token,
                )
                .execute()
            )

            for item in response.get("items", []):
                title = item.get("summary", "(No title)")
                if "'s birthday" in title.lower():
                    continue

                if item.get("eventType") == "holiday":
                    continue

                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date", "")
                events.append((start, title))

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    events.sort(key=lambda event: event[0])
    return events


class TodoItem(ctk.CTkFrame):
    def __init__(self, master, text, is_done, toggle_callback, delete_callback, **kwargs):
        super().__init__(
            master,
            corner_radius=8,
            fg_color=("#FFFFFF", "#242424"),
            border_width=1,
            border_color=("#EAEAEA", "#333333"),
            **kwargs
        )
        self.text = text
        self.is_done = is_done
        self.toggle_callback = toggle_callback
        self.delete_callback = delete_callback

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        self.checkbox = ctk.CTkCheckBox(
            self, text="", width=24, height=24,
            corner_radius=6, border_width=2,
            fg_color="#22c55e", border_color=("#CCCCCC", "#555555"),
            hover_color="#16a34a",
            command=self._on_toggle
        )
        if self.is_done:
            self.checkbox.select()
        self.checkbox.grid(row=0, column=0, padx=(12, 8), pady=12)

        font_kwargs = {"family": "Segoe UI", "size": 13}
        if self.is_done:
            font_kwargs["overstrike"] = True

        self.label = ctk.CTkLabel(
            self, text=self.text,
            font=ctk.CTkFont(**font_kwargs),
            text_color=("#888888", "#777777") if self.is_done else ("#1A1A1A", "#E0E0E0"),
            anchor="w", justify="left", wraplength=220
        )
        self.label.grid(row=0, column=1, sticky="w", pady=12)

        self.delete_btn = ctk.CTkButton(
            self, text="✕", width=28, height=28, corner_radius=8,
            fg_color="transparent", text_color=("#888888", "#777777"),
            hover_color=("#FFE4E6", "#7F1D1D"),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._on_delete
        )
        self.delete_btn.grid(row=0, column=2, padx=(8, 12), pady=12)

    def _on_toggle(self):
        self.is_done = self.checkbox.get() == 1
        font_kwargs = {"family": "Segoe UI", "size": 13}
        if self.is_done:
            font_kwargs["overstrike"] = True
        self.label.configure(
            font=ctk.CTkFont(**font_kwargs),
            text_color=("#888888", "#777777") if self.is_done else ("#1A1A1A", "#E0E0E0")
        )
        self.toggle_callback(self.text, self.is_done)

    def _on_delete(self):
        self.delete_callback(self.text)


class EventCard(ctk.CTkFrame):
    def __init__(self, master, start_date_str, title, compact=False, is_current=False, **kwargs):
        self.compact = compact
        self.is_current = is_current
        super().__init__(
            master, 
            corner_radius=8 if compact else 12,
            fg_color=("#FFFFFF", "#242424"), 
            border_width=1, 
            border_color=("#D9D9D9", "#3A3A3A") if is_current else ("#EAEAEA", "#333333"),
            **kwargs
        )
        
        day = ""
        month = ""
        time_str = ""
        
        try:
            if "T" in start_date_str:
                dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                day = dt.strftime("%d")
                month = dt.strftime("%b").upper()
                time_str = dt.strftime("%I:%M %p")
            else:
                dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                day = dt.strftime("%d")
                month = dt.strftime("%b").upper()
        except:
            day = start_date_str
            
        subtitle = ""
        main_title = title
        match = re.search(r'\[(.*?)\]', title)
        if match:
            subtitle = f"[{match.group(1)}]"
            main_title = title.replace(subtitle, "").strip()
        else:
            if ":" in main_title:
                parts = main_title.split(":", 1)
                main_title = parts[0].strip()
                subtitle = parts[1].strip()

        date_min_size = 62 if compact else 76
        self.grid_columnconfigure(0, weight=0, minsize=date_min_size)
        self.grid_columnconfigure(1, weight=0, minsize=2)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=0)

        base_pad_y = 6 if compact else 7
        title_wrap = 180 if compact else 300
        day_size = 14 if compact else 18
        month_size = 10 if compact else 11
        time_size = 8 if compact else 9
        title_size = 12 if compact else 16
        subtitle_size = 10 if compact else 12
        
        date_frame = ctk.CTkFrame(self, fg_color="transparent")
        date_frame.grid(row=0, column=0, padx=(8, 4), pady=base_pad_y, sticky="n")

        if compact and is_current:
            current_label = ctk.CTkLabel(
                date_frame,
                text="NOW",
                font=ctk.CTkFont(family="Segoe UI", size=8, weight="bold"),
                text_color=("#444444", "#DDDDDD")
            )
            current_label.pack(pady=(0, 1))
        
        day_label = ctk.CTkLabel(
            date_frame, 
            text=day, 
            font=ctk.CTkFont(family="Segoe UI", size=day_size, weight="bold"), 
            text_color=("#1A1A1A", "#E0E0E0")
        )
        day_label.pack(pady=(0, 0))
        
        month_label = ctk.CTkLabel(
            date_frame, 
            text=month, 
            font=ctk.CTkFont(family="Segoe UI", size=month_size, weight="bold"), 
            text_color=("#666666", "#A0A0A0")
        )
        month_label.pack(pady=(0, 1))
        
        if time_str:
            time_label = ctk.CTkLabel(
                date_frame, 
                text=time_str, 
                font=ctk.CTkFont(family="Segoe UI", size=time_size), 
                text_color=("#999999", "#707070")
            )
            time_label.pack()
            
        sep = ctk.CTkFrame(self, width=2, fg_color=("#EAEAEA", "#333333"), corner_radius=0)
        sep.grid(row=0, column=1, pady=base_pad_y, sticky="ns")
        
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=2, padx=(10, 10), pady=base_pad_y, sticky="nsew")
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text=main_title, 
            font=ctk.CTkFont(family="Segoe UI", size=title_size), 
            text_color=("#1A1A1A", "#E0E0E0"), 
            justify="left", 
            wraplength=title_wrap
        )
        title_label.pack(anchor="w", pady=(0, 1))
        
        if subtitle:
            subtitle_label = ctk.CTkLabel(
                title_frame, 
                text=subtitle, 
                font=ctk.CTkFont(family="Segoe UI", size=subtitle_size), 
                text_color=("#666666", "#A0A0A0"), 
                justify="left", 
                wraplength=title_wrap
            )
            subtitle_label.pack(anchor="w")

        # Force a small minimum height
        self.configure(height=50 if compact else 70)
        self.pack_propagate(False)
        self.grid_propagate(False)


class EventPopup(tk.Toplevel):

    def __init__(self, parent_pill, events_data):
        super().__init__(parent_pill)
        self._pill = parent_pill
        self._closed = False
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        if sys.platform == "darwin":
            self.attributes("-transparent", True)
            self.config(bg="systemTransparent")
        else:
            self.config(bg="#010101")
            self.attributes("-transparentcolor", "#010101")

        is_dark = ctk.get_appearance_mode() == "Dark"
        self._bg = "#2A2A2A" if is_dark else "#FFFFFF"
        self._border = "#404040" if is_dark else "#D8D8D8"
        self._text = "#E8E8E8" if is_dark else "#1A1A1A"
        self._sub = "#999999" if is_dark else "#777777"

        visible = events_data if events_data else []
        row_h = 48
        pad = 14
        btn_h = 38
        popup_w = 310
        content_h = pad + max(len(visible), 1) * row_h + 12 + btn_h + pad
        popup_h = min(content_h, 520)
        r = 14

        px = parent_pill.winfo_x()
        py = parent_pill.winfo_y() + parent_pill.PILL_H + 6
        sx = parent_pill.winfo_screenwidth()
        sy = parent_pill.winfo_screenheight()
        if px + popup_w > sx:
            px = sx - popup_w - 12
        if py + popup_h > sy:
            py = parent_pill.winfo_y() - popup_h - 6
        self.geometry(f"{popup_w}x{popup_h}+{px}+{py}")

        self.canvas = tk.Canvas(self, width=popup_w, height=popup_h, highlightthickness=0, bd=0)
        if sys.platform == "darwin":
            self.canvas.config(bg="systemTransparent")
        else:
            self.canvas.config(bg="#010101")
        self.canvas.pack(fill="both", expand=True)

        self._draw_rounded_rect(1, 1, popup_w - 1, popup_h - 1, r)

        if not visible:
            self.canvas.create_text(
                popup_w // 2, popup_h // 2 - 20,
                text="No upcoming events", fill=self._sub,
                font=("Helvetica", 13),
            )
        else:
            y = pad + 2
            for start_str, title in visible:
                if y + row_h > popup_h - btn_h - pad - 10:
                    self.canvas.create_text(
                        popup_w // 2, y + 14,
                        text=f"+ {len(visible) - visible.index((start_str, title))} more",
                        fill=self._sub, font=("Helvetica", 11),
                    )
                    break

                day, month = "", ""
                try:
                    if "T" in start_str:
                        dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        day, month = dt.strftime("%d"), dt.strftime("%b").upper()
                    else:
                        dt = datetime.strptime(start_str, "%Y-%m-%d")
                        day, month = dt.strftime("%d"), dt.strftime("%b").upper()
                except:
                    day = "?"

                clean_title = title
                m = re.search(r'\[(.*?)\]', clean_title)
                subtitle = ""
                if m:
                    subtitle = f"[{m.group(1)}]"
                    clean_title = clean_title.replace(subtitle, "").strip()

                self.canvas.create_text(
                    28, y + 10, text=day, fill=self._text,
                    font=("Helvetica", 15, "bold"),
                )
                self.canvas.create_text(
                    28, y + 27, text=month, fill=self._sub,
                    font=("Helvetica", 9, "bold"),
                )

                self.canvas.create_line(
                    56, y + 4, 56, y + row_h - 8,
                    fill=self._border, width=1,
                )

                display = clean_title
                if len(display) > 30:
                    display = display[:28] + "..."
                self.canvas.create_text(
                    68, y + (13 if subtitle else 20), text=display,
                    anchor="w", fill=self._text,
                    font=("Helvetica", 13),
                )
                if subtitle:
                    self.canvas.create_text(
                        68, y + 31, text=subtitle, anchor="w",
                        fill=self._sub, font=("Helvetica", 10),
                    )

                y += row_h

        btn_y = popup_h - btn_h - pad + 4
        btn_x1 = pad
        btn_x2 = popup_w - pad
        btn_r = 10
        btn_pts = [
            btn_x1 + btn_r, btn_y,
            btn_x2 - btn_r, btn_y,
            btn_x2, btn_y,
            btn_x2, btn_y + btn_r,
            btn_x2, btn_y + btn_h - btn_r,
            btn_x2, btn_y + btn_h,
            btn_x2 - btn_r, btn_y + btn_h,
            btn_x1 + btn_r, btn_y + btn_h,
            btn_x1, btn_y + btn_h,
            btn_x1, btn_y + btn_h - btn_r,
            btn_x1, btn_y + btn_r,
            btn_x1, btn_y,
            btn_x1 + btn_r, btn_y,
        ]
        btn_fill = "#333333" if is_dark else "#1A1A1A"
        btn_text_col = "#FFFFFF"
        self._btn_id = self.canvas.create_polygon(
            btn_pts, fill=btn_fill, outline=btn_fill, width=1, smooth=True
        )
        self._btn_text_id = self.canvas.create_text(
            popup_w // 2, btn_y + btn_h // 2,
            text="Open Vista", fill=btn_text_col,
            font=("Helvetica", 12, "bold"),
        )
        self._btn_y = btn_y
        self._btn_h = btn_h

        self.attributes("-alpha", 0.96)

        self.canvas.bind("<ButtonPress-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_hover)
        self.bind("<Escape>", lambda e: self._close())
        self._check_focus()

    def _on_click(self, e):
        if e.y >= self._btn_y and e.y <= self._btn_y + self._btn_h:
            self._close()
            self._pill._master.toggle_overlay()

    def _on_hover(self, e):
        if e.y >= self._btn_y and e.y <= self._btn_y + self._btn_h:
            self.canvas.config(cursor="hand2")
        else:
            self.canvas.config(cursor="arrow")

    def _check_focus(self):
        if self._closed:
            return
        try:
            fx, fy = self.winfo_pointerxy()
            in_popup = (self.winfo_rootx() <= fx <= self.winfo_rootx() + self.winfo_width() and
                        self.winfo_rooty() <= fy <= self.winfo_rooty() + self.winfo_height())
            in_pill = (self._pill.winfo_rootx() <= fx <= self._pill.winfo_rootx() + self._pill.winfo_width() and
                       self._pill.winfo_rooty() <= fy <= self._pill.winfo_rooty() + self._pill.winfo_height())
            if not in_popup and not in_pill:
                self._close()
                return
        except:
            pass
        self.after(400, self._check_focus)

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.destroy()
        except:
            pass
        try:
            self._pill._popup = None
            self._pill._update_caret(False)
        except:
            pass

    def _draw_rounded_rect(self, x1, y1, x2, y2, r):
        pts = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
            x1 + r, y1,
        ]
        self.canvas.create_polygon(
            pts, fill=self._bg, outline=self._border, width=1.5, smooth=True
        )


class FloatingPill(tk.Toplevel):

    PILL_H = 44
    RADIUS = 22
    PAD_X = 18

    def __init__(self, master, text="No upcoming events"):
        super().__init__(master)

        self.overrideredirect(True)
        self.attributes("-topmost", True)

        if sys.platform == "darwin":
            self.attributes("-transparent", True)
            self.config(bg="systemTransparent")
        else:
            self.config(bg="#010101")
            self.attributes("-transparentcolor", "#010101")

        self._drag_x = 0
        self._drag_y = 0
        self._moved = False
        self._master = master
        self._popup = None

        is_dark = ctk.get_appearance_mode() == "Dark"
        self._bg_fill = "#2A2A2A" if is_dark else "#FFFFFF"
        self._border_col = "#404040" if is_dark else "#D8D8D8"
        self._text_col = "#E8E8E8" if is_dark else "#1A1A1A"
        self._sub_col = "#888888" if is_dark else "#888888"
        self._caret_col = "#666666" if is_dark else "#AAAAAA"
        self._caret_hover = "#CCCCCC" if is_dark else "#555555"

        display_text = f"  {text}" if text else "  No events"
        feather = "\U0001fab6"

        tmp_font = ("Helvetica", 13, "bold")
        test_c = tk.Canvas(self)
        tid = test_c.create_text(0, 0, text=feather + display_text, font=tmp_font)
        bbox = test_c.bbox(tid)
        text_w = bbox[2] - bbox[0] if bbox else 120
        test_c.destroy()

        caret_zone = 36
        pill_w = text_w + self.PAD_X * 2 + caret_zone + 6
        pill_w = max(pill_w, 180)
        pill_w = min(pill_w, 360)
        self._pill_w = pill_w
        self._caret_x_start = pill_w - caret_zone

        self.geometry(f"{pill_w}x{self.PILL_H}")

        sx = self.winfo_screenwidth()
        self.geometry(f"+{sx - pill_w - 24}+24")

        self.canvas = tk.Canvas(
            self, width=pill_w, height=self.PILL_H,
            highlightthickness=0, bd=0,
        )
        if sys.platform == "darwin":
            self.canvas.config(bg="systemTransparent")
        else:
            self.canvas.config(bg="#010101")
        self.canvas.pack(fill="both", expand=True)

        self._draw_pill(pill_w, self.PILL_H, self.RADIUS)

        self.canvas.create_text(
            self.PAD_X + 2, self.PILL_H // 2,
            text=feather + display_text, anchor="w",
            fill=self._text_col, font=("Helvetica", 13, "bold"),
        )

        sep_x = self._caret_x_start
        self.canvas.create_line(
            sep_x, 10, sep_x, self.PILL_H - 10,
            fill=self._border_col, width=1,
        )

        cx = sep_x + caret_zone // 2
        cy = self.PILL_H // 2
        self._caret_id = self.canvas.create_text(
            cx, cy, text="▼", fill=self._caret_col,
            font=("Helvetica", 10),
        )

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._do_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)

        self.attributes("-alpha", 0.92)

    def _draw_pill(self, w, h, r):
        pts = [
            r, 0,  w - r, 0,  w, 0,  w, r,
            w, h - r,  w, h,  w - r, h,
            r, h,  0, h,  0, h - r,
            0, r,  0, 0,  r, 0,
        ]
        self.canvas.create_polygon(
            pts, fill=self._bg_fill, outline=self._border_col, width=1.5, smooth=True
        )

    def _is_in_caret_zone(self, x):
        return x >= self._caret_x_start

    def _on_motion(self, e):
        if self._is_in_caret_zone(e.x):
            self.canvas.itemconfigure(self._caret_id, fill=self._caret_hover)
            self.canvas.config(cursor="hand2")
        else:
            self.canvas.itemconfigure(self._caret_id, fill=self._caret_col)
            self.canvas.config(cursor="fleur")

    def _on_press(self, e):
        self._press_in_caret = self._is_in_caret_zone(e.x)
        self._drag_x = e.x_root - self.winfo_x()
        self._drag_y = e.y_root - self.winfo_y()
        self._moved = False

    def _do_drag(self, e):
        if self._press_in_caret:
            return
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")
        self._moved = True

    def _on_release(self, e):
        if self._moved:
            return
        self._toggle_popup()

    def _toggle_popup(self):
        if self._popup:
            try:
                self._popup._close()
            except:
                pass
            self._popup = None
            self._update_caret(False)
        else:
            try:
                self._popup = EventPopup(self, self._master.events_data)
                self._update_caret(True)
            except:
                self._popup = None
                self._update_caret(False)

    def _update_caret(self, is_open):
        self.canvas.itemconfigure(self._caret_id, text="▲" if is_open else "▼")

    def _on_enter(self, _e):
        self.attributes("-alpha", 1.0)

    def _on_leave(self, _e):
        if not self._popup:
            self.attributes("-alpha", 0.92)


class VistaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Vista")
        self.geometry("520x780")
        self.minsize(480, 650)
        
        # Try to set window icon
        try:
            import os
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logo.png")
            if os.path.exists(logo_path):
                img = tk.PhotoImage(file=logo_path)
                self.wm_iconphoto(True, img)
        except Exception:
            pass
        
        self.configure(fg_color=("#F8F9FA", "#171717"))
        
        self.events_data = []
        self.cards = []
        self.overlay_mode = False
        self._saved_geometry = ""
        self._saved_minsize = (480, 650)
        self._saved_overrideredirect = False
        self._saved_topmost = False
        self._overlay_alpha_idle = 0.65
        self._overlay_alpha_hover = 0.98
        self._drag_start_x = 0
        self._drag_start_y = 0
        
        self._user_name = ""
        self._user_photo = None
        self._focus_task = ""
        self._focus_monitor = None
        self._nudge_popup = None
        
        self.init_ui()
        
        self.after(200, self.load_events)

    def init_ui(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=35, pady=(40, 12))
        
        self.header_left = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_left.pack(side="left", fill="both", expand=True)
        
        # Try to load the logo
        try:
            from PIL import Image
            import os
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logo.png")
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=img, dark_image=img, size=(30, 30))
                self.title_label = ctk.CTkLabel(
                    self.header_left, 
                    text=" Vista", 
                    image=self.logo_image,
                    compound="left",
                    font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), 
                    text_color=("#1A1A1A", "#FFFFFF")
                )
            else:
                self.title_label = ctk.CTkLabel(
                    self.header_left, 
                    text="🪶 Vista", 
                    font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), 
                    text_color=("#1A1A1A", "#FFFFFF")
                )
        except Exception:
            self.title_label = ctk.CTkLabel(
                self.header_left, 
                text="🪶 Vista", 
                font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), 
                text_color=("#1A1A1A", "#FFFFFF")
            )
            
        self.title_label.pack(anchor="w")
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_left, 
            text="Your upcoming week", 
            font=ctk.CTkFont(family="Segoe UI", size=14), 
            text_color=("#666666", "#888888")
        )
        self.subtitle_label.pack(anchor="w", pady=(2, 0))
        
        self.header_controls = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_controls.pack(side="right", anchor="n")

        self.overlay_btn = ctk.CTkButton(
            self.header_controls,
            text="Overlay",
            width=70, height=28, corner_radius=14,
            fg_color="transparent", border_width=1,
            border_color=("#CECECE", "#3A3A3A"),
            text_color=("#2A2A2A", "#E8E8E8"),
            hover_color=("#ECECEC", "#2D2D2D"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.toggle_overlay,
        )
        self.overlay_btn.pack(side="left", padx=(0, 8), pady=(0, 4))
        
        self.theme_btn = ctk.CTkButton(
            self.header_controls,
            text="", width=28, height=28, corner_radius=14,
            fg_color="transparent",
            hover_color=("#E5E5E5", "#2A2A2A"),
            border_width=1, border_color=("#CECECE", "#3A3A3A"),
            font=ctk.CTkFont(family="Segoe UI Symbol", size=12, weight="bold"),
            command=self.toggle_theme,
        )
        self.theme_btn.pack(side="left", pady=(0, 4))
        self.refresh_theme_button()

        self.profile_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.avatar_label = ctk.CTkLabel(
            self.profile_frame, text="", width=32, height=32,
            corner_radius=16, fg_color=("#E0E0E0", "#333333"),
        )
        self.avatar_label.pack(side="left", padx=(0, 10))

        self.user_name_label = ctk.CTkLabel(
            self.profile_frame, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#1A1A1A", "#E0E0E0"),
        )
        self.user_name_label.pack(side="left")

        self.logout_btn = ctk.CTkButton(
            self.profile_frame, text="Sign out",
            width=65, height=26, corner_radius=13,
            fg_color="transparent", border_width=1,
            border_color=("#D0D0D0", "#3A3A3A"),
            text_color=("#888888", "#888888"),
            hover_color=("#F0E0E0", "#3A2020"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self.handle_logout,
        )
        self.logout_btn.pack(side="right")

        self.focus_frame = ctk.CTkFrame(
            self, fg_color=("#FFFFFF", "#242424"),
            corner_radius=12, border_width=1,
            border_color=("#EAEAEA", "#333333"),
        )

        self.focus_entry = ctk.CTkEntry(
            self.focus_frame,
            placeholder_text="What should you be working on?",
            height=36, corner_radius=10, border_width=0,
            fg_color="transparent",
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        self.focus_entry.pack(side="left", fill="x", expand=True, padx=(12, 6), pady=6)

        self.focus_btn = ctk.CTkButton(
            self.focus_frame, text="Start Focus",
            width=95, height=32, corner_radius=10,
            fg_color=("#1A1A1A", "#E0E0E0"),
            text_color=("#FFFFFF", "#1A1A1A"),
            hover_color=("#333333", "#C0C0C0"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.toggle_focus,
        )
        self.focus_btn.pack(side="right", padx=(0, 6), pady=6)

        self.focus_status = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#22c55e", "#22c55e"),
        )

        self.status_label = ctk.CTkLabel(
            self, text="Loading...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#666666", "#888888"),
        )
        self.status_label.pack(pady=(12, 0))
        
        self.tabview = ctk.CTkTabview(
            self, corner_radius=12,
            fg_color="transparent",
            segmented_button_fg_color=("#EAEAEA", "#333333"),
            segmented_button_selected_color=("#FFFFFF", "#444444"),
            segmented_button_selected_hover_color=("#F5F5F5", "#555555"),
            segmented_button_unselected_color=("#EAEAEA", "#333333"),
            segmented_button_unselected_hover_color=("#DFDFDF", "#444444"),
            text_color=("#1A1A1A", "#E0E0E0")
        )
        self.tabview.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        
        self.tab_calendar = self.tabview.add("Calendar")
        self.tab_todo = self.tabview.add("To-Do")
        self.tab_market = self.tabview.add("Plugins")
        
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.tab_calendar, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=("#E0E0E0", "#333333"),
            scrollbar_button_hover_color=("#C0C0C0", "#555555"),
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)
        self.scroll_frame.columnconfigure(0, weight=1)

        self.todo_scroll = ctk.CTkScrollableFrame(
            self.tab_todo, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=("#E0E0E0", "#333333"),
            scrollbar_button_hover_color=("#C0C0C0", "#555555"),
        )
        self.todo_scroll.pack(fill="both", expand=True, padx=0, pady=(0, 10))
        self.todo_scroll.columnconfigure(0, weight=1)

        self.todo_entry_frame = ctk.CTkFrame(self.tab_todo, fg_color="transparent")
        self.todo_entry_frame.pack(fill="x", side="bottom")

        self.todo_entry = ctk.CTkEntry(
            self.todo_entry_frame, placeholder_text="Add new to-do...",
            height=36, corner_radius=10, border_width=1,
            fg_color=("#FFFFFF", "#242424"), border_color=("#EAEAEA", "#333333")
        )
        self.todo_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.todo_entry.bind("<Return>", lambda e: self.add_todo())

        self.todo_add_btn = ctk.CTkButton(
            self.todo_entry_frame, text="Add", width=60, height=36,
            corner_radius=10, fg_color=("#1A1A1A", "#E0E0E0"),
            text_color=("#FFFFFF", "#1A1A1A"), hover_color=("#333333", "#C0C0C0"),
            command=self.add_todo
        )
        self.todo_add_btn.pack(side="right")

        # --- Marketplace / Plugins Tab ---
        self.market_scroll = ctk.CTkScrollableFrame(
            self.tab_market, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=("#E0E0E0", "#333333"),
            scrollbar_button_hover_color=("#C0C0C0", "#555555"),
        )
        self.market_scroll.pack(fill="both", expand=True, padx=0, pady=0)
        self.market_scroll.columnconfigure(0, weight=1)

        apps = [
            {"name": "Slack", "desc": "Update status to 'In Focus'", "icon": "💬"},
        ]

        for i, app in enumerate(apps):
            card = ctk.CTkFrame(
                self.market_scroll, fg_color=("#FFFFFF", "#242424"),
                corner_radius=10, border_width=1, border_color=("#EAEAEA", "#333333")
            )
            card.pack(fill="x", padx=10, pady=(0, 10), anchor="n")
            
            card.grid_columnconfigure(0, weight=0)
            card.grid_columnconfigure(1, weight=1)
            card.grid_columnconfigure(2, weight=0)
            
            icon_label = ctk.CTkLabel(
                card, text=app["icon"], font=ctk.CTkFont(size=24)
            )
            icon_label.grid(row=0, column=0, rowspan=2, padx=(15, 10), pady=15)
            
            name_label = ctk.CTkLabel(
                card, text=app["name"], 
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=("#1A1A1A", "#E0E0E0")
            )
            name_label.grid(row=0, column=1, sticky="w", pady=(12, 0))
            
            desc_label = ctk.CTkLabel(
                card, text=app["desc"], 
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=("#666666", "#A0A0A0")
            )
            desc_label.grid(row=1, column=1, sticky="w", pady=(0, 12))
            
            connect_btn = ctk.CTkButton(
                card, text="Connect", width=70, height=28, corner_radius=8,
                fg_color=("#F0F0F0", "#333333"), text_color=("#1A1A1A", "#FFFFFF"),
                hover_color=("#E0E0E0", "#444444"),
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                command=lambda n=app["name"]: self.show_integration_prompt(n)
            )
            connect_btn.grid(row=0, column=2, rowspan=2, padx=(10, 15))
        
        self.signin_btn = ctk.CTkButton(
            self, text="Sign in with Google",
            height=45, corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=("#EAEAEA", "#333333"),
            text_color=("#1A1A1A", "#FFFFFF"),
            hover_color=("#D0D0D0", "#444444"),
            command=self.handle_signin,
        )
        
        self._floating_text_value = "No upcoming events"
        self._pill_window = None
        
        self.todos = []
        self.todo_widgets = []
        self.load_todos()

    def get_todos_file_path(self):
        app_dir = Path.home() / "Library" / "Application Support" / "Vista"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "todos.json"

    def load_todos(self):
        try:
            path = self.get_todos_file_path()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.todos = json.load(f)
        except Exception:
            self.todos = []
        self.render_todos()

    def save_todos(self):
        try:
            path = self.get_todos_file_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.todos, f)
        except Exception:
            pass
        self.sync_tasks()

    def render_todos(self):
        for widget in self.todo_widgets:
            widget.destroy()
        self.todo_widgets.clear()
        
        if not self.todos:
            label = ctk.CTkLabel(
                self.todo_scroll, text="No tasks yet. Add one below!",
                text_color=("#888888", "#777777"),
                font=ctk.CTkFont(family="Segoe UI", size=13)
            )
            label.pack(pady=20)
            self.todo_widgets.append(label)
        else:
            for item in self.todos:
                # Provide a default empty string if 'text' or 'is_done' is missing
                task_text = item.get("text", "")
                task_is_done = item.get("is_done", False)
                if not task_text:
                    continue
                    
                todo_ui = TodoItem(
                    self.todo_scroll,
                    text=task_text,
                    is_done=task_is_done,
                    toggle_callback=self.toggle_todo,
                    delete_callback=self.delete_todo
                )
                todo_ui.pack(fill="x", padx=10, pady=(0, 8), anchor="n")
                self.todo_widgets.append(todo_ui)

    def add_todo(self):
        text = self.todo_entry.get().strip()
        if not text:
            return
        self.todos.append({"text": text, "is_done": False})
        self.todo_entry.delete(0, "end")
        self.save_todos()
        self.render_todos()

    def toggle_todo(self, text, is_done):
        for item in self.todos:
            if item.get("text") == text:
                item["is_done"] = is_done
                break
        self.save_todos()

    def delete_todo(self, text):
        self.todos = [item for item in self.todos if item.get("text") != text]
        self.save_todos()
        self.render_todos()

    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Light":
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")
        self.refresh_theme_button()
        self.refresh_overlay_button()

    def show_integration_prompt(self, app_name):
        if app_name == "Slack":
            self.show_slack_prompt()
            return
            
        popup = ctk.CTkToplevel(self)
        popup.title(f"Connect {app_name}")
        popup.attributes("-topmost", True)
        popup.geometry("380x200")
        popup.resizable(False, False)
        
        try:
            popup.update_idletasks()
            sw = popup.winfo_screenwidth()
            sh = popup.winfo_screenheight()
            w, h = 380, 200
            x = int((sw - w) / 2)
            y = int((sh - h) / 3)
            popup.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass
            
        frame = ctk.CTkFrame(popup, corner_radius=12, fg_color=("#FFFFFF", "#242424"))
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        
        title = ctk.CTkLabel(
            frame, text=f"Connect to {app_name}",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        title.pack(pady=(10, 5))
        
        desc = ctk.CTkLabel(
            frame, text=f"To connect {app_name}, you'll need to provide an API key or OAuth token. This feature is coming soon!",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#666666", "#A0A0A0"),
            wraplength=300, justify="center"
        )
        desc.pack(pady=(5, 15))
        
        btn = ctk.CTkButton(
            frame, text="Close", width=100, height=32, corner_radius=8,
            command=popup.destroy
        )
        btn.pack()
        
        popup.grab_set()
        popup.focus_set()

    def _slack_oauth_flow(self, popup, app_dir, creds_file, client_id, client_secret):
        import urllib.parse
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import json
        
        status_label = None
        for child in popup.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ctk.CTkLabel) and subchild.cget("text").startswith("Connecting"):
                        status_label = subchild
                        
        if not status_label:
            return

        redirect_uri = "https://localhost:8888/callback"
        auth_url = (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}"
            f"&user_scope=users.profile:write"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        )
        
        auth_code = {"code": None}

        class OAuthHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass
            def do_GET(self):
                if self.path.startswith("/callback"):
                    query = urllib.parse.urlparse(self.path).query
                    params = urllib.parse.parse_qs(query)
                    if "code" in params:
                        auth_code["code"] = params["code"][0]
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        html = (
                            "<html><body style='font-family:sans-serif;text-align:center;padding-top:50px;'>"
                            "<h2>Success!</h2><p>Slack connected. You can close this window and return to Vista.</p>"
                            "<script>setTimeout(window.close, 3000);</script>"
                            "</body></html>"
                        )
                        self.wfile.write(html.encode("utf-8"))
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b"Authorization failed.")
                else:
                    self.send_response(404)
                    self.end_headers()

        def _run_server():
            try:
                import ssl
                server = HTTPServer(('localhost', 8888), OAuthHandler)
                
                # Create a self-signed cert on the fly or use existing ones if you have them, 
                # but to avoid permission issues, we'll try standard ad-hoc SSL
                try:
                    import tempfile
                    from pathlib import Path
                    import subprocess
                    
                    # Generate a quick self-signed cert to use for https://localhost
                    cert_dir = Path(tempfile.gettempdir())
                    cert_path = cert_dir / "localhost.pem"
                    key_path = cert_dir / "localhost-key.pem"
                    
                    if not cert_path.exists():
                        subprocess.run([
                            "openssl", "req", "-x509", "-newkey", "rsa:2048",
                            "-keyout", str(key_path), "-out", str(cert_path),
                            "-days", "1", "-nodes", "-subj", "/CN=localhost"
                        ], check=True, capture_output=True)
                        
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
                    server.socket = context.wrap_socket(server.socket, server_side=True)
                except Exception as ssl_e:
                    print("SSL Warning (falling back to http if allowed by Slack, though requested https):", ssl_e)
                
                while auth_code["code"] is None:
                    server.handle_request()
                server.server_close()
                
                # Exchange code for token
                import requests
                resp = requests.post(
                    "https://slack.com/api/oauth.v2.access",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": auth_code["code"],
                        "redirect_uri": redirect_uri
                    }
                )
                data = resp.json()
                if data.get("ok") and "authed_user" in data:
                    token = data["authed_user"].get("access_token")
                    if token:
                        app_dir.mkdir(parents=True, exist_ok=True)
                        creds_file.write_text(token)
                        self.after(0, popup.destroy)
                        return
                
                self.after(0, lambda: status_label.configure(
                    text=f"Auth error: {data.get('error', 'unknown')}", text_color=("#ef4444", "#ef4444")
                ))
            except Exception as e:
                self.after(0, lambda e=e: status_label.configure(
                    text=f"Failed to connect: {e}", text_color=("#ef4444", "#ef4444")
                ))

        import threading
        threading.Thread(target=_run_server, daemon=True).start()
        webbrowser.open(auth_url)

    def show_slack_prompt(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Connect Slack")
        popup.attributes("-topmost", True)
        popup.geometry("450x300")
        popup.resizable(False, False)
        
        try:
            popup.update_idletasks()
            sw = popup.winfo_screenwidth()
            sh = popup.winfo_screenheight()
            w, h = 450, 300
            x = int((sw - w) / 2)
            y = int((sh - h) / 3)
            popup.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass
            
        frame = ctk.CTkFrame(popup, corner_radius=12, fg_color=("#FFFFFF", "#242424"))
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        
        title = ctk.CTkLabel(
            frame, text="Connect Slack",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        title.pack(pady=(5, 5))
        
        desc = ctk.CTkLabel(
            frame, text="To enable 1-click Sign In, paste your Client ID and Client Secret from your Slack app's 'Basic Information' page.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#666666", "#A0A0A0"),
            wraplength=350, justify="center"
        )
        desc.pack(pady=(0, 15))
        
        id_entry = ctk.CTkEntry(
            frame, placeholder_text="Client ID...", width=300, height=36,
            corner_radius=8, border_width=1,
            fg_color=("#F5F5F5", "#1A1A1A"), border_color=("#EAEAEA", "#333333"),
        )
        id_entry.pack(pady=(0, 10))
        
        sec_entry = ctk.CTkEntry(
            frame, placeholder_text="Client Secret...", width=300, height=36,
            corner_radius=8, border_width=1,
            fg_color=("#F5F5F5", "#1A1A1A"), border_color=("#EAEAEA", "#333333"),
            show="*"
        )
        sec_entry.pack(pady=(0, 15))
        
        app_dir = Path.home() / "Library" / "Application Support" / "Vista"
        creds_file = app_dir / "slack_token.txt"
        
        status_label = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(family="Segoe UI", size=12))
        status_label.pack(pady=(0, 10))
        
        def start_oauth():
            c_id = id_entry.get().strip()
            c_sec = sec_entry.get().strip()
            if not c_id or not c_sec:
                status_label.configure(text="Please enter both ID and Secret", text_color=("#ef4444", "#ef4444"))
                return
            
            status_label.configure(text="Connecting...", text_color=("#22c55e", "#22c55e"))
            self._slack_oauth_flow(popup, app_dir, creds_file, c_id, c_sec)
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack()
        
        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel", width=80, height=32, corner_radius=8,
            fg_color="transparent", border_width=1, border_color=("#D0D0D0", "#3A3A3A"),
            text_color=("#1A1A1A", "#FFFFFF"), hover_color=("#E0E0E0", "#444444"),
            command=popup.destroy
        )
        cancel_btn.pack(side="left", padx=5)
        
        save_btn = ctk.CTkButton(
            btn_frame, text="Sign in with Slack", width=140, height=32, corner_radius=8,
            fg_color=("#1A1A1A", "#E0E0E0"), text_color=("#FFFFFF", "#1A1A1A"),
            hover_color=("#333333", "#C0C0C0"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=start_oauth
        )
        save_btn.pack(side="left", padx=5)
        
        popup.grab_set()
        popup.focus_set()

    def refresh_theme_button(self):
        mode = ctk.get_appearance_mode()
        if mode == "Light":
            self.theme_btn.configure(text="☀", text_color="#111111")
        else:
            self.theme_btn.configure(text="☾", text_color="#F5F5F5")

    def refresh_overlay_button(self):
        if self.overlay_mode:
            self.overlay_btn.configure(text="Docked")
        else:
            self.overlay_btn.configure(text="Overlay")

    def _show_profile(self, creds):
        def _fetch():
            info = get_user_profile(creds)
            name = info.get("name", "")
            photo_url = info.get("picture", "")
            
            # The Google API returns 'id', which corresponds to the JWT 'sub'
            self._user_sub = info.get("id") or info.get("sub")
            
            if self._user_sub:
                import requests
                try:
                    payload = {"sub": self._user_sub, "email": info.get("email", "")}
                    resp = requests.post("https://server.tryvista.live/addSub", json=payload, timeout=5)
                    data = resp.json()
                    if data.get("status") == "failure":
                        print(f"Server error: {data.get('error')}")
                    else:
                        self.after(0, lambda: self.status_label.configure(
                            text="Syncing started...", text_color=("#22c55e", "#22c55e")
                        ))
                except Exception as e:
                    print(f"Error notifying server: {e}")
            
            # Try loading tasks from server first
            if hasattr(self, "_user_sub") and self._user_sub:
                self.fetch_tasks_from_server()
            
            photo_img = _download_photo(photo_url) if photo_url else None
            self.after(0, lambda: self._apply_profile(name, photo_img))
        threading.Thread(target=_fetch, daemon=True).start()

    def fetch_tasks_from_server(self):
        if not hasattr(self, "_user_sub") or not self._user_sub:
            return
            
        def _do_fetch():
            import requests
            try:
                payload = {"sub": self._user_sub}
                resp = requests.post("https://server.tryvista.live/getTasks", json=payload, timeout=5)
                data = resp.json()
                if data.get("status") == "success" and "tasks" in data:
                    server_tasks = data["tasks"]
                    
                    # Normalize server tasks to match python format
                    normalized_server_tasks = []
                    for t in server_tasks:
                        text_val = t.get("text") or t.get("title") or ""
                        done_val = t.get("is_done") or t.get("isCompleted") or False
                        if text_val:
                            normalized_server_tasks.append({"text": text_val, "is_done": done_val})
                            
                    server_task_texts = {t.get("text") for t in normalized_server_tasks}
                    merged_tasks = list(normalized_server_tasks)
                    
                    for local_t in self.todos:
                        # Normalize local tasks too, just in case
                        l_text = local_t.get("text") or local_t.get("title") or ""
                        l_done = local_t.get("is_done") or local_t.get("isCompleted") or False
                        if l_text and l_text not in server_task_texts:
                            merged_tasks.append({"text": l_text, "is_done": l_done})
                            
                    self.todos = merged_tasks
                    
                    # Save back to local cache
                    path = self.get_todos_file_path()
                    with open(path, "w", encoding="utf-8") as f:
                        import json
                        json.dump(self.todos, f)
                        
                    self.after(0, self.render_todos)
                    
                    # Immediately sync the merged list back up
                    self.sync_tasks()
                else:
                    # If error or no tasks, fallback to local tasks
                    self.sync_tasks()
            except Exception as e:
                print(f"Failed to fetch tasks from server: {e}")
                self.sync_tasks()
                
        threading.Thread(target=_do_fetch, daemon=True).start()

    def sync_tasks(self):
        if not hasattr(self, "_user_sub") or not self._user_sub:
            return
            
        def _do_sync():
            import requests
            try:
                # Need to convert boolean values correctly for python->json
                import json
                tasks_safe = [
                    {"text": str(t.get("text", "")), "is_done": bool(t.get("is_done", False))} 
                    for t in self.todos if t.get("text")
                ]
                payload = {
                    "sub": str(self._user_sub),
                    "tasks": tasks_safe
                }
                
                resp = requests.post("https://server.tryvista.live/updateTasks", json=payload, timeout=5)
                data = resp.json()
                if data.get("status") == "failure":
                    print(f"Task sync error: {data.get('error')}")
                else:
                    print("Tasks synced successfully")
            except Exception as e:
                print(f"Task sync failed: {e}")
                
        threading.Thread(target=_do_sync, daemon=True).start()

    def _apply_profile(self, name, photo_img):
        self._user_name = name
        if photo_img:
            try:
                photo_img = photo_img.resize((32, 32))
                self._user_photo = ctk.CTkImage(light_image=photo_img, dark_image=photo_img, size=(32, 32))
                self.avatar_label.configure(image=self._user_photo, text="")
            except Exception:
                self.avatar_label.configure(text=name[:1].upper() if name else "?")
        else:
            self.avatar_label.configure(text=name[:1].upper() if name else "?")
        self.user_name_label.configure(text=name if name else "Signed in")
        self.profile_frame.pack(fill="x", padx=35, pady=(0, 8), after=self.header_frame)
        self.focus_frame.pack(fill="x", padx=35, pady=(0, 8), after=self.profile_frame)

    def handle_logout(self):
        if self._focus_monitor:
            self._focus_monitor.stop()
            self._focus_monitor = None
            self.focus_btn.configure(text="Start Focus")
            self.focus_status.pack_forget()
        sign_out()
        self._user_name = ""
        self._user_photo = None
        self.profile_frame.pack_forget()
        self.focus_frame.pack_forget()
        self.focus_status.pack_forget()
        self.events_data = []
        self.clear_events()
        self.status_label.pack_forget()
        self.signin_btn.pack(pady=(20, 0), padx=35, fill="x")

    def toggle_focus(self):
        if self._focus_monitor and self._focus_monitor.running:
            self._focus_monitor.stop()
            self._focus_monitor = None
            self.focus_btn.configure(
                text="Start Focus",
                fg_color=("#1A1A1A", "#E0E0E0"),
                text_color=("#FFFFFF", "#1A1A1A"),
            )
            self.focus_status.pack_forget()
            return

        task = self.focus_entry.get().strip()
        if not task:
            self.focus_entry.configure(placeholder_text="Please type what you're working on!")
            return

        self._focus_task = task
        try:
            from app.monitor import FocusMonitor
        except ImportError:
            self.focus_status.configure(text="Monitor module not found", text_color=("#ef4444", "#ef4444"))
            self.focus_status.pack(padx=35, anchor="w", pady=(0, 4), after=self.focus_frame)
            return

        def on_distracted():
            def _do():
                self._show_focus_nudge()
                webbrowser.open("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTuTdiscNAFvZzY_JpIU7AvrZfqLDqfUowm2g&s")
            self.after(0, _do)

        self._focus_monitor = FocusMonitor(
            task=task,
            on_distracted_callback=on_distracted,
        )
        self._focus_monitor.start()

        self.focus_btn.configure(
            text="● 00:00",
            fg_color=("#ef4444", "#ef4444"),
            text_color=("#FFFFFF", "#FFFFFF"),
        )
        
        import time
        self._focus_start_time = time.time()
        self._update_focus_timer()

    def _update_focus_timer(self):
        if self._focus_monitor and self._focus_monitor.running:
            import time
            elapsed = int(time.time() - self._focus_start_time)
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            time_str = f"● {hours:02d}:{mins:02d}:{secs:02d}" if hours > 0 else f"● {mins:02d}:{secs:02d}"
            
            self.focus_btn.configure(text=time_str)
                
            self.after(1000, self._update_focus_timer)

    def _show_focus_nudge(self):
        if self._nudge_popup is not None:
            try:
                if self._nudge_popup.winfo_exists():
                    self._nudge_popup.destroy()
            except Exception:
                pass
            self._nudge_popup = None

        if self.overlay_mode:
            self.disable_overlay_mode()
        self.deiconify()
        self.lift()
        try:
            self.focus_force()
        except Exception:
            pass

        popup = ctk.CTkToplevel(self)
        self._nudge_popup = popup
        popup.title("Focus")
        popup.attributes("-topmost", True)
        popup.geometry("420x220")
        popup.resizable(False, False)
        popup.configure(fg_color=("#000000", "#000000"))

        try:
            popup.update_idletasks()
            sw = popup.winfo_screenwidth()
            sh = popup.winfo_screenheight()
            w, h = 420, 220
            x = int((sw - w) / 2)
            y = int((sh - h) / 3)
            popup.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        frame = ctk.CTkFrame(
            popup,
            corner_radius=18,
            fg_color=("#FFFFFF", "#171717"),
        )
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        title = ctk.CTkLabel(
            frame,
            text="Get back to work",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=("#1A1A1A", "#F5F5F5"),
        )
        title.pack(pady=(8, 4))

        task_text = self._focus_task or "your focus task"
        subtitle = ctk.CTkLabel(
            frame,
            text=f"You said you should be working on:\n\u201c{task_text}\u201d",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=("#4B5563", "#9CA3AF"),
            wraplength=360,
            justify="center",
        )
        subtitle.pack(pady=(4, 14))

        def _close():
            try:
                popup.destroy()
            except Exception:
                pass
            self._nudge_popup = None

        btn = ctk.CTkButton(
            frame,
            text="I'm back",
            width=120, height=34, corner_radius=999,
            fg_color=("#111827", "#F97316"),
            text_color=("#FFFFFF", "#111827"),
            hover_color=("#1F2937", "#FB923C"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=_close,
        )
        btn.pack(pady=(0, 10))

        try:
            popup.grab_set()
            btn.focus_set()
        except Exception:
            pass

    def toggle_overlay(self):
        if self.overlay_mode:
            self.disable_overlay_mode()
        else:
            self.enable_overlay_mode()

        self.refresh_overlay_button()
        if self.events_data:
            self.update_events_ui(self.events_data)

    def enable_overlay_mode(self):
        self.overlay_mode = True
        self.withdraw()
        self._pill_window = FloatingPill(self, self._floating_text_value)

    def disable_overlay_mode(self):
        self.overlay_mode = False
        if self._pill_window:
            self._pill_window.destroy()
            self._pill_window = None
        self.deiconify()

    def clear_events(self):
        for card in self.cards:
            card.destroy()
        self.cards.clear()

    def handle_signin(self):
        try:
            creds = sign_in_google()
            self.signin_btn.pack_forget()
            self.status_label.pack(pady=(12, 0))
            self.status_label.configure(text="Loading events...")
            self._show_profile(creds)
            threading.Thread(target=self.fetch_events_thread, args=(creds,), daemon=True).start()
        except Exception as e:
            self.status_label.pack(pady=(12, 0))
            self.status_label.configure(text=f"Sign-in error: {e}")

    def load_events(self):
        if not is_signed_in():
            self.status_label.pack_forget()
            self.signin_btn.pack(pady=(20, 0), padx=35, fill="x")
            return
            
        try:
            creds = sign_in_google()
            self._show_profile(creds)
            threading.Thread(target=self.fetch_events_thread, args=(creds,), daemon=True).start()
        except Exception as e:
            self.status_label.configure(text=f"Error loading events: {e}")
            self.signin_btn.pack(pady=(20, 0), padx=35, fill="x")

    def fetch_events_thread(self, creds):
        try:
            events = get_filtered_events(creds)
            self.after(0, self.update_events_ui, events)
        except Exception as e:
            self.after(0, lambda e=e: self.status_label.configure(text=f"Error: {e}"))

    def update_events_ui(self, events):
        self.events_data = events
        self.clear_events()
        
        if not self.events_data:
            self._floating_text_value = "Free today"
            self.status_label.pack(pady=(20, 0))
            self.status_label.configure(text="No events in the upcoming week.")
        else:
            next_title = self.events_data[0][1]
            match = re.search(r'\[(.*?)\]', next_title)
            if match:
                next_title = next_title.replace(f"[{match.group(1)}]", "").strip()
            if ":" in next_title:
                next_title = next_title.split(":", 1)[0].strip()
            if len(next_title) > 22:
                next_title = next_title[:20] + "..."
                
            self._floating_text_value = next_title

            visible_events = self.events_data[:8] if self.overlay_mode else self.events_data
            if self.overlay_mode:
                self.status_label.pack(pady=(0, 6))
                self.status_label.configure(text="Current + upcoming")
            else:
                self.status_label.pack_forget()

            for idx, (start, title) in enumerate(visible_events):
                card = EventCard(
                    self.scroll_frame,
                    start,
                    title,
                    compact=self.overlay_mode,
                    is_current=(idx == 0),
                )
                card.pack(fill="x", expand=False, anchor="n", pady=(0, 6 if self.overlay_mode else 8), padx=(6 if self.overlay_mode else 10, 10))
                self.cards.append(card)

def run_app():
    app = VistaApp()
    app.mainloop()
