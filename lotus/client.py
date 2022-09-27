import atexit
import logging
import numbers
import uuid
from datetime import datetime
from queue import Full, Queue

from dateutil.parser import parse
from dateutil.tz import tzutc
from six import string_types

from lotus.consumer import Consumer
from lotus.request import post
from lotus.utils import clean, guess_timezone, remove_trailing_slash
from lotus.version import VERSION

# try:

# except ImportError:
#     import Queue as queue


ID_TYPES = (numbers.Number, string_types)


class Client(object):
    """Create a new Lotus client."""

    log = logging.getLogger("lotus")

    def __init__(
        self,
        api_key=None,
        host=None,
        debug=False,
        max_queue_size=10000,
        send=True,
        on_error=None,
        flush_at=100,
        flush_interval=0.5,
        gzip=False,
        max_retries=3,
        sync_mode=False,
        timeout=15,
        thread=1,
    ):
        require("api_key", api_key, string_types)
        self.operations = {
            "track_event": {
                "url": "/api/track/",
                "name": "track_event",
            },
            "create_customer": {
                "url": "/api/customers/",
                "name": "create_customer",
            },
            "create_subscription": {
                "url": "/api/subscriptions/",
                "name": "create_subscription",
            },
            "cancel_subscription": {
                "url": "/api/cancel_subscription/",
                "name": "cancel_subscription",
            },
        }

        self.queue = {}
        for _, v in self.operations.items():
            self.queue[v["name"]] = Queue(max_queue_size)
        self.api_key = api_key
        self.on_error = on_error
        self.debug = debug
        self.send = send
        self.sync_mode = sync_mode
        self.host = host
        self.gzip = gzip
        self.timeout = timeout

        if debug:
            self.log.setLevel(logging.DEBUG)

        if sync_mode:
            self.consumers = None
        else:
            # On program exit, allow the consumer thread to exit cleanly.
            # This prevents exceptions and a messy shutdown when the
            # interpreter is destroyed before the daemon thread finishes
            # execution. However, it is *not* the same as flushing the queue!
            # To guarantee all messages have been delivered, you'll still need
            # to call flush().
            if send:
                atexit.register(self.join)
            for n in range(thread):
                self.consumers = []
                for operation, queue in self.queue.items():
                    if not host:
                        host = "https://www.uselotus.app"
                    endpoint_host = (
                        remove_trailing_slash(host)
                        + self.operations[operation]["url"]
                    )
                    consumer = Consumer(
                        queue,
                        api_key,
                        host=endpoint_host,
                        on_error=on_error,
                        flush_at=flush_at,
                        flush_interval=flush_interval,
                        gzip=gzip,
                        retries=max_retries,
                        timeout=timeout,
                    )
                    self.consumers.append(consumer)

                    # if we've disabled sending, just don't start the consumer
                    if send:
                        consumer.start()

    def track_event(
        self,
        customer_id=None,
        event_name=None,
        properties=None,
        time_created=None,
        idempotency_id=None,
    ):
        properties = properties or {}
        if idempotency_id is None:
            idempotency_id = str(uuid.uuid4())
        if time_created is None:
            time_created = datetime.now(tzutc())
        if type(time_created) is datetime:
            time_created = str(time_created)
        require("customer_id", customer_id, ID_TYPES)
        require("idempotency_id", idempotency_id, ID_TYPES)
        require("properties", properties, dict)
        require("event_name", event_name, string_types)
        require("time_created", time_created, string_types)

        msg = {
            "$type": "track_event",
            "properties": properties,
            "time_created": time_created,
            "customer_id": customer_id,
            "event_name": event_name,
            "idempotency_id": idempotency_id,
        }

        return self._enqueue(msg)

    def create_customer(
        self,
        customer_id=None,
        customer_name=None,
        currency=None,
        payment_provider_id=None,
        properties=None,
        balance=None,
    ):
        properties = properties or {}
        require("customer_id", customer_id, ID_TYPES)
        require("customer_name", customer_name, ID_TYPES)
        require("properties", properties, dict)

        msg = {
            "$type": "create_customer",
            "name": customer_name,
            "customer_id": customer_id,
            "properties": properties,
        }
        if currency:
            msg["currency"] = currency
        if payment_provider_id:
            msg["payment_provider_id"] = payment_provider_id
        if balance:
            msg["balance"] = balance

        return self._enqueue(msg)

    def create_subscription(
        self,
        customer_id=None,
        billing_plan_id=None,
        start_date=None,
        end_date=None,
        payment_provider_id=None,
        status=None,
        auto_renew=None,
        is_new=None,
        subscription_uid=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        require("billing_plan_id", billing_plan_id, ID_TYPES)
        require("start_date", start_date, ID_TYPES)

        msg = {
            "$type": "create_subscription",
            "start_date": start_date,
            "billing_plan_id": billing_plan_id,
            "customer_id": customer_id,
        }
        if end_date:
            msg["end_date"] = end_date
        if payment_provider_id:
            msg["payment_provider_id"] = payment_provider_id
        if status:
            msg["status"] = status
        if auto_renew:
            msg["auto_renew"] = auto_renew
        if is_new:
            msg["is_new"] = is_new
        if subscription_uid:
            msg["subscription_uid"] = subscription_uid

        return self._enqueue(msg)

    def cancel_subscription(
        self,
        subscription_uid=None,
        bill_now=None,
    ):
        require("subscription_uid", subscription_uid, ID_TYPES)

        msg = {
            "$type": "cancel_subscription",
            "subscription_uid": subscription_uid,
        }
        if bill_now:
            msg["bill_now"] = bill_now

        return self._enqueue(msg)

    def _enqueue(self, msg):
        """Push a new `msg` onto the queue, return `(success, msg)`"""

        msg["library"] = "lotus-python"
        msg['library_version'] = VERSION

        if "idempotency_id" in msg:
            msg["idempotency_id"] = stringify_id(msg.get("idempotency_id", None))
        if "customer_id" in msg:
            msg["customer_id"] = stringify_id(msg.get("customer_id", None))

        msg = clean(msg)
        self.log.debug("queueing: %s", msg)

        # if send is False, return msg as if it was successfully queued
        if not self.send:
            return True, msg

        if self.sync_mode:
            operation = msg["$type"]
            if self.host:
                endpoint_host = self.host + "/" + operation + "/"
            else:
                endpoint_host = None
            self.log.debug("enqueued with blocking %s.", msg["$type"])
            post(endpoint_host, gzip=self.gzip, timeout=self.timeout, batch=[msg])

            return True, msg
        try:
            operation = msg["$type"]
            self.queue[operation].put(msg, block=False)
            self.log.debug("enqueued %s.", msg["$type"])
            return True, msg
        except Full:
            self.log.warning("queue is full")
            return False, msg

    def flush(self):
        """Forces a flush from the internal queue to the server"""
        for operation, queue in self.queue.items():
            size = queue.qsize()
            queue.join()
            # Note that this message may not be precise, because of threading.
            self.log.debug("successfully flushed about %s items.", size)

    def join(self):
        """Ends the consumer thread once the queue is empty.
        Blocks execution until finished
        """
        for consumer in self.consumers:
            consumer.pause()
            try:
                consumer.join()
            except RuntimeError:
                # consumer thread has not started
                pass

    def shutdown(self):
        """Flush all messages and cleanly shutdown the client"""
        self.flush()
        self.join()


def require(name, field, data_type):
    """Require that the named `field` has the right `data_type`"""
    if not isinstance(field, data_type):
        msg = "{0} must have {1}, got: {2}".format(name, data_type, field)
        raise AssertionError(msg)


def stringify_id(val):
    if val is None:
        return None
    if isinstance(val, string_types):
        return val
    return str(val)