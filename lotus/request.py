import json
import logging
from datetime import date, datetime
from gzip import GzipFile
from io import BytesIO

from dateutil.tz import tzutc
from requests import sessions
from requests.auth import HTTPBasicAuth

from .utils import HTTPMethod, remove_trailing_slash
from .version import VERSION

_session = sessions.Session()


def send(
    host,
    api_key,
    method,
    gzip=False,
    timeout=15,
    body={},
    query={},
):
    """Post the `kwargs` to the API"""
    log = logging.getLogger("lotus")
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

    if method == HTTPMethod.GET:
        res = _session.get(url, headers=headers, params=query, timeout=timeout)
    elif method == HTTPMethod.POST:
        res = _session.post(
            url, headers=headers, data=data, params=query, timeout=timeout
        )
    elif method == HTTPMethod.PATCH:
        res = _session.patch(
            url, data=data, headers=headers, params=query, timeout=timeout
        )
    elif method == HTTPMethod.DELETE:
        res = _session.delete(url, headers=headers, params=query, timeout=timeout)
    else:
        raise ValueError("Unsupported HTTP method: " + method)

    if res.status_code == 200 or res.status_code == 201 or res.status_code == 204:
        log.debug("data uploaded successfully")
        return res

    try:
        if res.status_code != 204:
            payload = res.json()
        else:
            payload = "Success"
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
