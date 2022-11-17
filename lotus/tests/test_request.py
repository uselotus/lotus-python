import json
import unittest
from datetime import date, datetime

import mock
import pytest
import requests

from lotus.request import DatetimeSerializer, post


class TestRequests:
    # def test_valid_request(self):
    #     with mock.patch("lotus.request.post") as mock_post:
    #         res = post(
    #             batch=[
    #                 {"distinct_id": "distinct_id", "event": "python event", "type": "track"}
    #             ]
    #         )
    #     assert res.status_code == 200

    def test_invalid_host(self):
        with pytest.raises(Exception):
            post("testsecret", "bogus.lotus.app/", batch=[])

    def test_datetime_serialization(self):
        data = {"created": datetime(2012, 3, 4, 5, 6, 7, 891011)}
        result = json.dumps(data, cls=DatetimeSerializer)
        assert result == '{"created": "2012-03-04T05:06:07.891011"}'

    def test_date_serialization(self):
        today = date.today()
        data = {"created": today}
        result = json.dumps(data, cls=DatetimeSerializer)
        expected = '{"created": "%s"}' % today.isoformat()
        assert result == expected

    # def test_should_not_timeout(self):
    #     with mock.patch("lotus.request.post") as mock_post:
    #         res = post(
    #             batch=[
    #                 {"distinct_id": "distinct_id", "event": "python event", "type": "track"}
    #             ],
    #             timeout=15,
    #         )
    #     assert res.status_code == 200

    # def test_should_timeout(self):
    #     with pytest.raises(requests.ReadTimeout):
    #         post(
    #             batch=[
    #                 {
    #                     "distinct_id": "distinct_id",
    #                     "event": "python event",
    #                     "type": "track",
    #                 }
    #             ],
    #             timeout=0.0001,
    #         )
