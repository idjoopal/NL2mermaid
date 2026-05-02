"""
Custom exceptions for web search module.
"""


class SearchToolException(Exception):
    """Base exception for search tool."""


class InvalidParameterError(SearchToolException):
    """Raised when an invalid parameter is provided."""


class InvalidDateFormatError(InvalidParameterError):
    """Raised when a date format is invalid."""


class APIKeyMissingError(SearchToolException):
    """Raised when an API key is missing."""
