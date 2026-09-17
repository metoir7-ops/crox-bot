import os
import re
import time
import shutil
import tempfile
import subprocess
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ.get("SPLUS_BOT_TOKEN", "").strip()
BASE_URL = f"https://api.splus.ir/bot{TOKEN}"

if not TOKEN:
    raise RuntimeError("SPLUS_BOT_TOKEN environment variable is not set.")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"CROX Downloader Bot is running")

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health server listening on port {port}", flush=True)
    server.serve_forever()


threading.Thread(target=start_health_server, daemon=True).start()

session = requests.Session()


def api(method, data=None, files=None):
    try:
        r = session.post(
            f"{BASE_URL}/{method}",
            data=data,
            files=files,
            timeout=60
        )
        print(f"API {method}: HTTP {r.status_code}", flush=True)
        try:
            result = r.json()
        except Exception:
            print("API response was not JSON:", r.text[:500], flush=True)
            return {"ok": False}
        if not result.get("ok"):
            print(f"API {method} error:", result, flush=True)
        return result
    except Exception as e:
        print(f"API ERROR ({method}): {repr(e)}", flush=True)
        return {"ok": False}


def get_updates(offset=None):
    data = {
        "timeout": 25,
        "limit": 100
    }

    if offset is not None:
        data["offset"] = offset

    result = api("getUpdates", data)
    print("GET UPDATES:", "ok" if result.get("ok") else result, flush=True)
    return result


def send_message(chat_id, text):
    return api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


def send_file(chat_id, path, caption):
    try:
        with open(path, "rb") as f:
            return api(
                "sendDocument",
                {
                    "chat_id": chat_id,
                    "caption": caption
                },
                {
                    "document": f
                }
            )
    except Exception as e:
        print("SEND FILE ERROR:", e)
        return {"ok": False}


def detect_site(url):
    url = url.lower()

    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"

    if "instagram.com" in url:
        return "Instagram"

    if "tiktok.com" in url:
        return "TikTok"

    if "pinterest.com" in url or "pin.it" in url:
        return "Pinterest"

    return None


def download_media(url, folder):
    output = os.path.join(
        folder,
        "%(title).80s.%(ext)s"
    )

    command = [
        "yt-dlp",
        "--no-playlist",
        "-o",
        output,
        url
    ]

    print("DOWNLOAD:", url)

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        return None

    media = []

    for name in os.listdir(folder):
        path = os.path.join(folder, name)

        if os.path.isfile(path):
            media.append(path)

    return media[0] if media else None


def main():
    print("🤖 Downloader Bot فعال شد...", flush=True)

    offset = None

    while True:
        data = get_updates(offset)

        if not data.get("ok"):
            time.sleep(2)
            continue

        for update in data.get("result", []):

            offset = update["update_id"] + 1

            message = update.get("message")

            if not message:
                continue

            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "").strip().strip()

            if not chat_id:
                continue

            if text == "/start":
                send_message(
                    chat_id,
                    "📥 ربات دانلودر آماده‌ست!\\n\\n"
                    "🔗 لینک Instagram، YouTube، TikTok یا Pinterest رو بفرست 👇"
                )
                continue

            site = detect_site(text)

            if not site:
                send_message(
                    chat_id,
                    "❌ لینک معتبر پیدا نشد.\\n\\n"
                    "📸 Instagram\\n"
                    "▶️ YouTube\\n"
                    "🎵 TikTok\\n"
                    "📌 Pinterest"
                )
                continue

            send_message(
                chat_id,
                f"⏳ عشقم، دارم فایلتو آماده می‌کنم 😘\n\n"
                "🕐 حداکثر ۳ دقیقه صبر کن جیگر ❤️"
            )

            folder = tempfile.mkdtemp(
                prefix="crox_download_"
            )

            try:
                path = download_media(
                    text,
                    folder
                )

                if not path:
                    send_message(
                        chat_id,
                        "❌ دانلود انجام نشد.\\n"
                        "ممکنه لینک خصوصی، حذف‌شده یا غیرقابل‌دسترسی باشه."
                    )
                    continue

                send_message(
                    chat_id,
                    "📤 فایلت آماده‌ست عشقم 😘\nدارم برات می‌فرستم جیگر 😜"
                )

                result = send_file(
                    chat_id,
                    path,
                    f"✅ دانلود از {site} انجام شد."
                )

                if not result.get("ok"):
                    send_message(
                        chat_id,
                        "❌ ارسال فایل انجام نشد."
                    )

            except Exception as e:
                print("DOWNLOAD ERROR:", e)

                send_message(
                    chat_id,
                    "❌ هنگام دانلود خطایی رخ داد."
                )

            finally:
                shutil.rmtree(
                    folder,
                    ignore_errors=True
                )


if __name__ == "__main__":
    main()
