import os
import sys

from lotus.version import VERSION

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Don't import analytics-python module here, since deps may not be installed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lotus"))


long_description = """
Lotus is the quickest way to track usage and optimize pricing for your SaaS business. lotus-python is the python package.
"""

install_requires = [
    "requests>=2.7,<3.0",
    "six>=1.5",
    "monotonic>=1.5",
    "backoff>=1.6.0",
    "python-dateutil>2.1",
    "pydantic[email]>=1.10.0",
]

tests_require = ["mock>=2.0.0", "python-dotenv>=0.21.0"]

setup(
    name="lotus-python",
    version=VERSION,
    url="https://github.com/uselotus/lotus-python",
    author="Lotus",
    author_email="founders@lotus.io",
    maintainer="Lotus",
    maintainer_email="founders@lotus.io",
    test_suite="lotus.tests.all",
    packages=["lotus", "lotus.tests"],
    license="MIT License",
    install_requires=install_requires,
    tests_require=tests_require,
    description="Integrate Lotus into any python application.",
    long_description=long_description,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
