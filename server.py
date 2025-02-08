import subprocess
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    lang = request.args.get("lang", "en")

    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    subtitle_file = f"{video_id}.vtt"

    try:
        command = [
            "yt-dlp",
            "--extractor-args", "youtube:player-client=android",  # Використовуємо мобільний клієнт
            "--write-auto-sub",
            "--sub-lang", lang,
            "--skip-download",
            "--output", f"{video_id}.vtt",
            video_url
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

        if result.returncode != 0:
            return jsonify({"error": f"Не вдалося отримати субтитри. Код помилки: {result.returncode}, stderr: {result.stderr}"}), 500

        if not os.path.exists(subtitle_file):
            return jsonify({"error": f"Файл субтитрів {subtitle_file} не знайдено."}), 500

        with open(subtitle_file, "r", encoding="utf-8") as f:
            subtitles = f.readlines()

        transcript_text = "\n".join(line.strip() for line in subtitles if "-->" not in line and "WEBVTT" not in line)

        return jsonify({"video_id": video_id, "transcript": transcript_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
