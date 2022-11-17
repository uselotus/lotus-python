import unittest

import mock
import pytest

import lotus


class TestModule:
    def failed(self):
        self.failed = True

    def setup_method(self):
        self.failed = False
        lotus.api_key = "testsecret"
        lotus.on_error = self.failed

    def test_no_api_key(self):
        lotus.api_key = None
        with pytest.raises(Exception):
            lotus.track_event()

    def test_no_host(self):
        lotus.host = None
        with pytest.raises(Exception):
            lotus.track_event()

    def test_track(self, track_event_example):
        lotus.track_event(**track_event_example)
        with mock.patch("lotus.consumer.post") as mock_post:
            lotus.flush()

    def test_create_customer(self, create_customer_example):
        lotus.create_customer(**create_customer_example)
        with mock.patch("lotus.consumer.post") as mock_post:
            lotus.flush()

    def test_create_subscription(self, create_subscription_example):
        lotus.create_subscription(**create_subscription_example)
        with mock.patch("lotus.consumer.post") as mock_post:
            lotus.flush()

    def test_cancel_subscription(self, cancel_subscription_example):
        lotus.cancel_subscription(**cancel_subscription_example)
        with mock.patch("lotus.consumer.post") as mock_post:
            lotus.flush()

    def test_flush(self):
        with mock.patch("lotus.consumer.post") as mock_post:
            lotus.flush()
