from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable
import logging

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    lang = request.args.get("lang", "en")  # Мова за замовчуванням - англійська
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        logger.info(f"Fetching transcript for video: {video_id}, language: {lang}")
        
        # Отримати субтитри через YouTube API без авторизації
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
        subtitles = "\n".join([entry['text'] for entry in transcript])

        return jsonify({"video_id": video_id, "transcript": subtitles})

    except TranscriptsDisabled:
        logger.error(f"Subtitles are disabled for video: {video_id}")
        return jsonify({"error": "Subtitles are disabled for this video."}), 400
    except NoTranscriptAvailable:
        logger.error(f"No subtitles available for video: {video_id} in language: {lang}")
        return jsonify({"error": f"No subtitles available for this video in language: {lang}."}), 400
    except Exception as e:
        logger.error(f"Error fetching transcript for video: {video_id}. Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
