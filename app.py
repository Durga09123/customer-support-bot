from flask import Flask, jsonify, render_template, request

from bot import get_reply

app = Flask(__name__)


@app.get("/")
@app.get("/bot")
def index():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:300]
    return jsonify(get_reply(message))


@app.get("/api/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(debug=True)
