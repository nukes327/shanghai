#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Contains the exceptions for the Shanghai bot."""

from typing import Optional


class ShanghaiError(Exception):
    """Base shanghai exception class."""

    def __init__(self, *, error: str, message: Optional[str] = None):
        """Initialize ShanghaiError class.

        Args:
            error:   description of error that occurred
            message: final visible error message

        """
        if message is None:
            message = f"Shanghai encountered an error - {error}"
        super(ShanghaiError, self).__init__(message)
        self.error = error


class ClearanceError(ShanghaiError):
    """Raise for clearance violations."""

    def __init__(self, *, user: str, func: str):
        """Initialize ClearanceError class.

        Args:
            user: user that attempted clearance violation
            func: command that user attempted to execute

        """
        super(ClearanceError, self).__init__(error=f"ClearanceError - User: {user}, Command: {func}")
        self.user = user
        self.func = func


class LinkScanError(ShanghaiError):
    """Base link scanning exception class."""

    def __init__(self, *, error: str):
        """Initialize LinkScanError class.

        Args:
            error: description of error that occurred

        """
        super(LinkScanError, self).__init__(error=f"LinkScanError - {error}")
        self.error = error


class TitleError(LinkScanError):
    """Raise for exception in fetching page title."""

    def __init__(self, *, link: Optional[str] = None, error: str):
        """Initialize TitleError class.

        Args:
            link:  page that title could not be fetched from
            error: reason title fetch failed

        """
        super(TitleError, self).__init__(error=f"Failed to get title for {link}: {error}")
        self.link = link
        self.error = error


class RequestError(LinkScanError):
    """Raise for exception in GET request."""

    def __init__(self, *, link: Optional[str] = None, error: str):
        """Initialize RequestError class.

        Args:
            link:  page that failed GET request
            error: reason GET failed

        """
        super(RequestError, self).__init__(error=f"Get request failed for {link}: {error}")
        self.link = link
        self.error = error


class APIError(LinkScanError):
    """Raise for exception with an API."""

    def __init__(self, *, error: str):
        """Initialize APIError class.

        Args:
            error: exception that occurred with API

        """
        super(APIError, self).__init__(error=f"Problem with an API: {error}")
        self.error = error


class ShangSockError(ShanghaiError):
    """Raise for exception with socket."""

    def __init__(self, *, error: str):
        """Initialize ShangSockError class.

        Args:
            error: exception that occurred with socket

        """
        super(ShangSockError, self).__init__(error=f"ShangSockError - {error}")
        self.error = error
