from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable

app = Flask(__name__)

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        # Отримати субтитри англійською мовою
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        subtitles = "\n".join([entry['text'] for entry in transcript])

        return jsonify({"video_id": video_id, "transcript": subtitles})

    except TranscriptsDisabled:
        return jsonify({"error": "Subtitles are disabled for this video."}), 400
    except NoTranscriptAvailable:
        return jsonify({"error": "No subtitles available for this video."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
