from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptAvailable
import logging
import os

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Файл з куками (якщо є)
COOKIES_PATH = "cookies.txt"

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    lang = request.args.get("lang")  # Мова (можна передавати будь-яку, якщо None – отримуємо всі доступні)

    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        logger.info(f"Fetching transcript for video: {video_id}, language: {lang}")

        # Перевіряємо, чи файл куків існує
        cookies = COOKIES_PATH if os.path.exists(COOKIES_PATH) else None
        if cookies:
            logger.info(f"Using cookies from {COOKIES_PATH}")

        # Отримуємо список доступних субтитрів
        available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

        # Якщо вказана конкретна мова – пробуємо отримати субтитри цією мовою
        if lang:
            transcript = available_transcripts.find_transcript([lang]).fetch()
        else:
            # Якщо мову не вказано – пробуємо отримати автоматичні або будь-які доступні
            try:
                transcript = available_transcripts.find_generated_transcript(["uk", "en"]).fetch()
            except:
                transcript = available_transcripts.find_manually_created_transcript(["uk", "en"]).fetch()

        subtitles = "\n".join([entry["text"] for entry in transcript])

        return jsonify({"video_id": video_id, "transcript": subtitles})

    except TranscriptsDisabled:
        return jsonify({"error": "Subtitles are disabled for this video."}), 400
    except NoTranscriptAvailable:
        return jsonify({"error": f"No subtitles available for video {video_id}."}), 400
    except Exception as e:
        logger.error(f"Error fetching transcript for video {video_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
