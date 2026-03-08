import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime, timedelta

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
        calendar_name = calendar.get("summary", "Calendar")
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


def refresh_events(status_var, events_list):
    creds = sign_in_google()
    events = get_filtered_events(creds)

    events_list.delete(0, tk.END)
    for start, title in events:
        label = f"{start}  |  {title}" if start else title
        events_list.insert(tk.END, label)

    status_var.set(f"Loaded {len(events)} events")


def run_app():
    root = tk.Tk()
    root.title("Vista")

    status_var = tk.StringVar(value="Welcome to Vista")

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Google Sign-In").pack(anchor="w", pady=(0, 8))

    sign_in_button = ttk.Button(frame, text="Sign in with Google")
    events_list = tk.Listbox(frame, width=90, height=18)

    def on_sign_in():
        try:
            refresh_events(status_var, events_list)
            sign_in_button.pack_forget()
        except Exception as exc:
            status_var.set(f"Error: {exc}")

    sign_in_button.configure(command=on_sign_in)

    if is_signed_in():
        sign_in_button.pack_forget()
        try:
            refresh_events(status_var, events_list)
        except Exception as exc:
            status_var.set(f"Error: {exc}")
    else:
        sign_in_button.pack(anchor="w")

    events_list.pack(anchor="w", fill="both", expand=True, pady=(8, 0))
    ttk.Label(frame, textvariable=status_var).pack(anchor="w", pady=(12, 0))

    root.mainloop()
