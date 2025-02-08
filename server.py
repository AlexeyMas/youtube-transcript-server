import subprocess
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/debug_cookies", methods=["GET"])
def debug_cookies():
    try:
        with open("cookies.txt", "r", encoding="utf-8") as f:
            cookies_content = f.read()
        return jsonify({"cookies": cookies_content[:500]})  # Выводим первые 500 символов
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
