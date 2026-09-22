from flask import Flask, request, jsonify, send_from_directory, abort
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
import re
import os

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

HTML_FILE = "Hafiz_Studio_PRACTICE_SERVER_DOWNLOAD_9347.html"
DOWNLOAD_DIR = BASE_DIR / "hafiz_downloads"

DOWNLOAD_DIR.mkdir(exist_ok=True)


# Full-surah MP3 endpoint used by Hafiz Studio.
def audio_url(surah_id, reciter):
    return (
        f"https://cdn.islamic.network/quran/audio-surah/"
        f"128/{reciter}/{surah_id}.mp3"
    )


def safe_name(name):
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-")
    return name or "Surah"


def downloaded_files():
    result = []

    for path in sorted(DOWNLOAD_DIR.glob("*.mp3")):
        match = re.match(
            r"^(\d{1,3})-(.+)-Quran\.mp3$",
            path.name,
            re.IGNORECASE
        )

        if match:
            result.append({
                "surahId": int(match.group(1)),
                "name": match.group(2).replace("-", " "),
                "filename": path.name
            })

    return result


# Home page
@app.route("/")
def home():
    return send_from_directory(BASE_DIR, HTML_FILE)


# Downloaded Surahs list
@app.route("/api/downloaded")
def api_downloaded():
    return jsonify({
        "ok": True,
        "files": downloaded_files()
    })


# Download a Surah
@app.route("/download-surah")
def download_surah():
    try:
        surah_id = int(request.args.get("id", ""))
    except ValueError:
        return jsonify({
            "ok": False,
            "error": "Invalid Surah number."
        }), 400

    name = request.args.get("name", f"Surah-{surah_id}")
    reciter = request.args.get("reciter", "ar.alafasy")

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", reciter):
        return jsonify({
            "ok": False,
            "error": "Invalid reciter."
        }), 400

    filename = f"{surah_id:03d}-{safe_name(name)}-Quran.mp3"
    destination = DOWNLOAD_DIR / filename

    try:
        request_obj = Request(
            audio_url(surah_id, reciter),
            headers={
                "User-Agent": "Easy-Quran-Hafiz/1.0"
            }
        )

        with urlopen(request_obj, timeout=60) as remote:
            with open(destination, "wb") as out:
                while True:
                    chunk = remote.read(1024 * 256)

                    if not chunk:
                        break

                    out.write(chunk)

        if destination.stat().st_size < 1024:
            destination.unlink(missing_ok=True)

            raise RuntimeError(
                "The downloaded audio file was unexpectedly small."
            )

        return jsonify({
            "ok": True,
            "filename": filename,
            "surahId": surah_id
        })

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        RuntimeError
    ) as exc:

        destination.unlink(missing_ok=True)

        return jsonify({
            "ok": False,
            "error": f"Server could not save the Surah audio: {exc}"
        }), 502


# Play a downloaded Surah
@app.route("/audio/<path:filename>")
def audio(filename):
    safe_filename = Path(filename).name

    if not safe_filename.lower().endswith(".mp3"):
        abort(404)

    target = DOWNLOAD_DIR / safe_filename

    if not target.exists():
        abort(404)

    return send_from_directory(
        DOWNLOAD_DIR,
        safe_filename,
        mimetype="audio/mpeg"
    )


# Optional favicon handling
@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9347))

    print(f"Easy Quran Hafiz running on port {port}")
    print(f"Downloads are saved in: {DOWNLOAD_DIR}")

    app.run(
        host="0.0.0.0",
        port=port,
        threaded=True
    )