import time
import os

from flask import (
    Flask,
    jsonify
)

from api import (
    create_api,
    fetch_address,
    fetch_device
)

version = os.environ.get("APP_VERSION", "v0")
app = Flask(__name__)
api = None


@app.route("/loc")
def locate():
    global api
    if not api:
        api = create_api()
    d = fetch_address(api)
    return jsonify(d)


@app.route("/device")
def device():
    global api
    if not api:
        api = create_api()
    return str(fetch_device(api))


@app.route("/now")
def now():
    d = {
        "now": time.time(),
        "version": version
    }
    return jsonify(d)


@app.route("/")
def hello():
    return "Hello World!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
