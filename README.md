# Lotus Python

Official Lotus Python library to capture and send events to any Lotus instance (self-hosted or cloud).

This library uses an internal queue to make calls non-blocking and fast. It also batches requests and flushes asynchronously, making it perfect to use in any part of your web app or other server side application that needs performance.

## Installation 

```bash
pip install lotus-python
```

In your app, import the lotus library and set your api key **before** making any calls.

```python
import lotus

lotus.api_key = 'YOUR API KEY'
```

You can find your key in the /settings page in Lotus.

To debug, you can set debug mode.
```python
lotus.debug = True
```

## Making calls

### Track Event

Track event is the most common call you'll make. It's used to capture any event that happens in your app that you want to bill over eventually.
You can track absolutely anything, and with the extensible and customizable properties field, you can add as much information as you want.

A `track_event` call requires
 - `event_name` should correspond to what the event is and match what you define in your metrics.
 - `customer_id`  the id you defined in your backend for the corresponding customer and the same id that you passed into Lotus when creating the customer

Optionally you can submit
- `properties`, which can be a dict with any information you'd like to add.  In your metrics you can define properties to filer or aggregate over.
 - `idempotency_id` is a unique identifier for the specific event being passed in. Passing in a unique id allows Lotus to make sure no double counting occurs. If you don't pass in an idempotency_id, we will generate one for you using UUID4.

For example:
```python
lotus.track_event(customer_id='customer123', event_name='api_call', properties={'region': 'US', 'mb_used': 150})
```

### Create Customer
To let Lotus know that you have a new customer, simply use the create customer method. 

A `create_customer` call requires
- `customer_id` which uniquely identifies your customer in your backend. This is the same id you'll pass into `track_event` calls to identify the customer, in addition to other calls, so make sure it's available to you.
- `name` a name for your customer

Optionally you can submit
- `currency` what currency your customer is billed in. If you don't pass in a currency, we will default to USD.

For example:
```python
lotus.create_customer(
    customer_id='customer_id',
    name='Corporation Inc.'
)
```

The most obvious place to make this call is whenever a user signs up, or when they update their information.

### Create Subscription

A subscription associates one of your custoemrs with one of your billing plans.

A `create_subscription` call requires
- `customer_id` which uniquely identifies your customer in your backend. This is the same id you'll pass into `track_event` calls to identify the customer, in addition to other calls, so make sure it's available to you.
- `billing_plan_id` which uniquely identifies your billing plan in your backend. You can find the billing plan id in the billing plan page in Lotus.
- `start_date` the date the subscription starts. This should be a datetime string in UTC.

For example:
```python
lotus.create_subscription(
  customer_id='customer_1', 
  billing_plan_id='billing_plan_5',
  start_date='2020-01-01T00:00:00Z'
)
```

### Cancel Subscription

Cancels a subscription. You can optionally decide whether to bill for the usage so far that period or not.

A `cancel_subscription` call requires
- `subscription_uid` the unique ID of the subscription you want to cancel. You can find the subscription uid in the subscription page in Lotus.
- `bill_now` whether to bill for the usage so far that period or not. If you don't pass in a value, we will default to `True`.

For example:
```python
lotus.cancel_subscription(
  subscription_uid='subscription_4', 
  bill_now='True')
```


### Get Customer Access

Checks whether a customer has access to a specific feature or enough usage in their plan to register an event. This is useful if you want to gate access to certain features in your app based on usage.

A `get_customer_access` call requires
- `customer_id` the id you defined in your backend for the corresponding customer and the same id that you passed into Lotus when creating the customer

AND EITHER
- `feature_name` name of the feature you want to check access for.

OR

- `event_name` name of the event you want to check access for. In the backend we'll check whether any of the plan components associated with the event have surpassed their limit.

For example:
```python
lotus.get_customer_access(
  customer_id='customer123', 
  event_name='api_call'
)
```

## Thank you

This library is largely based on the `posthog-python` package.