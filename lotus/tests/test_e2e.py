import datetime
import os
import uuid

from dateutil import relativedelta
from dotenv import load_dotenv

import lotus


class TestEndtoEnd:
    def test_e2e(self):
        load_dotenv()  # take environment variables from .env.
        API_KEY = os.environ.get("LOTUS_API_KEY")
        host = os.environ.get("LOTUS_HOST", "https://api.uselotus.io")
        lotus.api_key = API_KEY
        lotus.strict = True
        lotus.host = host

        now = datetime.datetime.now(datetime.timezone.utc)
        now_minus_day = now - relativedelta.relativedelta(days=1)
        id = uuid.uuid4().hex

        plan_id = os.environ.get("PLAN_ID", "plan_aead7e8eb07249c2b2610e936d24a356")
        addon_id = os.environ.get("ADDON_ID", "addon_4f236c4f262443179a0d99f15405e7de")
        metric_id = os.environ.get(
            "METRIC_ID", "metric_a25d887196464a1389fd65194f9e1d7f"
        )
        unused_metric_id = os.environ.get(
            "UNUSED_METRIC_ID", "metric_5da8be769cdf4e3fa8233a22fb920733"
        )
        feature_id = os.environ.get(
            "FEATURE_ID", "feature_6b037a7bbce44ee98a65a04e97e2f5dd"
        )
        ## CREATE CUSTOMER
        response = lotus.create_customer(
            customer_id=id,
            customer_name="Test Customer",
            email=f"{id}@email.com",
        )
        assert response["customer_id"] == id

        ## LIST + CREATE CREDIT
        credits = lotus.list_credits(
            customer_id=id,
        )
        assert len(credits) == 0
        lotus.create_credit(
            customer_id=id,
            amount=100,
            currency_code="USD",
            expires_at=now + relativedelta.relativedelta(days=7),
            description="Test Credit",
        )
        credits = lotus.list_credits(
            customer_id=id,
            effective_after=now_minus_day,
            effective_before=now + relativedelta.relativedelta(days=1),
            expires_after=now_minus_day,
            expires_before=now + relativedelta.relativedelta(days=10),
            issued_after=now_minus_day,
            issued_before=now + relativedelta.relativedelta(days=1),
            status=["active"],
        )
        assert len(credits) == 1
        credit = credits[0]

        ## UPDATE + VOID CREDIT
        lotus.update_credit(
            credit_id=credit["credit_id"],
            expires_at=now + relativedelta.relativedelta(days=5),
            description="Updated Credit",
        )
        lotus.void_credit(
            credit_id=credit["credit_id"],
        )
        credits = lotus.list_credits(
            customer_id=id,
        )
        assert len(credits) == 1
        credit = credits[0]
        assert len(credit["drawdowns"]) > 0

        ## CREATE SUBSCRIPTION
        response = lotus.create_subscription(
            customer_id=id,
            plan_id=plan_id,
            start_date=str(now_minus_day),
            subscription_filters=[{"property_name": "region", "value": "US"}],
        )
        assert response["start_date"] == now_minus_day
        assert response["customer"]["customer_id"] == id
        assert response["billing_plan"]["plan_id"] == plan_id

        ## ATTACH ADDON
        response = lotus.attach_addon(
            attach_to_customer_id=id,
            addon_id=addon_id,
            attach_to_subscription_filters=[{"property_name": "region", "value": "US"}],
            attach_to_plan_id=plan_id,
            quantity=10,
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        assert response["addon"]["addon_id"] == addon_id
        assert now_minus_day < response["start_date"] < now
        assert response["parent"]["plan_detail"]["plan_id"] == plan_id
        assert response["fully_billed"] is True
        assert response["auto_renew"] is False

        ## TRIACK EVENT
        lotus.track_event(
            customer_id=id,
            event_name="test_event",
            properties={"region": "US", "mb_used": 150},
        )
        lotus.track_event(
            customer_id=id,
            event_name="test_event",
            properties={"region": "EU", "mb_used": 150},
        )
        lotus.track_event(
            customer_id=id,
            event_name="test_event",
            properties={"region": "US", "mb_used": 150},
        )

        ## LIST CUSTOMER + SUBSCRIPTIONS
        customers = lotus.list_customers()
        assert len(customers) > 0
        cust_subs = lotus.list_subscriptions(customer_id=id)
        assert len(cust_subs) > 0
        assert cust_subs[0]["customer"]["customer_id"] == id
        assert cust_subs[0]["subscription_filters"][0]["property_name"] == "region"
        assert cust_subs[0]["subscription_filters"][0]["value"] == "US"
        assert cust_subs[0]["auto_renew"] is True

        ## UPDATE SUBSCRIPTION
        sub = lotus.update_subscription(
            customer_id=id,
            plan_id=plan_id,
            turn_off_auto_renew=True,
        )
        assert len(sub) == 1
        assert sub[0]["auto_renew"] is False

        ## CANCEL ADDON
        response = lotus.cancel_addon(
            attached_customer_id=id,
            addon_id=addon_id,
            attached_plan_id=plan_id,
            flat_fee_behavior="charge_prorated",
        )[0]
        now = datetime.datetime.now(datetime.timezone.utc)
        assert response["end_date"] < now
        assert response["fully_billed"] is True

        ## METRIC ACCESS
        access = lotus.check_metric_access(
            customer_id=id,
            metric_id=metric_id,
            subscription_filters=[{"property_name": "region", "value": "US"}],
        )
        assert access["metric"]["event_name"] == "test_event"
        assert access["access_per_subscription"][0]["metric_usage"] >= 0
        assert access["access_per_subscription"][0]["metric_total_limit"] is None
        access = lotus.check_metric_access(  # bogus metric id
            customer_id=id,
            metric_id=unused_metric_id,
            subscription_filters=[{"property_name": "region", "value": "US"}],
        )
        assert access["access_per_subscription"][0]["metric_usage"] == 0
        assert access["access_per_subscription"][0]["metric_total_limit"] == 0

        ## FEATURE ACCESS
        feature_access = lotus.check_feature_access(
            customer_id=id, feature_id=feature_id
        )
        assert feature_access["feature"]["feature_name"] == "test_feature"
        assert feature_access["access"] is True
        lotus.get_customer(customer_id=id)

        ## CANCEL SUBSCRIPTION
        canceled_sub = lotus.cancel_subscription(
            customer_id=id, invoicing_behavior="invoice_now"
        )
        assert len(canceled_sub) == 1
        canceled_sub = canceled_sub[0]
        now = datetime.datetime.now(datetime.timezone.utc)
        assert canceled_sub["end_date"] <= now
        assert canceled_sub["fully_billed"] is True

        ## LIST PLANS
        plans = lotus.list_plans()
        assert len(plans) > 0
