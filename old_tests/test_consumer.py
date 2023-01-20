import json
import time
from queue import Queue

import mock

from lotus.consumer import MAX_MSG_SIZE, Consumer
from lotus.request import APIError


class TestConsumer:
    def test_next(self):
        q = Queue()
        consumer = Consumer(q, "")
        q.put(1)
        next = consumer.next()
        assert next == [1]

    def test_next_limit(self):
        q = Queue()
        flush_at = 50
        consumer = Consumer(q, "", flush_at)
        for i in range(10000):
            q.put(i)
        next = consumer.next()
        assert next == list(range(flush_at))

    def test_dropping_oversize_msg(self):
        q = Queue()
        consumer = Consumer(q, "")
        oversize_msg = {"m": "x" * MAX_MSG_SIZE}
        q.put(oversize_msg)
        next = consumer.next()
        assert next == []
        assert q.empty()

    def test_upload(self, track_event_example):
        q = Queue()
        consumer = Consumer(q, "testsecret")
        track = track_event_example()
        with mock.patch("lotus.consumer.post") as mock_post:
            q.put(track)
            success = consumer.upload()
        assert success == True

    def test_flush_interval(self, track_event_example):
        # Put _n_ items in the queue, pausing a little bit more than
        # _flush_interval_ after each one.
        # The consumer should upload _n_ times.
        q = Queue()
        flush_interval = 0.3
        consumer = Consumer(q, "testsecret", flush_at=10, flush_interval=flush_interval)
        with mock.patch("lotus.consumer.post") as mock_post:
            consumer.start()
            for i in range(0, 3):
                track = track_event_example()
                q.put(track)
                time.sleep(flush_interval * 1.1)
            assert mock_post.call_count == 3

    def test_multiple_uploads_per_interval(self, track_event_example):
        # Put _flush_at*2_ items in the queue at once, then pause for
        # _flush_interval_. The consumer should upload 2 times.
        q = Queue()
        flush_interval = 0.5
        flush_at = 10
        consumer = Consumer(q, "testsecret", flush_at=flush_at, flush_interval=flush_interval)
        with mock.patch("lotus.consumer.post") as mock_post:
            consumer.start()
            for i in range(0, flush_at * 2):
                track = track_event_example()
                q.put(track)
            time.sleep(flush_interval * 1.1)
            assert mock_post.call_count == 2

    def test_request(self, track_event_example):
        def mock_post(*args, **kwargs):
            mock_post.call_count += 1

        mock_post.call_count = 0

        with mock.patch("lotus.consumer.post", mock.Mock(side_effect=mock_post)):
            consumer = Consumer(None, "testsecret")
            track = track_event_example()
            consumer.request([track])

        assert mock_post.call_count == 1

    def _test_request_retry(
        self, consumer, expected_exception, exception_count, track_event_example
    ):
        def mock_post(*args, **kwargs):
            mock_post.call_count += 1
            if mock_post.call_count <= exception_count:
                raise expected_exception

        mock_post.call_count = 0

        with mock.patch("lotus.consumer.post", mock.Mock(side_effect=mock_post)):
            track = track_event_example()
            # request() should succeed if the number of exceptions raised is
            # less than the retries paramater.
            if exception_count <= consumer.retries:
                consumer.request([track])
            else:
                # if exceptions are raised more times than the retries
                # parameter, we expect the exception to be returned to
                # the caller.
                try:
                    consumer.request([track])
                except type(expected_exception) as exc:
                    assert exc == expected_exception
                else:
                    self.fail(
                        "request() should raise an exception if still failing "
                        "after %d retries" % consumer.retries
                    )

    def test_request_retry(self, track_event_example):
        # we should retry on general errors
        consumer = Consumer(None, "testsecret")
        self._test_request_retry(
            consumer, Exception("generic exception"), 2, track_event_example()
        )

        # we should retry on server errors
        consumer = Consumer(None, "testsecret")
        self._test_request_retry(
            consumer,
            APIError(500, "code", "Internal Server Error"),
            2,
            track_event_example(),
        )

        # we should retry on HTTP 429 errors
        consumer = Consumer(None, "testsecret")
        self._test_request_retry(
            consumer,
            APIError(429, "code", "Too Many Requests"),
            2,
            track_event_example(),
        )

        # we should NOT retry on other client errors
        consumer = Consumer(None, "testsecret")
        api_error = APIError(400, "code", "Client Errors")
        try:
            self._test_request_retry(consumer, api_error, 1, track_event_example())
        except APIError:
            pass
        else:
            self.fail("request() should not retry on client errors")

        # test for number of exceptions raise > retries value
        consumer = Consumer(None, "testsecret", retries=3)
        self._test_request_retry(
            consumer,
            APIError(500, "code", "Internal Server Error"),
            3,
            track_event_example(),
        )

    def test_pause(self):
        consumer = Consumer(None, "testsecret")
        consumer.pause()
        assert consumer.running == False

    def test_max_batch_size(self, track_event_example):
        q = Queue()
        consumer = Consumer(q, "testsecret", flush_at=100000, flush_interval=3)
        track = track_event_example()
        msg_size = len(json.dumps(track).encode())
        # number of messages in a maximum-size batch
        n_msgs = int(475000 / msg_size)

        def mock_post_fn(_, data, **kwargs):
            res = mock.Mock()
            res.status_code = 200
            assert len(data.encode()) < 500000, "batch size (%d) exceeds 500KB limit" % len(
                data.encode()
            )
            return res

        with mock.patch("lotus.request._session.post", side_effect=mock_post_fn) as mock_post:
            consumer.start()
            for _ in range(0, n_msgs + 2):
                q.put(track)
            q.join()
            assert mock_post.call_count == 2
