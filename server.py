from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptAvailable
import logging
import os
import random
import time
import re
import glob
import tempfile
from yt_dlp import YoutubeDL

app = Flask(__name__)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Шлях до файлу cookies.txt
COOKIES_PATH = os.getenv("COOKIES_PATH", "cookies.txt")
CACHE_TTL_SECONDS = int(os.getenv("TRANSCRIPT_CACHE_TTL_SECONDS", "3600"))
MAX_RETRIES = int(os.getenv("YOUTUBE_RETRY_ATTEMPTS", "3"))
BASE_RETRY_DELAY = float(os.getenv("YOUTUBE_RETRY_BASE_DELAY", "1.0"))

# Простий in-memory кеш, щоб зменшити кількість повторних запитів до YouTube.
transcript_cache = {}


def is_rate_limited(message: str) -> bool:
    lowered = message.lower()
    return "429" in lowered or "too many requests" in lowered


def is_bot_challenge(message: str) -> bool:
    lowered = message.lower()
    return (
        "sign in to confirm you're not a bot" in lowered
        or "confirm you’re not a bot" in lowered
        or "not a bot" in lowered
        or "--cookies-from-browser" in lowered
        or "use --cookies for the authentication" in lowered
    )


def should_retry(exception: Exception) -> bool:
    return is_rate_limited(str(exception))


def clean_error_message(message: str) -> str:
    compact = " ".join(message.split())
    if len(compact) > 220:
        return compact[:220] + "..."
    return compact


def get_cached_transcript(cache_key: str):
    cached = transcript_cache.get(cache_key)
    if not cached:
        return None
    if time.time() - cached["ts"] > CACHE_TTL_SECONDS:
        transcript_cache.pop(cache_key, None)
        return None
    return cached["value"]


def set_cached_transcript(cache_key: str, value: str):
    transcript_cache[cache_key] = {"value": value, "ts": time.time()}


def fetch_transcript_with_retries(video_id: str, lang: str, cookies):
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies)
            language_codes = [t.language_code for t in available_transcripts]

            if lang in language_codes:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang], cookies=cookies)
            else:
                auto_transcripts = [t.language_code for t in available_transcripts if t.is_generated]
                if not auto_transcripts:
                    raise NoTranscriptAvailable(f"No available transcripts for {video_id}.")

                source_lang = auto_transcripts[0]
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[source_lang], cookies=cookies)

                if lang != source_lang:
                    transcript = available_transcripts.find_generated_transcript([source_lang]).translate(lang).fetch()

            subtitles = "\n".join(entry["text"] for entry in transcript)
            return subtitles
        except Exception as exc:
            last_error = exc
            if not should_retry(exc) or attempt == MAX_RETRIES:
                break
            delay = (BASE_RETRY_DELAY * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
            logger.warning(
                "YouTube rate limit detected for %s (attempt %s/%s). Retrying in %.2fs",
                video_id, attempt, MAX_RETRIES, delay
            )
            time.sleep(delay)

    raise last_error


def parse_vtt_to_text(vtt_text: str) -> str:
    lines = []
    for raw_line in vtt_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper().startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        if "-->" in line:
            continue
        if line.isdigit():
            continue

        # Видаляємо базові VTT/HTML-теги.
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        lines.append(line)

    # Прибираємо повтори сусідніх рядків.
    deduplicated = []
    for line in lines:
        if not deduplicated or deduplicated[-1] != line:
            deduplicated.append(line)
    return "\n".join(deduplicated)


def fetch_transcript_with_ytdlp(video_id: str, lang: str, cookies):
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    language_candidates = [lang, "en", "en-US"]

    with tempfile.TemporaryDirectory() as temp_dir:
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": language_candidates,
            "subtitlesformat": "vtt",
            "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }
        if cookies:
            ydl_opts["cookiefile"] = cookies

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        vtt_files = sorted(glob.glob(os.path.join(temp_dir, f"{video_id}*.vtt")))
        if not vtt_files:
            raise NoTranscriptAvailable(f"No subtitles available for {video_id}.")

        with open(vtt_files[0], "r", encoding="utf-8", errors="ignore") as file:
            vtt_text = file.read()
        parsed_text = parse_vtt_to_text(vtt_text)
        if not parsed_text:
            raise NoTranscriptAvailable(f"Subtitle file exists but transcript is empty for {video_id}.")
        return parsed_text

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    lang = request.args.get("lang", "en")  # За замовчуванням - англійська

    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    cache_key = f"{video_id}:{lang}"
    cached_transcript = get_cached_transcript(cache_key)
    if cached_transcript:
        logger.info("Transcript cache hit for %s", cache_key)
        return jsonify({"video_id": video_id, "transcript": cached_transcript, "cached": True})

    try:
        logger.info(f"Fetching transcript for video: {video_id}, language: {lang}")

        # Перевіряємо, чи файл cookies.txt існує
        cookies = COOKIES_PATH if os.path.exists(COOKIES_PATH) else None
        if cookies:
            logger.info(f"Using cookies from {COOKIES_PATH}")

        source = "youtube_transcript_api"
        try:
            subtitles = fetch_transcript_with_retries(video_id=video_id, lang=lang, cookies=cookies)
        except Exception as primary_error:
            logger.warning("Primary transcript fetch failed for %s: %s", video_id, clean_error_message(str(primary_error)))
            source = "yt_dlp_fallback"
            subtitles = fetch_transcript_with_ytdlp(video_id=video_id, lang=lang, cookies=cookies)

        set_cached_transcript(cache_key, subtitles)
        return jsonify({"video_id": video_id, "transcript": subtitles, "cached": False, "source": source})

    except TranscriptsDisabled:
        return jsonify({"error": "Subtitles are disabled for this video."}), 400
    except NoTranscriptAvailable:
        return jsonify({"error": f"No subtitles available for {video_id} in {lang}."}), 400
    except Exception as e:
        message = clean_error_message(str(e))
        if is_bot_challenge(message):
            logger.warning("YouTube bot challenge for %s: %s", video_id, message)
            return jsonify({
                "error": "YouTube blocked automated subtitle access for now. Try again later or refresh server cookies.",
                "code": "youtube_bot_challenge"
            }), 503
        if is_rate_limited(message):
            logger.warning("Rate limited by YouTube for %s: %s", video_id, message)
            return jsonify({
                "error": "YouTube rate limit reached. Please retry later.",
                "code": "rate_limited"
            }), 429
        logger.exception("Unexpected transcript fetch error for %s", video_id)
        return jsonify({"error": message}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
