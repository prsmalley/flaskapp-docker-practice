from flask import Flask
from flask import request

app = Flask(__name__)

@app.route("/health")
def health ():
    return {"status": "ok"}

@app.route("/greet")
def greet():
    name = request.args.get("name", "world")
    return {"greeting": "Hi, " + name}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

