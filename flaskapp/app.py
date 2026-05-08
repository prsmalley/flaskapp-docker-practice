from flask import Flask
from flask import request
import os

app = Flask(__name__)

@app.route("/health")
def health ():
    return {"status": "ok"}

@app.route("/greet")
def greet():
    name = request.args.get("name", "world")
    return {"greeting": "Hi, " + name}

@app.route("/version")
def version():
    return {"version": "1.0.0"}

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    app.run(host=host, port=5000)

