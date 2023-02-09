# Lotus Python Library

[![MIT License](https://img.shields.io/badge/License-MIT-red.svg?style=flat)](https://opensource.org/licenses/MIT)
Official Lotus Python library to capture and send events to any Lotus instance (self-hosted or cloud).

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


## Currently Supported Methods
```
1. Tracking:
    - Track Event
2. Customers
    - List Customers
    - Get Customer
    - Create Customer
3. Credits
    - List Credits
    - Create Credit
    - Update Credit
    - Void Credit
4. Subscriptions
    - List Subscriptions
    - Create Subscription
    - Cancel Subscription
    - Update Subscription
5. Access Management
    - Get Feature Access
    - Get Metric Access
6. Plans
    - List Plans
    - Get Plan
7. Add-ons
    - Attach Add-on
    - Update Add-on
    - Cancel Add-on 
```

## Making calls

Please refer to the [Lotus documentation](https://docs.uselotus.io/docs/api/) for more information on how to use the library.

## Questions?

### [Join our Slack community.](https://lotus-community.slack.com)

## Thank you

This library is largely based on the `posthog-python` package.
