import sqlite3
import smtplib
from email.mime.text import MIMEText
import snscrape.modules.twitter as sntwitter

# CONFIG
ACCOUNT = "ACCOUNT_NAME"     # account to monitor
TEAM_KEYWORD = "palmeiras"   # your team keyword

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "YOUR_EMAIL@gmail.com"
EMAIL_PASS = "YOUR_APP_PASSWORD"
EMAIL_TO = "YOUR_EMAIL@gmail.com"

DB_FILE = "database.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY,
            last_tweet_id TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_last_tweet():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT last_tweet_id FROM state WHERE id=1")
    row = c.fetchone()

    conn.close()

    return row[0] if row else None


def save_last_tweet(tweet_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO state (id, last_tweet_id)
        VALUES (1, ?)
    """, (tweet_id,))

    conn.commit()
    conn.close()


def send_email(text, url):

    body = f"""
New tweet mentioning your team

{text}

{url}
"""

    msg = MIMEText(body)
    msg["Subject"] = "Football Alert"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)


def check_tweets():

    last_id = get_last_tweet()

    query = f"from:{ACCOUNT}"

    tweets = []

    for tweet in sntwitter.TwitterSearchScraper(query).get_items():
        tweets.append(tweet)
        if len(tweets) >= 5:
            break

    tweets.reverse()

    for tweet in tweets:

        if last_id and str(tweet.id) <= last_id:
            continue

        text = tweet.content.lower()

        if TEAM_KEYWORD in text:
            send_email(tweet.content, tweet.url)

        save_last_tweet(str(tweet.id))


if __name__ == "__main__":
    init_db()
    check_tweets()