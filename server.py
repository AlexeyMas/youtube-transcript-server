from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import logging
import os

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COOKIES_PATH = "cookies.txt"

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    lang = request.args.get("lang", "en")

    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        logger.info(f"Fetching transcript for video: {video_id}, language: {lang}")
        cookies = COOKIES_PATH if os.path.exists(COOKIES_PATH) else None

        available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies)
        logger.info(f"Available transcripts: {[str(t) for t in available_transcripts]}")

        transcript = None
        try:
            transcript = available_transcripts.find_manually_created_transcript([lang])
        except Exception as e:
            logger.warning(f"Manual transcript not found: {e}")
            try:
                transcript = available_transcripts.find_generated_transcript([lang])
            except Exception as e2:
                logger.warning(f"Generated transcript not found: {e2}")
                transcript = None

        if transcript is None:
            all_langs = [t.language_code for t in available_transcripts]
            try:
                transcript = available_transcripts.find_generated_transcript(all_langs)
            except Exception as e3:
                logger.warning(f"No transcript in any language: {e3}")
                return jsonify({"error": "No available transcripts."}), 400

        # Якщо потрібен переклад
        if transcript.language_code != lang:
            if transcript.is_translatable:
                transcript = transcript.translate(lang)
            else:
                logger.warning("Transcript is not translatable!")
                return jsonify({"error": "Transcript not translatable to requested language."}), 400

        # Перевіряємо, що fetch() не впаде
        try:
            subtitles = "\n".join([entry['text'] for entry in transcript.fetch()])
        except Exception as e:
            logger.error(f"Error in transcript.fetch(): {e}")
            return jsonify({"error": f"Failed to fetch transcript: {e}"}), 500

        return jsonify({"video_id": video_id, "transcript": subtitles})

    except TranscriptsDisabled:
        return jsonify({"error": "Subtitles are disabled for this video."}), 400
    except Exception as e:
        logger.error(f"General server error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
