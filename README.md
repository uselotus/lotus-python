# Lotus Python Library

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

## Making calls

Please refer to the [Lotus documentation](https://docs.uselotus.io/docs/intro) for more information on how to use the library.

## Questions?

### [Join our Slack community.](https://lotus-community.slack.com)

## Thank you

This library is largely based on the `posthog-python` package.