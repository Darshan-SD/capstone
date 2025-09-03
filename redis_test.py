from flask import Flask, session, request
from flask_session import Session
import redis

app = Flask(__name__)

# Configure Flask-Session to use Redis
app.config["SECRET_KEY"] = "test_secret"
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.Redis(host="localhost", port=6379)
app.config["SESSION_KEY_PREFIX"] = "session:"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = False

Session(app)

@app.route("/set")
def set_session():
    session["test_key"] = "Hello Redis!"
    return "✅ Session set!"

@app.route("/get")
def get_session():
    return dict(session)

@app.route("/session-id")
def session_id():
    return {"session_id": request.cookies.get("session")}


if __name__ == "__main__":
    app.run(debug=True)