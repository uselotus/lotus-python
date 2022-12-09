# Lotus Python library example

# Import the library
from datetime import datetime, timezone

import lotus

now = datetime.now(timezone.utc)

# You can find this key on the /settings page in Lotus
lotus.api_key = "rFMXBLi6.AHROCI4h2mlfnRF3rtLhAJM7VbidbWlI"

# Where you host Lotus, with no trailing /.
# You can remove this line if you're using the cloud version
lotus.host = "http://localhost:8000"


# create a customer
# lotus.create_customer(
#     customer_id="customer_id",
#     customer_name="Corporation Inc.",
#     email="my_email@email.com",
# )

# # create a subscription
# lotus.create_subscription(
#     customer_id="customer_id",
#     plan_id="plan_8b40ab11e80f4642900b1af3b0a7ed21",
#     start_date=str(now),
# )


# # Track an event
# lotus.track_event(
#     customer_id="customer_id",
#     event_name="api_call",
#     properties={"region": "US", "mb_used": 150},
# )

# lotus.track_event(
#     customer_id="customer_id",
#     event_name="testnet_transaction",
#     properties={"region": "US", "mb_used": 150},
# )

# # Get a list of customers
# customers = lotus.list_customers()
# print("customers", customers)

# # Get a list of subscriptions
# subscriptions = lotus.list_subscriptions()
# print("subscriptions", subscriptions)

# # Get a subscription for a customer
# subscription = lotus.get_subscription(customer_id="customer_id")
# print("subscription", subscription)

# # Update a subscription
# lotus.update_subscription(
#     customer_id="customer_id",
#     plan_id="plan_8b40ab11e80f4642900b1af3b0a7ed21",
#     turn_off_auto_renew=True,
# )

# # Get a customer's metric access
# metric_access = lotus.get_customer_metric_access(
#     customer_id="customer_id", event_name="testnet_transaction"
# )
# print("metric_access", metric_access)

# # Get a customer's feature access
# feature_access = lotus.get_customer_feature_access(
#     customer_id="customer_id", feature_name="feature_name"
# )
# print("feature_access", feature_access)

# # Get a customer
# customer = lotus.get_customer(customer_id="customer_id")
# print("customer", customer)

# # Cancel a subscription
# lotus.cancel_subscription(customer_id="customer_id")

# # get a list of all plans
# plans = lotus.list_plans()
# print("plans", plans)
