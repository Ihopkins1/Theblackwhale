"""Utility Python module for non-browser helpers.

The cart behavior for test.html lives in function.js.
"""


def cart_script_file() -> str:
    """Return the JavaScript file name used by test.html."""
    return "function.js"
