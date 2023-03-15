import atexit
import logging
import numbers
import uuid
from datetime import datetime
from decimal import Decimal
from queue import Full, Queue

from dateutil.tz import tzutc
from pydantic import parse_obj_as
from six import string_types

from .consumer import Consumer
from .models import (
    AddOnSubscriptionRecord,
    Customer,
    CustomerBalanceAdjustment,
    FeatureAccessResponse,
    GetEventAccess,
    GetFeatureAccess,
    MetricAccessResponse,
    Plan,
    SubscriptionRecord,
)
from .request import send
from .utils import HTTPMethod, clean
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
        strict=False,
        timeout=15,
        thread=1,
    ):
        require("api_key", api_key, string_types)
        self.operations = {
            # ping
            "ping": {
                "url": "/api/ping/",
                "name": "ping",
                "method": HTTPMethod.GET,
            },
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
            # "batch_create_customers": {
            #     "url": "/api/batch_create_customers/",
            #     "name": "batch_create_customers",
            #     "method": HTTPMethod.POST,
            # },
            # credits
            "list_credits": {
                "url": "/api/credits/",
                "name": "list_credits",
                "method": HTTPMethod.GET,
            },
            "create_credit": {
                "url": "/api/credits/",
                "name": "create_credit",
                "method": HTTPMethod.POST,
            },
            "update_credit": {
                "url": "/api/credits/",
                "name": "update_credit",
                "method": HTTPMethod.POST,
            },
            "void_credit": {
                "url": "/api/credits/",
                "name": "void_credit",
                "method": HTTPMethod.POST,
            },
            # subscription
            "create_subscription": {
                "url": "/api/subscriptions/",
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
            "switch_subscription_plan": {
                "url": "/api/subscriptions/switch_plan/",
                "name": "switch_subscription_plan",
                "method": HTTPMethod.POST,
            },
            "list_subscriptions": {
                "url": "/api/subscriptions/",
                "name": "list_subscriptions",
                "method": HTTPMethod.GET,
            },
            # addons - attach, cancel, update
            "attach_addon": {
                "url": "/api/subscriptions/addons/add/",
                "name": "attach_addon",
                "method": HTTPMethod.POST,
            },
            "cancel_addon": {
                "url": "/api/subscriptions/addons/cancel/",
                "name": "cancel_addon",
                "method": HTTPMethod.POST,
            },
            # "update_addon": {
            #     "url": "/api/subscriptions/addons/update/",
            #     "name": "update_addon",
            #     "method": HTTPMethod.POST,
            # },
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
            "check_metric_access": {
                "url": "/api/metric_access/",
                "name": "check_metric_access",
                "method": HTTPMethod.GET,
            },
            "check_feature_access": {
                "url": "/api/feature_access/",
                "name": "check_feature_access",
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
        self.strict = strict

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
                    host = "https://api.uselotus.io"
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
        if self.strict:
            return [x.dict() for x in parse_obj_as(list[Customer], ret)]
        else:
            return [Customer.construct(**x).dict() for x in ret]

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
        if self.strict:
            return parse_obj_as(Customer, ret).dict()
        else:
            return Customer.construct(**ret).dict()

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
        if self.strict:
            return parse_obj_as(Customer, ret).dict()
        else:
            return Customer.construct(**ret).dict()

    def list_credits(
        self,
        customer_id=None,
        currency_code=None,
        effective_after=None,
        effective_before=None,
        expires_after=None,
        expires_before=None,
        issued_after=None,
        issued_before=None,
        status=None,
    ):
        require("customer_id", customer_id, ID_TYPES)

        body = {
            "$type": "list_credits",
        }
        query = {
            "customer_id": customer_id,
        }
        if currency_code:
            query["currency_code"] = currency_code
        if effective_after:
            require("effective_after", effective_after, datetime)
            query["effective_after"] = effective_after
        if effective_before:
            require("effective_before", effective_before, datetime)
            query["effective_before"] = effective_before
        if expires_after:
            require("expires_after", expires_after, datetime)
            query["expires_after"] = expires_after
        if expires_before:
            require("expires_before", expires_before, datetime)
            query["expires_before"] = expires_before
        if issued_after:
            require("issued_after", issued_after, datetime)
            query["issued_after"] = issued_after
        if issued_before:
            require("issued_before", issued_before, datetime)
            query["issued_before"] = issued_before
        if status:
            assert isinstance(status, list) is True, "status must be a list of strings"
        for s in status or []:
            assert s in [
                "active",
                "inactive",
            ], "Invalid status"
            body["status"] = status

        ret = self._enqueue(body, block=True, query=query)
        if self.strict:
            return [
                x.dict() for x in parse_obj_as(list[CustomerBalanceAdjustment], ret)
            ]
        else:
            return [CustomerBalanceAdjustment.construct(**x).dict() for x in ret]

    def create_credit(
        self,
        customer_id=None,  # required
        amount=None,  # required
        currency_code=None,  # required
        description=None,
        effective_at=None,
        expires_at=None,
        amount_paid=None,
        amount_paid_currency_code=None,
    ):

        require("customer_id", customer_id, ID_TYPES)
        require("amount", amount, (float, int, Decimal))
        require("currency_code", currency_code, string_types)

        body = {
            "$type": "create_credit",
            "customer_id": customer_id,
            "amount": amount,
            "currency_code": currency_code,
        }
        if description:
            require("description", description, string_types)
            body["description"] = description
        if effective_at:
            require("effective_at", effective_at, datetime)
            body["effective_at"] = effective_at
        if expires_at:
            require("expires_at", expires_at, datetime)
            body["expires_at"] = expires_at
        if amount_paid:
            require("amount_paid", amount_paid, (float, int, Decimal))
            body["amount_paid"] = amount_paid
        if amount_paid_currency_code:
            require(
                "amount_paid_currency_code", amount_paid_currency_code, string_types
            )
            body["amount_paid_currency_code"] = amount_paid_currency_code

        ret = self._enqueue(body, block=True)
        if self.strict:
            return parse_obj_as(CustomerBalanceAdjustment, ret).dict()
        else:
            return CustomerBalanceAdjustment.construct(**ret).dict()

    def update_credit(
        self,
        credit_id=None,
        description=None,
        expires_at=None,
    ):
        require("credit_id", credit_id, ID_TYPES)

        body = {
            "$type": "update_credit",
            "$append_to_url": credit_id,
        }
        if description:
            require("description", description, string_types)
            body["description"] = description
        if expires_at:
            require("expires_at", expires_at, datetime)
            body["expires_at"] = expires_at

        ret = self._enqueue(body, block=True)
        if self.strict:
            return parse_obj_as(CustomerBalanceAdjustment, ret).dict()
        else:
            return CustomerBalanceAdjustment.construct(**ret).dict()

    def void_credit(
        self,
        credit_id=None,
    ):
        require("credit_id", credit_id, ID_TYPES)

        body = {
            "$type": "void_credit",
            "$append_to_url": credit_id,
        }

        ret = self._enqueue(body, block=True)
        if self.strict:
            return parse_obj_as(CustomerBalanceAdjustment, ret).dict()
        else:
            return CustomerBalanceAdjustment.construct(**ret).dict()

    def batch_create_customers(
        self,
        *,
        customers=[],
        behavior_on_existing=None,
    ):
        for customer in customers:
            require("customer_id", customer.customer_id, ID_TYPES)
            require("email", customer.email, ID_TYPES)

        require("behavior_on_existing", behavior_on_existing, ID_TYPES)

        if behavior_on_existing not in ["merge", "ignore", "overwrite"]:
            raise ValueError("Must provide valid value for behavior_on_existing")

        body = {
            "$type": "batch_create_customers",
            "customers": customers,
            "behavior_on_existing": behavior_on_existing,
        }

        return self._enqueue(body, block=True)

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
        version_id=None,
        metadata=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        if plan_id:
            require("plan_id", plan_id, ID_TYPES)
            assert version_id is None, "Cannot specify both plan_id and version_id"
        if version_id:
            require("version_id", version_id, ID_TYPES)
            assert plan_id is None, "Cannot specify both plan_id and version_id"
        require("start_date", start_date, ID_TYPES)
        if metadata:
            require("metadata", metadata, dict)
            for key, value in metadata.items():
                require("metadata key", key, (string_types, numbers.Number))
                require("metadata value", value, (string_types, numbers.Number))

        for filter in subscription_filters or []:
            require("property_name", filter["property_name"], ID_TYPES)
            require("value", filter["value"], ID_TYPES)

        body = {
            "$type": "create_subscription",
            "start_date": start_date,
            "customer_id": customer_id,
        }
        if plan_id:
            body["plan_id"] = plan_id
        elif version_id:
            body["version_id"] = version_id
        else:
            raise ValueError("Must provide either plan_id or version_id")
        if end_date:
            body["end_date"] = end_date
        if auto_renew:
            body["auto_renew"] = auto_renew
        if is_new:
            body["is_new"] = is_new
        if subscription_filters:
            body["subscription_filters"] = subscription_filters
        if metadata:
            body["metadata"] = metadata

        ret = self._enqueue(body, block=True)
        if self.strict:
            return parse_obj_as(SubscriptionRecord, ret).dict()
        else:
            return SubscriptionRecord.construct(**ret).dict()

    def cancel_subscription(
        self,
        *,
        subscription_id=None,
        flat_fee_behavior=None,
        usage_behavior=None,
        invoicing_behavior=None,
    ):
        require("subscription_id", subscription_id, ID_TYPES)
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
        if flat_fee_behavior:
            body["flat_fee_behavior"] = flat_fee_behavior
        if usage_behavior:
            body["usage_behavior"] = usage_behavior
        if invoicing_behavior:
            body["invoicing_behavior"] = invoicing_behavior
        query = {}

        if subscription_id:
            ret = self._enqueue(
                body,
                query=query,
                block=True,
                endpoint_url=f"/api/subscriptions/{subscription_id}/cancel/",
            )

        if self.strict:
            return parse_obj_as(SubscriptionRecord, ret).dict()
        else:
            return SubscriptionRecord.construct(**ret)

    def list_subscriptions(
        self,
        status=None,
        customer_id=None,
        plan_id=None,
        range_end=None,
        range_start=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        if plan_id:
            require("plan_id", plan_id, ID_TYPES)
        if range_end:
            require("range_end", range_end, datetime)
        if range_start:
            require("range_start", range_start, datetime)
        if status is not None:
            assert isinstance(status, list), "status must be a list of strings"
            for s in status or []:
                assert s in [
                    "active",
                    "ended",
                    "not_started",
                ], "Invalid status"

        body = {
            "$type": "list_subscriptions",
        }
        query = {
            "customer_id": customer_id,
        }
        if status is not None:
            query["status"] = status
        if plan_id is not None:
            query["plan_id"] = plan_id
        if range_end is not None:
            query["range_end"] = range_end
        if range_start is not None:
            query["range_start"] = range_start

        ret = self._enqueue(body, query=query, block=True)
        if self.strict:
            return [x.dict() for x in parse_obj_as(list[SubscriptionRecord], ret)]
        else:
            return [SubscriptionRecord.construct(**x).dict() for x in ret]

    def switch_subscription_plan(
        self,
        subscription_id,
        switch_plan_id=None,
        invoicing_behavior=None,
        usage_behavior=None,
        dynamic_fixed_charges_initial_units=None,
    ):
        require("subscription_id", subscription_id, ID_TYPES)
        require("switch_plan_id", switch_plan_id, ID_TYPES)
        for initial_units in dynamic_fixed_charges_initial_units or []:
            require("property_name", initial_units["metric_id"], ID_TYPES)
            require("value", initial_units["units"], numbers.Number)
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

        body = {
            "$type": "switch_subscription_plan",
        }
        if switch_plan_id:
            body["switch_plan_id"] = switch_plan_id
        if invoicing_behavior:
            body["invoicing_behavior"] = invoicing_behavior
        if usage_behavior:
            body["usage_behavior"] = usage_behavior

        ret = self._enqueue(
            body,
            block=True,
            endpoint_url=f"/api/subscriptions/{subscription_id}/switch_plan/",
        )
        if self.strict:
            return parse_obj_as(SubscriptionRecord, ret).dict()
        else:
            return SubscriptionRecord.construct(**ret)

    def update_subscription(
        self,
        *,
        turn_off_auto_renew=None,
        end_date=None,
        subscription_id=None,
        metadata=None,
    ):
        require("subscription_id", subscription_id, ID_TYPES)
        if turn_off_auto_renew is not None:
            require("turn_off_auto_renew", turn_off_auto_renew, bool)
        if end_date:
            require("end_date", end_date, str)
        if metadata:
            require("metadata", metadata, dict)
            for key, value in metadata.items():
                require("metadata key", key, (string_types, numbers.Number))
                require("metadata value", value, (string_types, numbers.Number))

        body = {
            "$type": "update_subscription",
        }
        if turn_off_auto_renew:
            body["turn_off_auto_renew"] = turn_off_auto_renew
        if end_date:
            body["end_date"] = end_date

        ret = self._enqueue(
            body,
            block=True,
            endpoint_url=f"/api/subscriptions/{subscription_id}/update/",
        )

        if self.strict:
            return parse_obj_as(SubscriptionRecord, ret).dict()
        else:
            return SubscriptionRecord.construct(**ret)

    def attach_addon(
        self,
        *,
        subscription_id=None,
        addon_id=None,
        addon_version_id=None,
        quantity=None,
        metadata=None,
    ):
        if addon_id:
            require("addon_id", addon_id, ID_TYPES)
            assert (
                addon_version_id is None
            ), "addon_version_id must be None if addon_id is provided"
        if addon_version_id:
            require("addon_version_id", addon_version_id, ID_TYPES)
            assert (
                addon_id is None
            ), "addon_id must be None if addon_version_id is provided"
        require("subscription_id", subscription_id, ID_TYPES)
        if quantity:
            require("quantity", quantity, int)
        else:
            quantity = 1
        if metadata:
            require("metadata", metadata, dict)
            for key, value in metadata.items():
                require("metadata key", key, (string_types, numbers.Number))
                require("metadata value", value, (string_types, numbers.Number))

        body = {
            "$type": "attach_addon",
            "quantity": quantity,
        }
        if metadata:
            body["metadata"] = metadata
        if addon_id:
            body["addon_id"] = addon_id
        elif addon_version_id:
            body["addon_version_id"] = addon_version_id
        else:
            raise ValueError("Either addon_id or addon_version_id must be provided")

        endpoint_url = f"/api/subscriptions/{subscription_id}/addons/attach/"

        ret = self._enqueue(body, block=True, endpoint_url=endpoint_url)
        if self.strict:
            return parse_obj_as(AddOnSubscriptionRecord, ret).dict()
        else:
            return AddOnSubscriptionRecord.construct(**ret).dict()

    def cancel_addon(
        self,
        subscription_id=None,
        addon_id=None,
        addon_version_id=None,
        flat_fee_behavior=None,
        usage_behavior=None,
        invoicing_behavior=None,
    ):
        require("subscription_id", subscription_id, ID_TYPES)
        if addon_id:
            require("addon_id", addon_id, ID_TYPES)
            assert (
                addon_version_id is None
            ), "addon_version_id must be None if addon_id is provided"
        if addon_version_id:
            require("addon_version_id", addon_version_id, ID_TYPES)
            assert (
                addon_id is None
            ), "addon_id must be None if addon_version_id is provided"

        if flat_fee_behavior is not None:
            assert flat_fee_behavior in [
                "refund",
                "charge_prorated",
                "charge_full",
            ], "flat_fee_behavior must be one of 'refund', 'charge_prorated', or 'charge_full'"
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

        body = {
            "$type": "cancel_addon",
        }
        if flat_fee_behavior:
            body["flat_fee_behavior"] = flat_fee_behavior
        if usage_behavior:
            body["usage_behavior"] = usage_behavior
        if invoicing_behavior:
            body["invoicing_behavior"] = invoicing_behavior

        if addon_id:
            endpoint_url = (
                f"/api/subscriptions/{subscription_id}/addons/{addon_id}/cancel/"
            )
        elif addon_version_id:
            endpoint_url = f"/api/subscriptions/{subscription_id}/addons/{addon_version_id}/cancel/"
        else:
            raise ValueError("Either addon_id or addon_version_id must be provided")

        ret = self._enqueue(body, block=True, endpoint_url=endpoint_url)
        if self.strict:
            return parse_obj_as(AddOnSubscriptionRecord, ret).dict()
        else:
            return AddOnSubscriptionRecord.construct(**ret).dict()

    def list_plans(
        self,
        *,
        duration=None,
        exclude_tags=None,
        include_tags=None,
        include_tags_all=None,
        version_currency_code=None,
        version_custom_type=None,
        version_status=None,
    ):
        if duration is not None:
            assert duration in [
                "monthly",
                "quarterly",
                "yearly",
            ], "duration must be one of 'monthly', 'quarterly', or 'yearly'"
        if exclude_tags is not None:
            require("exclude_tags", exclude_tags, list)
            for tag in exclude_tags:
                require("tag", tag, str)
        if include_tags is not None:
            require("include_tags", include_tags, list)
            for tag in include_tags:
                require("tag", tag, str)
        if include_tags_all is not None:
            require("include_tags_all", include_tags_all, list)
            for tag in include_tags_all:
                require("tag", tag, str)
        if version_currency_code is not None:
            require("version_currency_code", version_currency_code, ID_TYPES)
        if version_custom_type is not None:
            assert version_custom_type in [
                "custom_only",
                "public_only",
                "all",
            ], "version_custom_type must be one of 'custom_only', 'public_only', or 'all'"
        if version_status is not None:
            require("version_status", version_status, list)
            version_status = list(set(version_status))
            for status in version_status:
                assert status in [
                    "active",
                    "ended",
                    "not_started",
                ], "version_status must be one of 'active' or 'ended' or 'not_started'"

        body = {
            "$type": "list_plans",
        }

        query = {}
        if duration is not None:
            query["duration"] = duration
        if exclude_tags is not None:
            query["exclude_tags"] = exclude_tags
        if include_tags is not None:
            query["include_tags"] = include_tags
        if include_tags_all is not None:
            query["include_tags_all"] = include_tags_all
        if version_currency_code is not None:
            query["version_currency_code"] = version_currency_code
        if version_custom_type is not None:
            query["version_custom_type"] = version_custom_type
        if version_status is not None:
            query["version_status"] = version_status

        ret = self._enqueue(body, block=True)
        if self.strict:
            return [x.dict() for x in parse_obj_as(list[Plan], ret)]
        else:
            return [Plan.construct(**x).dict() for x in ret]

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
        if self.strict:
            return parse_obj_as(Plan, ret).dict()
        else:
            return Plan.construct(**ret).dict()

    def get_customer_metric_access(
        self,
        customer_id=None,
        event_name=None,
        metric_id=None,
        subscription_filters=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        if not event_name and not metric_id:
            raise ValueError("Must provide event_name or metric_id")
        if event_name and metric_id:
            raise ValueError("Must provide event_name or metric_id, not both")

        for filter in subscription_filters or []:
            require("property_name", filter["property_name"], ID_TYPES)
            require("value", filter["value"], ID_TYPES)

        body = {
            "$type": "get_customer_metric_access",
        }
        query = {
            "customer_id": customer_id,
            "event_name": event_name,
            "metric_id": metric_id,
            "subscription_filters": subscription_filters,
        }

        ret = self._enqueue(body, query=query, block=True)
        if self.strict:
            return [x.dict() for x in parse_obj_as(list[GetEventAccess], ret)]
        else:
            return [GetEventAccess.construct(**x).dict() for x in ret]

    def check_metric_access(
        self,
        customer_id=None,
        metric_id=None,
        subscription_filters=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        require("metric_id", metric_id, ID_TYPES)
        for filter in subscription_filters or []:
            require("property_name", filter["property_name"], ID_TYPES)
            require("value", filter["value"], ID_TYPES)

        body = {
            "$type": "check_metric_access",
        }
        query = {
            "customer_id": customer_id,
            "metric_id": metric_id,
            "subscription_filters": subscription_filters,
        }

        ret = self._enqueue(body, query=query, block=True)
        if self.strict:
            return parse_obj_as(MetricAccessResponse, ret).dict()
        else:
            return MetricAccessResponse.construct(**ret).dict()

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
        if self.strict:
            return [x.dict() for x in parse_obj_as(list[GetFeatureAccess], ret)]
        else:
            return [GetFeatureAccess.construct(**x).dict() for x in ret]

    def check_feature_access(
        self,
        customer_id=None,
        feature_id=None,
        subscription_filters=None,
    ):
        require("customer_id", customer_id, ID_TYPES)
        require("feature_id", feature_id, ID_TYPES)
        for filter in subscription_filters or []:
            require("property_name", filter["property_name"], ID_TYPES)
            require("value", filter["value"], ID_TYPES)

        body = {
            "$type": "check_feature_access",
        }
        query = {
            "customer_id": customer_id,
            "feature_id": feature_id,
            "subscription_filters": subscription_filters,
        }

        ret = self._enqueue(body, query=query, block=True)
        if self.strict:
            return parse_obj_as(FeatureAccessResponse, ret).dict()
        else:
            return FeatureAccessResponse.construct(**ret).dict()

    def _enqueue(self, body, query=None, block=False, endpoint_url=None):
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
            if endpoint_url is None:
                endpoint_url = self.operations[operation]["url"]
                if "$append_to_url" in body:
                    endpoint_url = endpoint_url + body["$append_to_url"] + "/"
            body.pop("$append_to_url", None)
            if self.host:
                endpoint_host = self.host + endpoint_url
            else:
                endpoint_host = "https://api.uselotus.io" + endpoint_url
            if operation == "update_credit":
                endpoint_host = endpoint_host + "update/"
            elif operation == "void_credit":
                endpoint_host = endpoint_host + "void/"
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
            except Exception:
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
