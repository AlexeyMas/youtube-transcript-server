import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # Використання yt-dlp для отримання субтитрів
        command = ["/usr/local/bin/yt-dlp", "--write-auto-sub", "--sub-lang", "en", "--skip-download", "-J", video_url]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({"error": "Не вдалося отримати субтитри"}), 500

        output = result.stdout
        return jsonify({"video_id": video_id, "transcript": output})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
