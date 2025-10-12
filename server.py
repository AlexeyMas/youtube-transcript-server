from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import logging
import os
import time

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COOKIES_PATH = "cookies.txt"

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    start = time.time()
    video_id = request.args.get("video_id")
    lang = request.args.get("lang", "en")

    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        logger.info(f"Fetching transcript for video: {video_id}, language: {lang}")
        cookies = COOKIES_PATH if os.path.exists(COOKIES_PATH) else None

        # ОТРИМАННЯ ТРАНСКРИПТУ (без list_transcripts)
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang], cookies=cookies)
        except TranscriptsDisabled:
            return jsonify({"error": "Subtitles are disabled for this video."}), 400
        except Exception as e:
            logger.error(f"Error getting transcript: {e}")
            return jsonify({"error": str(e)}), 400

        subtitles = "\n".join([entry['text'] for entry in transcript])
        logger.info(f"Elapsed time: {time.time()-start} сек")
        return jsonify({"video_id": video_id, "transcript": subtitles})
    
    except Exception as e:
        logger.info(f"Elapsed time: {time.time()-start} сек")
        logger.error(f"General server error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
