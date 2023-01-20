import time
import unittest
from datetime import date, datetime

import mock
import pytest
import six

from lotus import Client

API_KEY = "ptZNACr2.nxc84U9orJ2rJpB6Qjl8wvJkvZdvn9Gi"


class TestClient:
    def fail(self, e, batch):
        """Mark the failure handler"""
        self.failed = True

    def setup_method(self):
        self.failed = False
        self.client = Client(
            API_KEY,
            host="http://localhost:8000",
            on_error=self.fail,
        )

    def test_requires_api_key(self):
        with pytest.raises(AssertionError):
            Client(None)

    def test_empty_flush(self):
        self.client.flush()

    def test_basic_track_event(self, track_event_example):
        client = self.client
        success, msg = client.track_event(**track_event_example())
        client.flush()
        assert success == True
        assert self.failed == False

        assert msg["event_name"] == "python test event"
        assert msg["idempotency_id"]
        assert msg["properties"] == {"property": "value"}

    def test_stringifies_distinct_id(self, track_event_example):
        # A large number that loses precision in node:
        # node -e "console.log(157963456373623802 + 1)" > 157963456373623800
        client = self.client
        success, msg = client.track_event(**track_event_example())
        client.flush()
        assert success == True
        assert self.failed == False

    def test_basic_create_customer(self, create_customer_example):
        client = self.client
        success, msg = client.create_customer(**create_customer_example)

        assert success == True
        assert self.failed == False

        assert msg["properties"] == {"property": "value"}
        assert msg["name"] == "test customer"
        assert msg["customer_id"] == "customer_id"
        assert msg["$type"] == "create_customer"

    def test_basic_create_subscription(self, create_subscription_example):
        client = self.client
        success, msg = client.create_subscription(**create_subscription_example)
        client.flush()
        assert success == True
        assert self.failed == False

        assert isinstance(msg["start_date"], str)
        assert msg["billing_plan_id"] == "my_id"
        assert msg["customer_id"] == "customer_id"
        assert msg["$type"] == "create_subscription"

    def test_basic_cancel_subscription(self, cancel_subscription_example):
        client = self.client
        success, msg = client.cancel_subscription(**cancel_subscription_example)
        client.flush()

        assert success == True
        assert self.failed == False

        assert msg["subscription_id"] == "subscription_id"
        assert msg["bill_now"] == "True"
        assert msg["$type"] == "cancel_subscription"

    def test_basic_get_access(self, get_customer_access_example):
        client = self.client
        success, msg = client.get_customer_access(**get_customer_access_example)
        client.flush()

        assert success == True
        assert self.failed == False

        assert msg["customer_id"] == "customer_id"
        assert msg["event_name"] == "event_name"
        assert msg["$type"] == "get_customer_access"

    def test_flush(self, track_event_example):
        client = self.client
        # set up the consumer with more requests than a single batch will allow
        for i in range(1000):
            payload = track_event_example()
            success, msg = client.track_event(**payload)
        # We can't reliably assert that the queue is non-empty here; that's
        # a race condition. We do our best to load it up though.
        client.flush()
        # Make sure that the client queue is empty after flushing
        assert client.queue.empty() == True

    def test_shutdown(self, track_event_example):
        client = self.client
        # set up the consumer with more requests than a single batch will allow
        for i in range(1000):
            payload = track_event_example()
            payload["idempotency_id"] = str(i)
            success, msg = client.track_event(**payload)
        client.shutdown()
        # we expect two things after shutdown:
        # 1. client queue is empty
        # 2. consumer thread has stopped
        assert client.queue.empty() == True
        for consumer in client.consumers:
            assert consumer.is_alive() == False

    def test_overflow(self, track_event_example):
        client = Client(API_KEY, max_queue_size=1)
        # Ensure consumer thread is no longer uploading
        client.join()

        for i in range(10):
            payload = track_event_example()
            client.track_event(**payload)

        success, msg = client.track_event(**track_event_example())
        # Make sure we are informed that the queue is at capacity
        assert success == False

    def test_failure_on_invalid_api_key(self, track_event_example):
        client = Client(
            "bad_key",
            host="http://localhost:8000",
            on_error=self.fail,
        )
        client.track_event(**track_event_example())
        client.flush()
        assert self.failed == True

    def test_unicode(self):
        Client(six.u("unicode_key"))

    def test_numeric_distinct_id(self, track_event_example):
        self.client.track_event(**track_event_example())
        self.client.flush()
        assert self.failed == False

    def test_debug(self):
        Client("bad_key", debug=True)

    def test_gzip(self, track_event_example):
        client = Client(API_KEY, on_error=self.fail, gzip=True)
        for i in range(10):
            payload = track_event_example()
            client.track_event(**payload)
        with mock.patch("lotus.consumer.post") as mock_post:
            client.flush()
        assert self.failed == False

    def test_user_defined_flush_at(self, track_event_example):
        client = Client(API_KEY, on_error=self.fail, flush_at=10, flush_interval=3)

        def mock_post_fn(*args, **kwargs):
            assert len(kwargs["body"]["batch"]) == 10

        # the post function should be called 2 times, with a batch size of 10
        # each time.
        with mock.patch("lotus.consumer.post", side_effect=mock_post_fn) as mock_post:
            for i in range(20):
                payload = track_event_example()
                client.track_event(**payload)
            time.sleep(1)
            assert mock_post.call_count == 2

    def test_user_defined_timeout(self):
        client = Client(API_KEY, timeout=10)
        for consumer in client.consumers:
            assert consumer.timeout == 10

    def test_default_timeout_15(self):
        client = Client(API_KEY)
        for consumer in client.consumers:
            assert consumer.timeout == 15
