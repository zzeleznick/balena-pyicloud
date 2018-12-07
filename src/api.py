import backoff
import logging
import os

from datetime import datetime
from pyicloud import PyiCloudService

from flask.logging import default_handler

from pyicloud.exceptions import (
    PyiCloudFailedLoginException,
    PyiCloudAPIResponseError,
    PyiCloud2SARequiredError,
    PyiCloudServiceNotActivatedErrror
)

backoff_logger = logging.getLogger('backoff')
backoff_logger.addHandler(default_handler)

logger = logging.getLogger()
logger.addHandler(default_handler)

EMAIL = os.environ["APP_EMAIL"]
PW = os.environ["APPLE_PW"]


def fatal_code(e):
    return (isinstance(e, PyiCloudFailedLoginException)
            or isinstance(e, PyiCloud2SARequiredError)
            or isinstance(e, PyiCloudServiceNotActivatedErrror)
            )


@backoff.on_exception(backoff.expo,
                      (PyiCloudFailedLoginException,
                       PyiCloudAPIResponseError,
                       PyiCloud2SARequiredError,
                       PyiCloudServiceNotActivatedErrror
                       ),
                      max_tries=5,
                      max_time=300,
                      jitter=backoff.full_jitter,
                      giveup=fatal_code)
def create_api():
    logger.info("create_api called")
    return PyiCloudService(EMAIL, PW)


@backoff.on_exception(backoff.expo,
                      (PyiCloudFailedLoginException,
                       PyiCloudAPIResponseError,
                       PyiCloud2SARequiredError,
                       PyiCloudServiceNotActivatedErrror
                       ),
                      max_tries=5,
                      max_time=300,
                      jitter=backoff.full_jitter,
                      giveup=fatal_code)
def reauth(api):
    return api.authenticate()


def fetch_device(api):
    def _fetch():
        try:
            return api.iphone
        except PyiCloudAPIResponseError as e:
            logger.error("Failed to fetch: {}".format(e), exc_info=True)
            reauth(api)
    device = None
    for i in range(3):
        logger.info("({}) Calling fetch_device".format(i))
        device = _fetch()
        if device:
            break
        logger.error("({}) Failed to fetch_device".format(i))
    else:
        logger.error("({}) No more retries".format(i))
    return device


def fetch_location(api):
    def _fetch():
        try:
            return api.friends.locations
        except PyiCloudAPIResponseError as e:
            logger.error("Failed to fetch: {}".format(e), exc_info=True)
            reauth(api)
    loc = None
    for i in range(3):
        logger.info("({}) Fetching location".format(i))
        loc = _fetch()
        if loc:
            break
        logger.error("({}) Failed to fetch location".format(i))
    else:
        logger.error("({}) No more retries".format(i))
    return loc


def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('year',        60*60*24*365),
        ('month',       60*60*24*30),
        ('day',         60*60*24),
        ('hour',        60*60),
        ('minute',      60),
        ('second',      1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings)


def fetch_address(api):
    res = {}
    loc = fetch_location(api)
    if not loc:
        res["error"] = "Failed: No location"
        return res
    # Just care about the first one
    loc = loc[0].get('location', {})
    lines = loc.get('address', {}).get('formattedAddressLines', [])
    if not lines:
        logger.info("Missing data in {}".format(loc))
        res["error"] = "Failed: Missing location data"
        return res

    res["address"] = " ".join(lines)
    ts = loc.get('timestamp')
    if ts:
        then = datetime.utcfromtimestamp(ts / 1000)
        timestamp = then.strftime('%Y-%m-%d %H:%M:%S')
        res["timestamp"] = timestamp
        now = datetime.utcnow()
        res["last_updated"] = td_format(now - then)

    return res

if __name__ == '__main__':
    api = create_api()
    print(fetch_address(api))
