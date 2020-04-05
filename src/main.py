import time
import os
import logging

from flask import Flask, jsonify

from api import (
    logger,
    rot_handler,
    test_logger,
    create_api,
    fetch_address,
    fetch_device,
    ICloudAPI,
)

_version = os.environ.get("APP_VERSION", "v0")
port = os.environ.get("PORT", 80)
debug = os.environ.get("DEBUG", False)

app = Flask(__name__)


@app.route("/loc", defaults={"idx": 1})
@app.route("/loc/<idx>")
def locate(idx):
    app.logger.info("locate called for idx %s", idx)
    try:
        idx = int(idx)
    except ValueError:
        return "Bad Request", 400
    d = fetch_address(idx)
    return jsonify(d)


@app.route("/locations")
def locations():
    d = fetch_address(0)
    return jsonify(d)


@app.route("/device")
def device():
    global api
    if not api:
        api = create_api()
    return str(fetch_device(api))


@app.route("/now")
def now():
    logger.info("now called")
    app.logger.warning("now called")
    d = {"now": time.time(), "version": _version}
    return jsonify(d)


@app.route("/version")
def version():
    return _version


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/test")
def test():
    logger.info("test called")
    app.logger.warning("test called")
    test_logger()
    return "Success"


if __name__ == "__main__":
    app.logger.addHandler(rot_handler)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("App launching on port %s", port)
    app.run(host="0.0.0.0", debug=debug, port=port)
