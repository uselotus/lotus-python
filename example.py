# Lotus Python library example

# Import the library
import lotus

# You can find this key on the /settings page in Lotus
lotus.api_key = "<your key>"

# Where you host Lotus, with no trailing /.
# You can remove this line if you're using the cloud version
lotus.host = "http://127.0.0.1:8000"

# Track an event
lotus.track_event(
    customer_id="customer123",
    event_name="api_call",
    properties={"region": "US", "mb_used": 150},
)

# create a customer
lotus.create_customer(customer_id="customer_id", name="Corporation Inc.")

# create a subscription
lotus.create_subscription(
    customer_id="customer_1",
    billing_plan_id="billing_plan_5",
    start_date="2020-01-01T00:00:00Z",
)
