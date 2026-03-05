import os
import json
import base64
import requests
import smtplib
from email.mime.text import MIMEText
import snscrape.modules.twitter as sntwitter

ACCOUNT = os.getenv("ACCOUNT")               
TEAM_KEYWORD = os.getenv("TEAM_KEYWORD", "").lower() 
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")
STATE_PATH = os.getenv("STATE_PATH", "state.json")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")  

if not (ACCOUNT and TEAM_KEYWORD and EMAIL_USER and EMAIL_PASS and EMAIL_TO and GITHUB_TOKEN and GITHUB_REPO):
    raise SystemExit("Missing required environment variables.")

GH_API_FILE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{STATE_PATH}"

def load_state_from_repo():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(GH_API_FILE_URL, headers=headers)
    if r.status_code == 200:
        payload = r.json()
        content = base64.b64decode(payload["content"]).decode()
        return json.loads(content), payload["sha"]
    elif r.status_code == 404:
        return {}, None
    else:
        r.raise_for_status()

def save_state_to_repo(state, sha=None):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content_b64 = base64.b64encode(json.dumps(state).encode()).decode()
    data = {
        "message": "Update scraper state",
        "content": content_b64,
    }
    if sha:
        data["sha"] = sha
    r = requests.put(GH_API_FILE_URL, headers=headers, json=data)
    r.raise_for_status()
    return r.json()["content"]["sha"]

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(EMAIL_USER, EMAIL_PASS)
        s.send_message(msg)

def main():
    state, sha = load_state_from_repo()
    last_id = int(state.get("last_tweet_id", 0))

    query = f"from:{ACCOUNT}"
    items = []
    for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
        items.append(tweet)
        if i >= 29:  
            break

    items.reverse()
    new_last_id = last_id
    sent_any = False

    for tweet in items:
        tid = int(tweet.id)
        if tid <= last_id:
            continue

        text = tweet.content.lower()
        if TEAM_KEYWORD in text:
            subject = f"[Football Alert] {ACCOUNT} mentioned {TEAM_KEYWORD}"
            body = f"{tweet.content}\n\nLink: {tweet.url}"
            send_email(subject, body)
            sent_any = True

        if tid > new_last_id:
            new_last_id = tid

    if new_last_id != last_id:
        state["last_tweet_id"] = str(new_last_id)
        sha = save_state_to_repo(state, sha)

if __name__ == "__main__":
    main()