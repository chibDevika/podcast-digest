import feedparser
import requests
import anthropic
import smtplib
import os
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

FEED_URL = "https://api.substack.com/feed/podcast/10845/s/29339.rss"
LAST_SEEN_FILE = "last_seen.txt"

def get_latest_episode():
    feed = feedparser.parse(
        FEED_URL,
        agent="Mozilla/5.0 (compatible; LennyDigestBot/1.0)"
    )
    if not feed.entries:
        print(f"Feed returned 0 entries. Status: {feed.get('status', 'unknown')}")
        print(f"Feed bozo: {feed.get('bozo', False)}")
        raise SystemExit("Empty feed — check URL or add debug logging")
    return feed.entries[0]

def read_last_seen():
    with open(LAST_SEEN_FILE) as f:
        return f.read().strip()

def write_last_seen(guid):
    with open(LAST_SEEN_FILE, "w") as f:
        f.write(guid)

def fetch_transcript(url):
    res = requests.get(url, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")
    # Lenny's Substack puts transcript in the main article body
    body = soup.find("div", class_="body")
    if not body:
        body = soup.find("article")
    return body.get_text(separator="\n") if body else ""

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
    episode = get_latest_episode()
    guid = episode.get("id", episode.link)
    last_seen = read_last_seen()

    if guid == last_seen:
        print("No new episode.")
        return

    print(f"New episode: {episode.title}")
    transcript = fetch_transcript(episode.link)

    if not transcript:
        print("Could not fetch transcript.")
        return

    summary = summarize(transcript, episode.title)
    send_email(f"Lenny: {episode.title}", summary)
    write_last_seen(guid)
    print("Email sent.")

if __name__ == "__main__":
    main()