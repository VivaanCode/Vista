import os
import time
import threading
import json

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY", "")
FEATHERLESS_URL = "https://api.featherless.ai/v1/chat/completions"
FEATHERLESS_MODEL = "Qwen/Qwen3-4B"

APP_DATA_DIR = Path.home() / "Library" / "Application Support" / "Vista"
SCREENSHOT_PATH = APP_DATA_DIR / ".tmp_screenshot.png"
LOG_PATH = APP_DATA_DIR / "monitor_debug.log"

_log_lock = threading.Lock()


def _log(msg):
    with _log_lock:
        try:
            with open(LOG_PATH, "a") as f:
                ts = time.strftime("%H:%M:%S")
                f.write(f"[{ts}] {msg}\n")
        except Exception:
            pass


def _ensure_dir():
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def take_screenshot():
    _ensure_dir()
    try:
        SCREENSHOT_PATH.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        import Quartz
        from PIL import Image

        cg_image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectInfinite,
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault,
        )
        if cg_image is None:
            _log("Quartz: CGWindowListCreateImage returned None")
            return None

        w = Quartz.CGImageGetWidth(cg_image)
        h = Quartz.CGImageGetHeight(cg_image)
        if w == 0 or h == 0:
            _log(f"Quartz: image is {w}x{h}, skipping")
            return None

        row_bytes = Quartz.CGImageGetBytesPerRow(cg_image)
        data_provider = Quartz.CGImageGetDataProvider(cg_image)
        raw_data = Quartz.CGDataProviderCopyData(data_provider)

        img = Image.frombytes("RGBA", (w, h), raw_data, "raw", "BGRA", row_bytes, 1)
        img = img.convert("RGB")
        img.save(str(SCREENSHOT_PATH), "PNG")

        size = SCREENSHOT_PATH.stat().st_size
        _log(f"Screenshot: {w}x{h}, saved {size} bytes")
        return SCREENSHOT_PATH
    except Exception as e:
        _log(f"Screenshot error: {e}")
        return None


def encode_screenshot(path):
    import base64
    from io import BytesIO
    from PIL import Image
    try:
        img = Image.open(path)
        # Downscale for efficiency. Max width/height 1024 to save tokens and bandwidth
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")
        buffered = BytesIO()
        # Save as JPEG to compress size
        img.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str
    except Exception as e:
        _log(f"Encode image error: {e}")
        return ""


def delete_screenshot():
    try:
        SCREENSHOT_PATH.unlink(missing_ok=True)
    except Exception:
        pass


def ask_featherless(task, img_base64):
    import requests as _req

    prompt = (
        f"/no_think\n"
        f"You are an intelligent AI focus monitor. The user is supposed to be focusing on the concept of: '{task}'.\n\n"
        "Look at this screenshot of their computer screen.\n"
        "Analyze the overall concept of what the user is doing based on the image.\n"
        "IMPORTANT RULES:\n"
        "- Evaluate based on CONCEPT. If the activity conceptually aligns with or helps accomplish the task (like researching, studying, writing, reading docs, or coding related to the topic), answer YES.\n"
        "- General productivity tools (search engines, IDEs, code editors, documents) are ON-TASK if used for the concept.\n"
        "- If the core concept of the screen is clearly an unrelated distraction (like playing video games, watching unrelated videos, or browsing social media feeds), answer NO.\n"
        "- Reply with ONLY the single word YES or NO."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                }
            ]
        }
    ]

    try:
        resp = _req.post(
            FEATHERLESS_URL,
            headers={"Authorization": f"Bearer {FEATHERLESS_API_KEY}"},
            json={
                "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
                "messages": messages,
                "max_tokens": 10,
                "temperature": 0.0,
            },
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning", "") or ""
        _log(f"Featherless content={content!r}, reasoning={reasoning[:150]!r}")

        answer = content.strip().upper()
        if not answer and reasoning:
            answer = reasoning.strip().upper()

        if "NO" in answer:
            _log("Verdict: OFF-TASK")
            return False
        if "YES" in answer:
            _log("Verdict: ON-TASK")
            return True

        _log("Verdict: could not parse, assuming on-task")
        return True
    except Exception as e:
        _log(f"Featherless API error: {e}")
        return True


class FocusMonitor:
    INTERVAL = 15

    def __init__(self, task, on_distracted_callback=None, on_permission_needed=None):
        self.task = task
        self.running = False
        self._thread = None
        self._on_distracted = on_distracted_callback
        self._on_permission_needed = on_permission_needed
        self._permission_prompted = False
        self._slack_token = self._load_slack_token()
        
    def _load_slack_token(self):
        try:
            creds_file = APP_DATA_DIR / "slack_token.txt"
            if creds_file.exists():
                return creds_file.read_text().strip()
        except Exception:
            pass
        return None
        
    def _set_slack_status(self, text, emoji):
        if not self._slack_token: return
        try:
            import requests
            url = "https://slack.com/api/users.profile.set"
            headers = {
                "Authorization": f"Bearer {self._slack_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            data = {
                "profile": {
                    "status_text": text,
                    "status_emoji": emoji,
                    "status_expiration": 0
                }
            }
            resp = requests.post(url, headers=headers, json=data, timeout=5)
            _log(f"Slack status update: {resp.json().get('ok', False)}")
        except Exception as e:
            _log(f"Slack status error: {e}")

    def start(self):
        if self.running:
            return
        self.running = True
        _ensure_dir()
        try:
            LOG_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        _log(f"=== Focus Monitor started, task: {self.task!r} ===")
        
        # Set slack status when starting focus
        self._set_slack_status(f"In Focus: {self.task}", ":dart:")
        
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        _log("=== Focus Monitor stopped ===")
        # Clear slack status when stopping focus
        self._set_slack_status("", "")

    def _loop(self):
        while self.running:
            start_time = time.time()
            try:
                _log("--- cycle start ---")
                path = take_screenshot()

                if path is None:
                    _log("No screenshot, skipping")
                else:
                    img_base64 = encode_screenshot(path)
                    
                    # Immediately delete the screenshot from your local computer
                    delete_screenshot()

                    if not img_base64:
                        _log("Failed to encode screenshot, skipping")
                    else:
                        on_task = ask_featherless(self.task, img_base64)
                        if not on_task and self._on_distracted:
                            _log(">>> Triggering distraction callback")
                            self._on_distracted()

            except Exception as e:
                _log(f"Loop error: {e}")

            # Calculate how long the API/screenshot took and sleep the remainder
            # to guarantee exactly 15 seconds between cycles
            elapsed = time.time() - start_time
            sleep_time = max(0, self.INTERVAL - elapsed)
            time.sleep(sleep_time)
