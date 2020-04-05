import backoff
import logging
import logging.handlers

# import sys
import os

from datetime import datetime
from pyicloud import PyiCloudService

from flask.logging import default_handler

from pyicloud.exceptions import (
    PyiCloudFailedLoginException,
    PyiCloudAPIResponseException,
    PyiCloud2SARequiredException,
    PyiCloudServiceNotActivatedException,
)

formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
rot_handler = logging.handlers.RotatingFileHandler("app.log", maxBytes=1024 * 1024)
rot_handler.setLevel(logging.INFO)
rot_handler.setFormatter(formatter)

backoff_logger = logging.getLogger("backoff")
backoff_logger.addHandler(default_handler)
backoff_logger.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(default_handler)
logger.addHandler(rot_handler)

EMAIL = os.environ["APP_EMAIL"]
PW = os.environ["APPLE_PW"]


def fatal_code(e):
    return (
        isinstance(e, PyiCloudFailedLoginException)
        or isinstance(e, PyiCloud2SARequiredException)
        or isinstance(e, PyiCloudServiceNotActivatedException)
    )


@backoff.on_exception(
    backoff.expo,
    (
        PyiCloudFailedLoginException,
        PyiCloudAPIResponseException,
        PyiCloud2SARequiredException,
        PyiCloudServiceNotActivatedException,
    ),
    max_tries=5,
    max_time=300,
    jitter=backoff.full_jitter,
    giveup=fatal_code,
)
def create_api():
    logger.info("create_api called")
    return PyiCloudService(EMAIL, PW)


@backoff.on_exception(
    backoff.expo,
    (
        PyiCloudFailedLoginException,
        PyiCloudAPIResponseException,
        PyiCloud2SARequiredException,
        PyiCloudServiceNotActivatedException,
    ),
    max_tries=5,
    max_time=300,
    jitter=backoff.full_jitter,
    giveup=fatal_code,
)
def reauth(api):
    return api.authenticate()


class ICloudAPI(object):
    api = None

    @classmethod
    def init(cls):
        logger.info("init called for ICloudAPI: {}".format(cls.api))
        if cls.api:
            return
        cls.api = create_api()

    @classmethod
    def reauth(cls):
        logger.info("reauth called for ICloudAPI")
        reauth(cls.api)

    @classmethod
    def fetch_device(cls, retries=3):
        cls.init()

        def _fetch():
            try:
                return cls.api.iphone
            except PyiCloudAPIResponseException as e:
                logger.error("Failed to fetch: {}".format(e), exc_info=True)
            try:
                cls.reauth()
            except PyiCloudAPIResponseException as e:
                logger.error("Failed to reauth: {}".format(e), exc_info=True)

        device = None
        for i in range(retries):
            logger.info("({}) Calling fetch_device".format(i))
            device = _fetch()
            if device:
                break
            logger.error("({}) Failed to fetch_device".format(i))
        else:
            logger.error("({}) No more retries".format(i))
        return device

    @classmethod
    def fetch_locations(cls, retries=3):
        cls.init()

        def _fetch():
            try:
                return cls.api.friends.locations
            except PyiCloudAPIResponseException as e:
                logger.error("Failed to fetch: {}".format(e), exc_info=True)
            try:
                cls.reauth()
            except PyiCloudAPIResponseException as e:
                logger.error("Failed to reauth: {}".format(e), exc_info=True)

        locations = None
        for i in range(retries):
            logger.info("({}) Calling fetch_locations".format(i))
            locations = _fetch()
            if locations:
                break
            logger.error("({}) Failed to fetch_locations".format(i))
        else:
            logger.error("({}) No more retries".format(i))
        return locations


def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ("year", 60 * 60 * 24 * 365),
        ("month", 60 * 60 * 24 * 30),
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("minute", 60),
        ("second", 1),
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = "s" if period_value > 1 else ""
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings)


def extact_address(payload={}):
    res = {}
    loc = payload.get("location", {})
    lines = loc.get("address", {}).get("formattedAddressLines", [])
    if not lines:
        logger.info("Missing data in {}".format(loc))
        res["error"] = "Failed: Missing location data"
        return res
    res["address"] = " ".join(lines)
    ts = loc.get("timestamp")
    if not ts:
        return res
    then = datetime.utcfromtimestamp(ts / 1000)
    timestamp = then.strftime("%Y-%m-%d %H:%M:%S")
    res["timestamp"] = timestamp
    now = datetime.utcnow()
    res["last_updated"] = td_format(now - then)
    return res


def fetch_address(idx=1):
    res = {}
    locations = ICloudAPI.fetch_locations()
    mapped_index = idx - 1  # 0
    if not locations:
        res["error"] = "Failed: No location"
        return res
    if mapped_index >= len(locations):
        res["error"] = "Failed: Index ({}) out of range ({})".format(
            idx, len(locations)
        )
        return res
    if mapped_index < 0:
        # get all
        return {i: extact_address(loc) for i, loc in enumerate(locations)}
    return extact_address(locations[mapped_index])


def test_logger():
    logger.debug("Hello debug")
    logger.info("Hello info")
    logger.warning("Hello warning")


if __name__ == "__main__":
    api = create_api()
    print(fetch_address(api))
