import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys

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
            print("no credentials file found")
            sys.exit(1)

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0)

    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def run_app():
    root = tk.Tk()
    root.title("Vista")

    status_var = tk.StringVar(value="Welcome to Vista: Your smart productivity assistant")

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Google Sign-In").pack(anchor="w", pady=(0, 8))

    def on_sign_in():
        try:
            sign_in_google()
            status_var.set("Signed in with Google")
        except Exception as exc:
            status_var.set(f"Error: {exc}")

    ttk.Button(frame, text="Sign in with Google", command=on_sign_in).pack(anchor="w")

    ttk.Label(frame, textvariable=status_var).pack(anchor="w", pady=(12, 0))

    root.mainloop()
