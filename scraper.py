import os
import json
import base64
import requests
import feedparser
import smtplib
from email.mime.text import MIMEText
from time import mktime
from datetime import datetime

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

NITTER_INSTANCES = [
    "nitter.net",
    "nitter.snopyta.org",
    "nitter.42l.fr",
    "nitter.it",
]

def fetch_feed(account):
    for inst in NITTER_INSTANCES:
        url = f"https://{inst}/{account}/rss"
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "rss-fetcher/1.0"})
            if r.status_code == 200 and r.text.strip():
                return feedparser.parse(r.text)
        except Exception:
            continue
    return None

def entry_id(entry):
    if "id" in entry and entry.id:
        return entry.id
    if "guid" in entry and entry.guid:
        return entry.guid
    return entry.get("link", "")

def entry_published_ts(entry):
    if "published_parsed" in entry and entry.published_parsed:
        return int(mktime(entry.published_parsed))
    return 0

def main():
    state, sha = load_state_from_repo()
    seen_id = state.get("last_id", "")

    feed = fetch_feed(ACCOUNT)
    if not feed:
        print("ERROR: could not fetch any Nitter RSS instance.")
        raise SystemExit(1)

    items = feed.entries or []
    items.sort(key=entry_published_ts)

    new_last_id = seen_id
    matches = []

    for entry in items:
        eid = entry_id(entry)
        if not eid:
            continue
        if seen_id and eid <= seen_id:
            continue

        text_candidates = []
        if "title" in entry:
            text_candidates.append(entry.title)
        if "summary" in entry:
            text_candidates.append(entry.summary)
        content = " ".join(text_candidates).lower()

        if TEAM_KEYWORD in content:
            link = entry.get("link", "")
            pub = entry.get("published", "")
            matches.append({"title": entry.get("title",""), "link": link, "published": pub})

        new_last_id = eid

    if matches:
        body_lines = []
        for m in matches:
            body_lines.append(f"{m['title']}\n{m['link']}\nPublished: {m['published']}\n\n")
        body = "\n".join(body_lines)
        subject = f"[Football Alert] {ACCOUNT} - {len(matches)} new"
        send_email(subject, body)
        print(f"Sent email with {len(matches)} items.")

    if new_last_id and new_last_id != seen_id:
        state["last_id"] = new_last_id
        sha = save_state_to_repo(state, sha)
        print("State updated in repository.")

if __name__ == "__main__":
    main()