import sys
import re
import threading
from pathlib import Path
from datetime import datetime, timedelta
import customtkinter as ctk

# Set up customtkinter appearance and theme
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Assets path (project root / assets)
_APP_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _APP_DIR.parent / "assets"
_SUN_PNG = _ASSETS_DIR / "sun.png"
_MOON_PNG = _ASSETS_DIR / "moon.png"

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

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
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not credentials_file.exists():
            raise FileNotFoundError("Credentials file doesn't exist")

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0)

    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds

def is_signed_in(token_path="token.json"):
    return Path(token_path).exists()

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


class EventCard(ctk.CTkFrame):
    def __init__(self, master, start_date_str, title, **kwargs):
        super().__init__(
            master, 
            corner_radius=12, 
            fg_color=("#FFFFFF", "#242424"), 
            border_width=1, 
            border_color=("#EAEAEA", "#333333"), 
            **kwargs
        )
        
        # Format the date string
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
            
        # Try to extract subtitle (text in brackets)
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

        # Config Grid
        self.grid_columnconfigure(0, weight=0, minsize=85) # Date column
        self.grid_columnconfigure(1, weight=0, minsize=2)  # Separator
        self.grid_columnconfigure(2, weight=1)             # Title column
        self.grid_rowconfigure(0, weight=1)
        
        # Left Side (Date)
        date_frame = ctk.CTkFrame(self, fg_color="transparent")
        date_frame.grid(row=0, column=0, padx=(10, 5), pady=15, sticky="nsew")
        
        day_label = ctk.CTkLabel(
            date_frame, 
            text=day, 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), 
            text_color=("#1A1A1A", "#E0E0E0")
        )
        day_label.pack(pady=(0, 0))
        
        month_label = ctk.CTkLabel(
            date_frame, 
            text=month, 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), 
            text_color=("#666666", "#A0A0A0")
        )
        month_label.pack(pady=(0, 2))
        
        if time_str:
            time_label = ctk.CTkLabel(
                date_frame, 
                text=time_str, 
                font=ctk.CTkFont(family="Segoe UI", size=9), 
                text_color=("#999999", "#707070")
            )
            time_label.pack()
            
        # Separator
        sep = ctk.CTkFrame(self, width=2, fg_color=("#EAEAEA", "#333333"), corner_radius=0)
        sep.grid(row=0, column=1, pady=18, sticky="ns")
        
        # Right Side (Title)
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=2, padx=(20, 15), pady=15, sticky="nsew")
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text=main_title, 
            font=ctk.CTkFont(family="Segoe UI", size=16), 
            text_color=("#1A1A1A", "#E0E0E0"), 
            justify="left", 
            wraplength=300
        )
        title_label.pack(anchor="w", pady=(0, 2) if subtitle else (8, 0))
        
        if subtitle:
            subtitle_label = ctk.CTkLabel(
                title_frame, 
                text=subtitle, 
                font=ctk.CTkFont(family="Segoe UI", size=12), 
                text_color=("#666666", "#A0A0A0"), 
                justify="left", 
                wraplength=300
            )
            subtitle_label.pack(anchor="w")


class VistaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Vista")
        self.geometry("520x720")
        self.minsize(480, 600)
        
        # Set background color for the main window (Light / Dark)
        self.configure(fg_color=("#F8F9FA", "#171717"))
        
        self.events_data = []
        self.cards = []
        
        self.init_ui()
        
        # Delay event loading to allow UI to render first
        self.after(200, self.load_events)

    def init_ui(self):
        # Header Layout
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=35, pady=(40, 20))
        
        self.header_left = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_left.pack(side="left", fill="both", expand=True)
        
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
        
        # Theme toggle: sun = light theme icon, moon = dark theme icon (from your SVGs)
        self._theme_icon = None
        if _SUN_PNG.exists() and _MOON_PNG.exists():
            try:
                from PIL import Image
                self._theme_icon = ctk.CTkImage(
                    light_image=Image.open(_SUN_PNG),
                    dark_image=Image.open(_MOON_PNG),
                    size=(24, 24),
                )
            except ImportError:
                pass
        
        self.theme_btn = ctk.CTkButton(
            self.header_frame,
            text="" if self._theme_icon else "Theme",
            width=40 if self._theme_icon else 80,
            height=40,
            corner_radius=20,
            fg_color="transparent",
            hover_color=("#E5E5E5", "#2A2A2A"),
            image=self._theme_icon,
            command=self.toggle_theme,
        )
        self.theme_btn.pack(side="right", anchor="n")
        
        # Status Label
        self.status_label = ctk.CTkLabel(
            self, 
            text="Loading...", 
            font=ctk.CTkFont(family="Segoe UI", size=12), 
            text_color=("#666666", "#888888")
        )
        self.status_label.pack(pady=(20, 0))
        
        # Scrollable area for events
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="transparent", 
            corner_radius=0, 
            scrollbar_button_color=("#E0E0E0", "#333333"),
            scrollbar_button_hover_color=("#C0C0C0", "#555555")
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=(25, 15), pady=(0, 20))
        
        # Sign In Button
        self.signin_btn = ctk.CTkButton(
            self, 
            text="Sign in with Google", 
            height=45, 
            corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=("#EAEAEA", "#333333"),
            text_color=("#1A1A1A", "#FFFFFF"),
            hover_color=("#D0D0D0", "#444444"),
            command=self.handle_signin
        )

    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Light":
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def clear_events(self):
        for card in self.cards:
            card.destroy()
        self.cards.clear()

    def handle_signin(self):
        try:
            creds = sign_in_google()
            self.signin_btn.pack_forget()
            self.status_label.pack(pady=(20, 0))
            self.status_label.configure(text="Loading events...")
            # Use a thread to fetch events without freezing the UI
            threading.Thread(target=self.fetch_events_thread, args=(creds,), daemon=True).start()
        except Exception as e:
            self.status_label.pack(pady=(20, 0))
            self.status_label.configure(text=f"Sign-in error: {e}")

    def load_events(self):
        if not is_signed_in():
            self.status_label.pack_forget()
            self.signin_btn.pack(pady=(20, 0), padx=35, fill="x")
            return
            
        try:
            creds = sign_in_google()
            # Use a thread to fetch events
            threading.Thread(target=self.fetch_events_thread, args=(creds,), daemon=True).start()
        except Exception as e:
            self.status_label.configure(text=f"Error loading events: {e}")
            self.signin_btn.pack(pady=(20, 0), padx=35, fill="x")

    def fetch_events_thread(self, creds):
        try:
            events = get_filtered_events(creds)
            # Schedule update on the main thread
            self.after(0, self.update_events_ui, events)
        except Exception as e:
            self.after(0, lambda e=e: self.status_label.configure(text=f"Error: {e}"))

    def update_events_ui(self, events):
        self.events_data = events
        self.clear_events()
        
        if not self.events_data:
            self.status_label.pack(pady=(20, 0))
            self.status_label.configure(text="No events in the upcoming week.")
        else:
            self.status_label.pack_forget()
            for start, title in self.events_data:
                card = EventCard(self.scroll_frame, start, title)
                card.pack(fill="x", pady=(0, 15), padx=(10, 10))
                self.cards.append(card)

def run_app():
    app = VistaApp()
    app.mainloop()
