import os
import re
import tempfile
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

# Convert YouTube Shorts URLs to standard Watch URLs
def clean_youtube_url(url):
    shorts_match = re.search(r"youtube\.com/shorts/([a-zA-Z0-9_-]+)", url)
    if shorts_match:
        video_id = shorts_match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

# Common options with a realistic User-Agent to bypass cloud blocks
BASE_YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    },
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/fetch-info", methods=["POST"])
def fetch_info():
    data = request.json or {}
    url = clean_youtube_url(data.get("url", ""))

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        ydl_opts = {**BASE_YDL_OPTS, "skip_download": True}
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
    url = clean_youtube_url(data.get("url", ""))
    quality = data.get("quality")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        **BASE_YDL_OPTS,
        "outtmpl": output_template,
    }

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
