import atexit
import json
import logging
import numbers
import uuid
from datetime import datetime
from queue import Full, Queue

from dateutil.parser import parse
from dateutil.tz import tzutc
from pydantic import parse_obj_as
from six import string_types

from .consumer import Consumer
from .models import *
from .request import send
from .utils import HTTPMethod, clean, guess_timezone, remove_trailing_slash
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
                "method": HTTPMethod.POST,
            },
            # customer
            "list_customers": {
                "url": "/api/customers/",
                "name": "list_customers",
                "method": HTTPMethod.GET,
            },
            "get_customer": {
                "url": "/api/customers/",
                "name": "get_customer",
                "method": HTTPMethod.GET,
            },
            "create_customer": {
                "url": "/api/customers/",
                "name": "create_customer",
                "method": HTTPMethod.POST,
            },
            # subscription
            "create_subscription": {
                "url": "/api/subscriptions/add/",
                "name": "create_subscription",
                "method": HTTPMethod.POST,
            },
            "cancel_subscription": {
                "url": "/api/subscriptions/cancel/",
                "name": "cancel_subscription",
                "method": HTTPMethod.POST,
            },
            "update_subscription": {
                "url": "/api/subscriptions/update/",
                "name": "update_subscription",
                "method": HTTPMethod.POST,
            },
            "list_subscriptions": {
                "url": "/api/subscriptions/",
                "name": "list_subscriptions",
                "method": HTTPMethod.GET,
            },
            # get access
            "get_customer_metric_access": {
                "url": "/api/customer_metric_access/",
                "name": "get_customer_metric_access",
                "method": HTTPMethod.GET,
            },
            "get_customer_feature_access": {
                "url": "/api/customer_feature_access/",
                "name": "get_customer_feature_access",
                "method": HTTPMethod.GET,
            },
            # plans
            "list_plans": {
                "url": "/api/plans/",
                "name": "list_plans",
                "method": HTTPMethod.GET,
            },
            "get_plan": {
                "url": "/api/plans/",
                "name": "get_plan",
                "method": HTTPMethod.GET,
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
        *,
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

        body = {
            "$type": "track_event",
            "properties": properties,
            "time_created": time_created,
            "customer_id": customer_id,
            "event_name": event_name,
            "idempotency_id": idempotency_id,
        }

        return self._enqueue(body)

    def list_customers(
        self,
    ):

        body = {
            "$type": "list_customers",
        }

        ret = self._enqueue(body, block=True)
        obj = parse_obj_as(list[Customer], ret)
        return obj.json()

    def get_customer(
        self,
        *,
        customer_id=None,
    ):
        require("customer_id", customer_id, ID_TYPES)

        body = {
            "$type": "get_customer",
            "$append_to_url": customer_id,
        }

        ret = self._enqueue(body, block=True)
        obj = parse_obj_as(Customer, ret)
        return obj.json()

    def create_customer(
        self,
        *,
        customer_name=None,
        customer_id=None,
        email=None,
        payment_provider=None,
        payment_provider_id=None,
        properties=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        require("email", customer_name, ID_TYPES)

        if (payment_provider is None) != (payment_provider_id is None):
            raise ValueError(
                "Either both payment_provider and payment_provider_id must be provided, or neither"
            )

        body = {
            "$type": "create_customer",
            "customer_id": customer_id,
            "email": email,
            "properties": properties or {},
        }
        if customer_name:
            body["customer_name"] = customer_name

        if payment_provider:
            body["payment_provider"] = payment_provider

        if payment_provider_id:
            body["payment_provider_id"] = payment_provider_id

        ret = self._enqueue(body, block=True)
        obj = parse_obj_as(Customer, ret)
        return obj.json()

    # def create_batch_customers(
    #     self,
    #     *,
    #     customers=[],
    #     behavior_on_existing=None,
    # ):
    #     for customer in customers:
    #         require("customer_id", customer.customer_id, ID_TYPES)
    #         require("email", customer.email, ID_TYPES)

    #     require("behavior_on_existing", behavior_on_existing, ID_TYPES)

    #     if behavior_on_existing not in ["merge", "ignore", "overwrite"]:
    #         raise ValueError("Must provide valid value for behavior_on_existing")

    #     body = {
    #         "$type": "create_batch_customers",
    #         "customers": customers,
    #         "behavior_on_existing": behavior_on_existing,
    #     }

    #     return self._enqueue(body, block=True)

    def create_subscription(
        self,
        *,
        customer_id=None,
        plan_id=None,
        start_date=None,
        end_date=None,
        auto_renew=None,
        is_new=None,
        subscription_filters=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        require("plan_id", plan_id, ID_TYPES)
        require("start_date", start_date, ID_TYPES)

        for filter in subscription_filters or []:
            require("property_name", filter["property_name"], ID_TYPES)
            require("value", filter["value"], ID_TYPES)

        body = {
            "$type": "create_subscription",
            "start_date": start_date,
            "plan_id": plan_id,
            "customer_id": customer_id,
        }
        if end_date:
            body["end_date"] = end_date
        if auto_renew:
            body["auto_renew"] = auto_renew
        if is_new:
            body["is_new"] = is_new
        if subscription_filters:
            body["subscription_filters"] = subscription_filters

        ret = self._enqueue(body, block=True)
        obj = parse_obj_as(SubscriptionRecord, ret)
        return obj.json()

    def cancel_subscription(
        self,
        *,
        customer_id=None,
        plan_id=None,
        subscription_filters=None,
        flat_fee_behavior=None,
        usage_behavior=None,
        invoicing_behavior=None,
    ):
        if plan_id:
            require("plan_id", plan_id, ID_TYPES)
        if customer_id:
            require("customer_id", customer_id, ID_TYPES)
        for filter in subscription_filters or []:
            require("property_name", filter["property_name"], ID_TYPES)
            require("value", filter["value"], ID_TYPES)
        if usage_behavior is not None:
            assert usage_behavior in [
                "bill_full",
                "bill_none",
            ], "usage_behavior must be one of 'bill_full' or 'bill_none'"
        if invoicing_behavior is not None:
            assert invoicing_behavior in [
                "add_to_next_invoice",
                "invoice_now",
            ], "invoicing_behavior must be one of 'add_to_next_invoice' or 'invoice_now'"
        if flat_fee_behavior is not None:
            assert flat_fee_behavior in [
                "refund",
                "prorate",
                "charge_full",
            ], "flat_fee_behavior must be one of 'refund', 'prorate', or 'charge_full'"

        body = {
            "$type": "cancel_subscription",
        }

        query = {}
        if plan_id:
            query["plan_id"] = plan_id
        if customer_id:
            query["customer_id"] = customer_id
        if subscription_filters:
            query["subscription_filters"] = json.dumps(subscription_filters)
        if flat_fee_behavior:
            body["flat_fee_behavior"] = flat_fee_behavior
        if usage_behavior:
            body["usage_behavior"] = usage_behavior
        if invoicing_behavior:
            body["invoicing_behavior"] = invoicing_behavior

        ret = self._enqueue(body, query=query, block=True)
        obj = parse_obj_as(list[SubscriptionRecord], ret)
        return obj.json()

    def list_subscriptions(
        self,
        status=None,
    ):
        for s in status or []:
            assert s in [
                "active",
                "ended",
                "not_started",
            ], "Invalid status"

        body = {
            "$type": "list_subscriptions",
        }
        query = {}
        if status is not None:
            query["status"] = status

        ret = self._enqueue(body, query=query, block=True)
        obj = parse_obj_as(list[SubscriptionRecord], ret)
        return obj.json()

    def update_subscription(
        self,
        customer_id=None,
        plan_id=None,
        subscription_filters=None,
        replace_plan_id=None,
        invoicing_behavior=None,
        usage_behavior=None,
        turn_off_auto_renew=None,
        end_date=None,
    ):
        if plan_id:
            require("plan_id", plan_id, ID_TYPES)
        if customer_id:
            require("customer_id", customer_id, ID_TYPES)
        for filter in subscription_filters or []:
            require("property_name", filter["property_name"], ID_TYPES)
            require("value", filter["value"], ID_TYPES)
        if replace_plan_id:
            require("replace_plan_id", replace_plan_id, ID_TYPES)
        if invoicing_behavior is not None:
            assert invoicing_behavior in [
                "transfer_to_new_subscription",
                "keep_separate",
            ], "invoicing_behavior must be one of 'transfer_to_new_subscription' or 'keep_separate'"
        if usage_behavior is not None:
            assert invoicing_behavior in [
                "add_to_next_invoice",
                "invoice_now",
            ], "usage_behavior must be one of 'add_to_next_invoice' or 'invoice_now'"
        if turn_off_auto_renew is not None:
            require("turn_off_auto_renew", turn_off_auto_renew, bool)
        if end_date:
            require("end_date", end_date, str)

        query = {}
        if plan_id:
            query["plan_id"] = plan_id
        if customer_id:
            query["customer_id"] = customer_id
        if subscription_filters:
            query["subscription_filters"] = json.dumps(subscription_filters)

        body = {
            "$type": "update_subscription",
        }
        if replace_plan_id:
            body["replace_plan_id"] = replace_plan_id
        if invoicing_behavior:
            body["invoicing_behavior"] = invoicing_behavior
        if turn_off_auto_renew:
            body["turn_off_auto_renew"] = turn_off_auto_renew
        if end_date:
            body["end_date"] = end_date
        if usage_behavior:
            body["usage_behavior"] = usage_behavior

        ret = self._enqueue(body, query=query, block=True)
        obj = parse_obj_as(list[SubscriptionRecord], ret)
        return obj.json()

    def list_plans(
        self,
    ):

        body = {
            "$type": "list_plans",
        }

        ret = self._enqueue(body, block=True)
        obj = parse_obj_as(list[Plan], ret)
        return obj.json()

    def get_plan(
        self,
        *,
        plan_id=None,
    ):
        require("plan_id", plan_id, ID_TYPES)

        body = {
            "$type": "get_customer",
            "$append_to_url": plan_id,
        }
        ret = self._enqueue(body, block=True)
        obj = parse_obj_as(Plan, ret)
        return obj.json()

    def get_customer_metric_access(
        self,
        customer_id=None,
        event_name=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        if not event_name:
            raise ValueError("Must provide event_name")

        body = {
            "$type": "get_customer_metric_access",
        }
        query = {
            "customer_id": customer_id,
            "event_name": event_name,
        }

        ret = self._enqueue(body, query=query, block=True)
        obj = parse_obj_as(list[GetEventAccess], ret)
        return obj.json()

    def get_customer_feature_access(
        self,
        customer_id=None,
        feature_name=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        if not feature_name:
            raise ValueError("Must provide feature_name")

        body = {
            "$type": "get_customer_feature_access",
        }
        query = {
            "customer_id": customer_id,
            "feature_name": feature_name,
        }

        ret = self._enqueue(body, query=query, block=True)
        obj = parse_obj_as(list[GetFeatureAccess], ret)
        return obj.json()

    def _enqueue(self, body, query=None, block=False):
        """Push a new `body` onto the queue, return `(success, body)`"""
        body["library"] = "lotus-python"
        body["library_version"] = VERSION

        if "idempotency_id" in body:
            body["idempotency_id"] = stringify_id(body.get("idempotency_id", None))
        if "customer_id" in body:
            body["customer_id"] = stringify_id(body.get("customer_id", None))

        body = clean(body)
        self.log.debug("queueing: %s", body)

        # if send is False, return body as if it was successfully queued
        if not self.send:
            return True, body

        if self.sync_mode or block:
            operation = body["$type"]
            endpoint_url = self.operations[operation]["url"]
            if "$append_to_url" in body:
                endpoint_url = endpoint_url + body["$append_to_url"] + "/"
                del body["$append_to_url"]
            if self.host:
                endpoint_host = self.host + endpoint_url
            else:
                endpoint_host = "https://www.uselotus.app" + endpoint_url
            self.log.debug(
                "enqueued body to %s with blocking %s.", endpoint_host, body["$type"]
            )
            response = send(
                endpoint_host,
                api_key=self.api_key,
                gzip=self.gzip,
                timeout=self.timeout,
                body=body,
                query=query,
                method=self.operations[operation]["method"],
            )

            try:
                data = response.json()
            except:
                data = response.text

            return data

        try:
            self.queue.put(body, block=False)
            self.log.debug("enqueued %s.", body["$type"])
            return True, body
        except Full:
            self.log.warning("queue is full")
            return False, body

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
        body = "{0} must have {1}, got: {2}".format(name, data_type, field)
        raise AssertionError(body)


def stringify_id(val):
    if val is None:
        return None
    if isinstance(val, string_types):
        return val
    return str(val)
