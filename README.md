# Twitter / X Football Alert

Simple GitHub Actions project that checks a public X account (via Nitter RSS) every 5 minutes and sends an email when a team keyword appears.

## How to use

1. Create a repository and copy the files:
   - `scraper.py`
   - `requirements.txt`
   - `.github/workflows/scrape.yml`

2. Add repository **Variables**:
   - `ACCOUNT` = the X account username (example: `futebol_info`)
   - `TEAM_KEYWORD` = keyword to match (example: `flamengo`)

3. Add **Secrets**:
   - `EMAIL_USER` = SMTP username (example Gmail)
   - `EMAIL_PASS` = SMTP app password
   - `EMAIL_TO` = recipient email

4. Trigger the workflow manually once (Actions → select workflow → Run workflow).  
   Scheduled runs will then run automatically (cron every 5 minutes).

## Notes
- The workflow runs on the repository's default branch.
- GitHub cron uses **UTC** and can be delayed by a few seconds/minutes.
- If you need faster than 5-minute polling use a different platform (Lambda, VPS).

That's it.
