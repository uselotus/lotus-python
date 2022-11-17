import json
import logging
from datetime import date, datetime
from gzip import GzipFile
from io import BytesIO

from dateutil.tz import tzutc
from requests import sessions
from requests.auth import HTTPBasicAuth

from .utils import remove_trailing_slash
from .version import VERSION

_session = sessions.Session()


def post(host, api_key, gzip=False, timeout=15, body={}, method="GET"):
    """Post the `kwargs` to the API"""
    log = logging.getLogger("lotus")
    body = body
    body["sentAt"] = datetime.utcnow().replace(tzinfo=tzutc()).isoformat()
    url = host
    if not url.startswith("http"):
        url = "https://" + url
    data = json.dumps(body, cls=DatetimeSerializer)
    log.debug("making request: %s", data)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "lotus-python/" + VERSION,
        "X-API-KEY": api_key,
    }
    if gzip:
        headers["Content-Encoding"] = "gzip"
        buf = BytesIO()
        with GzipFile(fileobj=buf, mode="w") as gz:
            # 'data' was produced by json.dumps(),
            # whose default encoding is utf-8.
            gz.write(data.encode("utf-8"))
        data = buf.getvalue()

    if method == "GET":
        res = _session.get(url, headers=headers, params=body, timeout=timeout)
    elif method == "POST":
        res = _session.post(url, headers=headers, data=data, timeout=timeout)
    else:
        res = _session.patch(url, data=data, headers=headers, timeout=timeout)
    if res.status_code == 200 or res.status_code == 201:
        log.debug("data uploaded successfully")
        return res

    try:
        payload = res.json()
        log.debug("received response: %s", payload)
        raise APIError(res.status_code, payload)
    except ValueError:
        raise APIError(res.status_code, res.text)


class APIError(Exception):
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload

    def __str__(self):
        msg = "[Lotus] {0}: {1}"
        return msg.format(self.status, self.payload)


class DatetimeSerializer(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)
