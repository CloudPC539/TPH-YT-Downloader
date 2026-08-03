import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/fetch-info", methods=["POST"])
def fetch_info():
    data = request.json or {}
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
    data = request.json or {}
    url = data.get("url")
    quality = data.get("quality")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Create a temporary directory to store the file before sending
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
    }

    # Format mapping (selecting single-file streams when possible to avoid needing ffmpeg)
    if quality == "best":
        ydl_opts["format"] = "best[ext=mp4]/best"
    elif quality == "1080p":
        ydl_opts["format"] = "best[height<=1080][ext=mp4]/best[height<=1080]"
    elif quality == "720p":
        ydl_opts["format"] = "best[height<=720][ext=mp4]/best[height<=720]"
    elif quality == "480p":
        ydl_opts["format"] = "best[height<=480][ext=mp4]/best[height<=480]"
    elif quality in ["mp3", "m4a", "wav"]:
        ydl_opts["format"] = "bestaudio/best"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # Cleanup temporary file after sending
        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(filename):
                    os.remove(filename)
                os.rmdir(temp_dir)
            except Exception:
                pass
            return response

        return send_file(
            filename,
            as_attachment=True,
            download_name=os.path.basename(filename)
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
