from lotus.client import Client
from lotus.version import VERSION

__version__ = VERSION

"""Settings."""
api_key = None
host = None
on_error = None
debug = False
send = True
sync_mode = False

default_client = None


def track_event(*args, **kwargs):
    _proxy("track_event", *args, **kwargs)


def create_customer(*args, **kwargs):
    _proxy("create_customer", *args, **kwargs)


def create_subscription(*args, **kwargs):
    _proxy("create_subscription", *args, **kwargs)


def cancel_subscription(*args, **kwargs):
    _proxy("cancel_subscription", *args, **kwargs)


def get_customer_access(*args, **kwargs):
    return _proxy("get_customer_access", *args, **kwargs)


def get_customers(*args, **kwargs):
    return _proxy("get_customers", *args, **kwargs)


def get_current_usage(*args, **kwargs):
    return _proxy("get_current_usage", *args, **kwargs)


def get_plans(*args, **kwargs):
    return _proxy("get_plans", *args, **kwargs)


def get_subscriptions(*args, **kwargs):
    return _proxy("get_subscriptions", *args, **kwargs)


def flush():
    """Tell the client to flush."""
    _proxy("flush")


def join():
    """Block program until the client clears the queue"""
    _proxy("join")


def shutdown():
    """Flush all messages and cleanly shutdown the client"""
    _proxy("flush")
    _proxy("join")


def _proxy(method, *args, **kwargs):
    """Create an analytics client if one doesn't exist and send to it."""
    global default_client
    if not default_client:
        default_client = Client(
            api_key,
            host=host,
            debug=debug,
            on_error=on_error,
            send=send,
            sync_mode=sync_mode,
        )

    fn = getattr(default_client, method)
    ret = fn(*args, **kwargs)
    return ret
