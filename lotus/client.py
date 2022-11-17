import atexit
import logging
import numbers
import uuid
from datetime import datetime
from queue import Full, Queue

from dateutil.parser import parse
from dateutil.tz import tzutc
from six import string_types

from .consumer import Consumer
from .request import post
from .utils import clean, guess_timezone, remove_trailing_slash
from .version import VERSION

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
            # track event
            "track_event": {
                "url": "/api/track/",
                "name": "track_event",
                "method": "POST",
            },
            # customer
            "get_all_customers": {
                "url": "/api/customers/",
                "name": "get_all_customers",
                "method": "GET",
            },
            "get_customer_detail": {
                "url": "/api/customer_detail/",
                "name": "get_customer_detail",
                "method": "GET",
            },
            "create_customer": {
                "url": "/api/customers/",
                "name": "create_customer",
                "method": "POST",
            },
            # subscription
            "create_subscription": {
                "url": "/api/subscriptions/",
                "name": "create_subscription",
                "method": "POST",
            },
            "cancel_subscription": {
                "url": "/api/subscriptions/",
                "name": "cancel_subscription",
                "method": "PATCH",
            },
            "get_all_subscriptions": {
                "url": "/api/subscriptions/",
                "name": "get_all_subscriptions",
                "method": "GET",
            },
            "get_subscription_detail": {
                "url": "/api/subscriptions/",
                "name": "get_subscription_detail",
                "method": "GET",
            },
            "change_subscription_plan": {
                "url": "/api/subscriptions/",
                "name": "change_subscription_plan",
                "method": "PATCH",
            },
            # get access
            "get_customer_access": {
                "url": "/api/customer_access/",
                "name": "get_customer_access",
                "method": "GET",
            },
            # plans
            "get_all_plans": {
                "url": "/api/plans/",
                "name": "get_all_plans",
                "method": "GET",
            },
        }

        self.queue = Queue(max_queue_size)
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
                if not host:
                    host = "https://www.uselotus.app"
                endpoint_host = host + "/api/track/"
                consumer = Consumer(
                    self.queue,
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

    def get_all_customers(
        self,
    ):

        msg = {
            "$type": "get_all_customers",
        }

        return self._enqueue(msg, block=True)

    def get_customer_detail(
        self,
        customer_id=None,
    ):
        require("customer_id", customer_id, ID_TYPES)

        msg = {
            "$type": "get_customer_detail",
            "customer_id": customer_id,
        }

        return self._enqueue(msg, block=True)

    def create_customer(
        self,
        customer_id=None,
        customer_name=None,
        balance=None,
    ):
        properties = properties or {}
        require("customer_id", customer_id, ID_TYPES)
        require("customer_name", customer_name, ID_TYPES)

        msg = {
            "$type": "create_customer",
            "name": customer_name,
            "customer_id": customer_id,
            "properties": properties,
        }
        if balance:
            msg["balance"] = balance

        return self._enqueue(msg, block=True)

    def create_subscription(
        self,
        customer_id=None,
        plan_id=None,
        start_date=None,
        end_date=None,
        status=None,
        auto_renew=None,
        is_new=None,
        subscription_id=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        require("plan_id", plan_id, ID_TYPES)
        require("start_date", start_date, ID_TYPES)

        msg = {
            "$type": "create_subscription",
            "start_date": start_date,
            "plan_id": plan_id,
            "customer_id": customer_id,
        }
        if end_date:
            msg["end_date"] = end_date
        if status:
            msg["status"] = status
        if auto_renew:
            msg["auto_renew"] = auto_renew
        if is_new:
            msg["is_new"] = is_new
        if subscription_id:
            msg["subscription_id"] = subscription_id

        return self._enqueue(msg, block=True)

    def cancel_subscription(
        self,
        subscription_id=None,
        turn_off_auto_renew=None,
        replace_immediately_type=None,
    ):
        require("subscription_id", subscription_id, ID_TYPES)
        assert (
            turn_off_auto_renew is True or replace_immediately_type is not None
        ), "Must provide either turn_off_auto_renew or replace_immediately_type"
        if turn_off_auto_renew is None:
            assert replace_immediately_type in [
                "end_current_subscription_and_bill",
                "end_current_subscription_dont_bill",
            ], "replace_immediately_type must be one of 'end_current_subscription_and_bill', 'end_current_subscription_dont_bill' when using status"
        msg = {
            "$type": "cancel_subscription",
            "$append_to_url": subscription_id,
        }
        if turn_off_auto_renew:
            msg["auto_renew"] = False
        else:
            msg["status"] = "ended"
            msg["replace_immediately_type"] = replace_immediately_type

        return self._enqueue(msg, block=True)

    def get_all_subscriptions(
        self,
    ):

        msg = {
            "$type": "get_all_subscriptions",
        }

        return self._enqueue(msg, block=True)

    def get_subscription_detail(
        self,
        subscription_id=None,
    ):

        msg = {
            "$type": "get_subscription_detail",
            "$append_to_url": subscription_id,
        }

        return self._enqueue(msg, block=True)

    def change_subscription_plan(
        self,
        subscription_id=None,
        plan_id=None,
        replace_immediately_type=None,
    ):
        require("subscription_id", subscription_id, ID_TYPES)
        require("plan_id", plan_id, ID_TYPES)
        assert replace_immediately_type in [
            "end_current_subscription_and_bill",
            "end_current_subscription_dont_bill",
            "change_subscription_plan",
        ], "Invalid replace_immediately_type"

        msg = {
            "$type": "cancel_subscription",
            "$append_to_url": subscription_id,
            "plan_id": plan_id,
            "replace_immediately_type": replace_immediately_type,
        }

        return self._enqueue(msg, block=True)

    def get_all_plans(
        self,
    ):

        msg = {
            "$type": "get_all_plans",
        }

        return self._enqueue(msg, block=True)

    def get_customer_access(
        self,
        customer_id=None,
        event_name=None,
        feature_name=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        if not event_name and not feature_name:
            raise ValueError("Must provide event_name or feature_name")
        elif event_name and feature_name:
            raise ValueError("Can't provide both event_name and feature_name")

        msg = {
            "$type": "get_customer_access",
            "customer_id": customer_id,
        }
        if event_name:
            msg["event_name"] = event_name
        elif feature_name:
            msg["feature_name"] = feature_name

        return self._enqueue(msg, block=True)

    def _enqueue(self, msg, block=False):
        """Push a new `msg` onto the queue, return `(success, msg)`"""
        msg["library"] = "lotus-python"
        msg["library_version"] = VERSION

        if "idempotency_id" in msg:
            msg["idempotency_id"] = stringify_id(msg.get("idempotency_id", None))
        if "customer_id" in msg:
            msg["customer_id"] = stringify_id(msg.get("customer_id", None))

        msg = clean(msg)
        self.log.debug("queueing: %s", msg)

        # if send is False, return msg as if it was successfully queued
        if not self.send:
            return True, msg

        if self.sync_mode or block:
            operation = msg["$type"]
            endpoint_url = self.operations[operation]["url"]
            if "$append_to_url" in msg:
                endpoint_url = endpoint_url + msg["$append_to_url"] + "/"
                del msg["$append_to_url"]
            if self.host:
                endpoint_host = self.host + endpoint_url
            else:
                endpoint_host = "https://www.uselotus.app" + endpoint_url
            self.log.debug("enqueued msg to %s with blocking %s.", endpoint_host, msg["$type"])
            response = post(
                endpoint_host,
                api_key=self.api_key,
                gzip=self.gzip,
                timeout=self.timeout,
                body=msg,
                method=self.operations[operation]["method"],
            )

            try:
                data = response.json()
            except:
                data = response.text

            return data

        try:
            self.queue.put(msg, block=False)
            self.log.debug("enqueued %s.", msg["$type"])
            return True, msg
        except Full:
            self.log.warning("queue is full")
            return False, msg

    def flush(self):
        """Forces a flush from the internal queue to the server"""
        queue = self.queue
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
