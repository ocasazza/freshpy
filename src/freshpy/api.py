# -*- coding: utf-8 -*-
"""
:Module:            freshpy.api
:Synopsis:          This module handles interactions with the Freshservice REST API
:Created By:        Jeff Shurtliff
:Last Modified:     Jeff Shurtliff
:Modified Date:     29 Jan 2025
"""

import requests
import time
import random

from . import errors
from .utils import log_utils

# Initialize logging
logger = log_utils.initialize_logging(__name__)


def define_headers():
    """This function defines the headers to use in API calls.

    .. versionadded:: 1.0.0
    """
    headers = {"Content-Type": "application/json"}
    return headers


def define_auth(api_key):
    """This function defines the authentication dictionary to use in API calls.

    .. versionadded:: 1.0.0
    """
    credentials = (api_key, "X")
    return credentials


def get_request_with_retries(
    fresh_object, uri, headers=None, return_json=True, verify_ssl=True
):
    """This function performs a GET request and will retry several times if a failure occurs.

    .. versionchanged:: 2.0.0
       Added error handling for 404 responses and exceptions when converting response to JSON.

    .. versionchanged:: 1.1.0
       Added the ability to disable SSL verification on API calls.

    .. versionadded:: 1.0.0

    :param fresh_object: The instantiated :py:class:`freshpy.core.FreshPy` object.
    :param uri: The URI to query
    :type uri: string
    :param headers: The HTTP headers to utilize in the REST API call
    :type headers: dict, None
    :param return_json: Determines if JSON data should be returned
    :type return_json: bool
    :param verify_ssl: Determines if SSL verification should occur (``True`` by default)
    :type verify_ssl: bool
    :returns: The JSON data from the response or the raw :py:mod:`requests` response.
    :raises: :py:exc:`freshpy.errors.exceptions.APIConnectionError`
    """
    # Define headers if not supplied
    headers = define_headers() if not headers else headers

    # Construct the credentials dictionary
    credentials = define_auth(fresh_object.api_key)

    # Construct the query URL
    query_url = fresh_object.base_url + uri

    # Perform the API call
    retries, response = 0, None
    while retries <= 5:
        try:
            response = requests.get(
                query_url, headers=headers, auth=credentials, verify=verify_ssl
            )
            break
        except Exception as exc_msg:
            _report_failed_attempt(exc_msg, "get", retries)
            retries += 1
    if retries == 6:
        _raise_exception_for_repeated_timeouts()
    if return_json:
        if response.status_code == 429:
            delay = (5**i) + (random.random() * 5)
            print(f"Rate detected. Retrying in {delay:.2f}s")
            time.sleep(delay)

        if response.status_code == 404:
            response = {
                "status": "error",
                "status_code": 404,
                "error_message": "Data not found",
            }
        else:
            try:
                response = response.json()
            except Exception as exc_msg:
                response = {
                    "status": "exception",
                    "status_code": None,
                    "error_message": exc_msg,
                }
    return response


def _report_failed_attempt(_exc_msg, _request_type, _retries):
    """This function reports a failed API call that will be retried.

    .. versionchanged:: 2.0.0
       Replaced a generic py:exc:`Exception` with a py:exc:`RuntimeError` exception.

    .. versionadded:: 1.0.0

    :param _exc_msg: The exception that was raised within a try/except clause
    :param _request_type: The type of API request (e.g. ``post``, ``put`` or ``get``)
    :type _request_type: str
    :param _retries: The attempt number for the API request
    :type _retries: int
    :returns: None
    """
    _exc_name = type(_exc_msg).__name__
    if "connect" not in _exc_name.lower():
        raise RuntimeError(f"{_exc_name}: {_exc_msg}")
    _current_attempt = f"(Attempt {_retries} of 5)"
    _error_msg = (
        f"The {_request_type.upper()} request has failed with the following exception: "
        + f"{_exc_name}: {_exc_msg} {_current_attempt}"
    )
    errors.handlers.eprint(f"{_error_msg}\n{_exc_name}: {_exc_msg}\n")


def _raise_exception_for_repeated_timeouts():
    """This function raises an exception when all API attempts (including) retries resulted in a timeout.

    .. versionadded:: 1.0.0

    :returns: None
    :raises: :py:exc:`freshpy.errors.exceptions.APIConnectionError`
    """
    _failure_msg = (
        "The script was unable to complete successfully after five consecutive API timeouts. "
        + "Please run the script again or contact Freshservice Support for further assistance."
    )
    raise errors.exceptions.APIConnectionError(_failure_msg)
