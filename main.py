import requests
import anthropic
import smtplib
import os
from email.mime.text import MIMEText
from youtube_transcript_api import YouTubeTranscriptApi

CHANNEL_ID = "UC6t1O76G0jYXOAoYCm153dA"
LAST_SEEN_FILE = "last_seen.txt"
YT_API_KEY = os.environ["YOUTUBE_API_KEY"]

def get_latest_video():
    res = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "key": YT_API_KEY,
            "channelId": CHANNEL_ID,
            "part": "snippet",
            "order": "date",
            "maxResults": 1,
            "type": "video",
        },
        timeout=10
    )
    items = res.json().get("items", [])
    if not items:
        raise SystemExit("No videos found")
    item = items[0]
    return {
        "id": item["id"]["videoId"],
        "title": item["snippet"]["title"],
        "url": f"https://youtube.com/watch?v={item['id']['videoId']}"
    }

def fetch_transcript(video_id):
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join([t["text"] for t in transcript])

def read_last_seen():
    with open(LAST_SEEN_FILE) as f:
        return f.read().strip()

def write_last_seen(video_id):
    with open(LAST_SEEN_FILE, "w") as f:
        f.write(video_id)

def summarize(transcript, title):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""You are summarizing a podcast episode for a busy product manager.

Episode: {title}

Transcript:
{transcript[:12000]}

Give me:
1. The guest and their background in 2 sentences
2. The 5 most useful ideas from this episode, each in 2-3 sentences
3. One quote worth saving

Be direct. No filler."""
        }]
    )
    return response.content[0].text

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["GMAIL_ADDRESS"]
    msg["To"] = os.environ["GMAIL_ADDRESS"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["GMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)

def main():
    video = get_latest_video()
    last_seen = read_last_seen()

    if video["id"] == last_seen:
        print("No new episode.")
        return

    print(f"New episode: {video['title']}")
    transcript = fetch_transcript(video["id"])
    summary = summarize(transcript, video["title"])
    send_email(f"Lenny: {video['title']}", summary)
    write_last_seen(video["id"])
    print("Email sent.")

if __name__ == "__main__":
    main()