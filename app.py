import os
from flask import Flask, render_template, request, jsonify
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/fetch-info", methods=["POST"])
def fetch_info():
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "Unknown Title")
            duration = info.get("duration", 0)

            minutes, seconds = divmod(duration, 60)
            time_str = f"{minutes}m {seconds}s" if duration else "Live/N/A"

            return jsonify({
                "title": title,
                "duration": time_str
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download", methods=["POST"])
def download_media():
    data = request.json
    url = data.get("url")
    quality = data.get("quality")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    ydl_opts = {"outtmpl": output_template}

    if quality == "best":
        ydl_opts["format"] = "bestvideo+bestaudio/best"
    elif quality == "1080p":
        ydl_opts["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    elif quality == "720p":
        ydl_opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]"
    elif quality == "480p":
        ydl_opts["format"] = "bestvideo[height<=480]+bestaudio/best[height<=480]"
    elif quality == "mp3":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }]
    elif quality == "m4a":
        ydl_opts["format"] = "bestaudio[ext=m4a]/best"
    elif quality == "wav":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return jsonify({"message": f"Successfully downloaded to {DOWNLOAD_DIR}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting server... Open http://127.0.0.1:5000 in your browser.")
    app.run(debug=True, port=5000)
