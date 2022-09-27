import pytest


@pytest.fixture
def track_event_example():
    return {
        "customer_id": "distinct_id",
        "event_name": "python test event",
        "properties": {"property": "value"},
        "idempotency_id": "messageId",
        "time_created": "2020-09-03T00:00:00+00:00",
    }


@pytest.fixture
def create_customer_example():
    return {
        "customer_id": "distinct_id",
        "customer_name": "test customer",
        "properties": {"property": "value"},
    }


@pytest.fixture
def create_subscription_example():
    return {
        "customer_id": "customer_id",
        "billing_plan_id": "billing_plan_id",
        "start_date": "2020-09-03",
    }


@pytest.fixture
def cancel_subscription_example():
    return {
        "subscription_uid": "subscription_uid",
        "bill_now": "True",
    }
