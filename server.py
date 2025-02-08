import subprocess
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Перевіряємо, чи встановлено yt-dlp, і якщо ні — встановлюємо його
def install_yt_dlp():
    try:
        subprocess.run(["yt-dlp", "--version"], check=True)
    except FileNotFoundError:
        print("yt-dlp не знайдено, встановлюємо...")
        subprocess.run(["pip", "install", "yt-dlp"], check=True)

install_yt_dlp()  # Викликаємо функцію при запуску сервера

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # Використовуємо yt-dlp для отримання субтитрів
        command = ["yt-dlp", "--write-auto-sub", "--sub-lang", "en", "--skip-download", "-J", video_url]
        result = subprocess.run(command, capture_output=True, text=True)

        print(f"Команда виконана: {' '.join(command)}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        if result.returncode != 0:
            return jsonify({"error": f"Не вдалося отримати субтитри. Код помилки: {result.returncode}, stderr: {result.stderr}"}), 500

        return jsonify({"video_id": video_id, "transcript": result.stdout})

    except Exception as e:
        return jsonify({"error": f"Exception: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
