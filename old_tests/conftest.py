import uuid

import pytest


@pytest.fixture
def track_event_example():
    def do_track_event_example():
        return {
            "customer_id": "customer_id",
            "event_name": "python test event",
            "properties": {"property": "value"},
            "idempotency_id": str(uuid.uuid4()),
            "time_created": "2020-09-03T00:00:00+00:00",
        }

    return do_track_event_example


@pytest.fixture
def create_customer_example():
    return {
        "customer_id": "customer_id",
        "customer_name": "test customer",
        "properties": {"property": "value"},
    }


@pytest.fixture
def create_subscription_example():
    return {
        "customer_id": "customer_id",
        "billing_plan_id": "my_id",
        "start_date": "2020-09-03",
        "subscription_id": "subscription_id",
    }


@pytest.fixture
def cancel_subscription_example():
    return {
        "subscription_id": "subscription_id",
        "bill_now": "True",
    }


@pytest.fixture
def get_customer_access_example():
    return {
        "customer_id": "customer_id",
        "event_name": "event_name",
    }
