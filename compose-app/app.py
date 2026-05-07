from flask import Flask, jsonify
from flask import request
import redis
import os

app = Flask(__name__)
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)


@app.route("/health")
def health ():
    return {"status": "ok"}

@app.route("/greet")
def greet():
    name = request.args.get("name", "world")
    return {"greeting": "Hi, " + name}

@app.route('/counter')
def counter():
    count = redis_client.incr('hits')
    return jsonify(count=count)


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    app.run(host=host, port=5000)

