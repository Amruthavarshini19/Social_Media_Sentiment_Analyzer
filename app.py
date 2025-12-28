from flask import Flask, request, jsonify
from flask_cors import CORS
from googleapiclient.discovery import build
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os
import re

app = Flask(__name__)
CORS(app)

# Sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY not set")

@app.route("/", methods=["GET"])
def home():
    return "Backend is running!", 200



def extract_video_id(url):
    """
    Supports:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    """
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


@app.route("/analyze-youtube", methods=["POST"])
def analyze_youtube():
    data = request.get_json()
    video_url = data.get("url")

    if not video_url:
        return jsonify({"error": "YouTube URL missing"}), 400

    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=50,
            textFormat="plainText"
        ).execute()
    except Exception as e:
        return jsonify({
            "error": "Comments unavailable or API error",
            "details": str(e)
        }), 500

    results = []

    for item in response.get("items", []):
        comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]

        score = analyzer.polarity_scores(comment)

        sentiment = "neutral"
        if score["compound"] > 0.05:
            sentiment = "positive"
        elif score["compound"] < -0.05:
            sentiment = "negative"

        results.append({
            "comment": comment,
            "sentiment": sentiment,
            "confidence": score["compound"]
        })

    return jsonify(results)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
