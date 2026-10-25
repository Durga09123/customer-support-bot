# Fresh Fruit Shop – Customer Support Bot

A rule-based NLP chatbot (Flask) that answers fruit availability and price questions and prepares a bill from typed orders such as `apple 1kg mango 2kg`.

**NLP techniques used:** text normalisation, regex tokenisation, plural/stem handling, fuzzy matching for typos (`difflib`), quantity–item pairing, intent detection.

## Run locally (VS Code)
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Deploy on Vercel
1. Push this folder to a GitHub repository.
2. On vercel.com choose **Add New → Project**, import the repository.
3. Leave the defaults and click **Deploy**.

## Structure
```
app.py            Flask routes
bot.py            NLP engine and fruit catalogue
templates/        index.html
static/           style.css, script.js
vercel.json       Vercel configuration
requirements.txt  Python dependencies
```
Edit prices in the `CATALOG` dictionary at the top of `bot.py`.

https://customer-support-bot-six-dun.vercel.app/
