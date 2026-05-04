from flask import Flask, jsonify
from flask import request
import redis

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
    app.run(host="0.0.0.0", port=5000)

