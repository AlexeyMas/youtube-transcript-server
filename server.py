from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptAvailable
import logging
import os

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Шлях до файлу cookies.txt
COOKIES_PATH = "cookies.txt"  # Замініть на актуальний шлях, якщо потрібно

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    lang = request.args.get("lang", "en")  # За замовчуванням - англійська

    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        logger.info(f"Fetching transcript for video: {video_id}, language: {lang}")

        # Перевіряємо, чи файл cookies.txt існує
        cookies = COOKIES_PATH if os.path.exists(COOKIES_PATH) else None
        if cookies:
            logger.info(f"Using cookies from {COOKIES_PATH}")
        
        # Отримуємо список доступних субтитрів
        available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies)

        # Якщо є субтитри на запитану мову
        if lang in [t.language_code for t in available_transcripts]:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang], cookies=cookies)

        else:
            # Якщо немає ручних субтитрів → використовуємо авто-субтитри
            auto_transcripts = [t.language_code for t in available_transcripts if t.is_generated]

            if auto_transcripts:
                logger.info(f"Using auto-generated subtitles in {auto_transcripts[0]}")
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[auto_transcripts[0]], cookies=cookies)

                # Якщо потрібно, додаємо можливість перекладу
                if lang != auto_transcripts[0]:
                    transcript = available_transcripts.find_generated_transcript([auto_transcripts[0]]).translate(lang).fetch()

            else:
                return jsonify({"error": "No available transcripts."}), 400

        subtitles = "\n".join([entry['text'] for entry in transcript])
        return jsonify({"video_id": video_id, "transcript": subtitles})

    except TranscriptsDisabled:
        return jsonify({"error": "Subtitles are disabled for this video."}), 400
    except NoTranscriptAvailable:
        return jsonify({"error": f"No subtitles available for {video_id} in {lang}."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
