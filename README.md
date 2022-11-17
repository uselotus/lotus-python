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
1. TrackEvent
2. Get All Customers
3. Get Customer Details
4. Create Customer
5. Create Subscription
6. Cancel Subscription
7. Change Subscription
8. Get All Subscriptions
9. Get Subscription Details
10. Get All Plans
11. Get Customer Access
```

## Making calls

Please refer to the [Lotus documentation](https://docs.uselotus.io/docs/api/) for more information on how to use the library.

## Questions?

### [Join our Slack community.](https://lotus-community.slack.com)

## Thank you

This library is largely based on the `posthog-python` package.
