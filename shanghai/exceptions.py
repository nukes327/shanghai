#!/usr/bin/env python3
"""Contains the exceptions for the Shanghai bot"""

class ShanghaiError(Exception):
    """Base Error Class"""
    def __init__(self, *,
                 error: str = None,
                 message: str = None):
        if message is None:
            message = f'Shanghai encountered an error - {error}'
        super(ShanghaiError, self).__init__(message)
        self.error = error

class ClearanceError(ShanghaiError):
    """Someone tried to run something over their clearance"""
    def __init__(self, *,
                 user: str = None,
                 func: str = None):
        super(ClearanceError, self).__init__(error='ClearanceError - {user}: {func}')
        self.user = user
        self.func = func

    def __str__(self):
        return repr(' - '.join([self.user, self.func]))

class LinkScanError(ShanghaiError):
    """Base Link Scanning Error Class"""
    def __init__(self, *,
                 error: str = None):
        super(LinkScanError, self).__init__(error=f'LinkScanError - {error}')
        self.error = error

class TitleError(LinkScanError):
    """Error in fetching title"""
    def __init__(self, *,
                 link: str = None):
        super(TitleError, self).__init__(error=f'Failed to get title for {link}')
        self.link = link

class RequestError(LinkScanError):
    """Error in GET request"""
    def __init__(self, *,
                 link: str = None):
        super(RequestError, self).__init__(error=f'Get request failed for {link}')
        self.link = link
