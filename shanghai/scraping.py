#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Contains methods related to scraping webpages."""

import configparser
import logging
import re

from bs4 import BeautifulSoup
import requests
import requests.exceptions

from .apis import pixiv_tags
from .exceptions import (
    TitleError, RequestError, APIError)


_PIXIV = re.compile(r'pixiv.*illust_id(\d+)')


def scrape(link: str, apis: configparser.ConfigParser) -> str:
    """Check a link and return pertinent info.

    Args:
        link: The link to be scanned
        apis: A config parser with relevant information for
              api usage (usernames and passwords mostly)

    Returns:
        A string with info relating to the link for the bot to use

    Notes:
        The apis arg is like to change when I've figured out
        a good way to pass a dictionary rather than the whole
        honkin parser

    """
    logger = logging.getLogger(__name__)
    message = None
    logger.info(f'Beginning handling for {link}')
    try:
        response = get_response(link)
    except RequestError as inst:
        logger.error('There was an error making the request', exc_info=inst)
        message = inst
    else:
        logger.info(f'Request successful for {link}')
        message = []
        if response.headers['content-type'] == 'text/html':
            try:
                message.append(fetch_title(response))
            except TitleError:
                message.append('No title found for the linked page')
            try:
                message.append(
                    pixiv_tags(_PIXIV.search(link).group(1), apis['pixiv']))
            except APIError:
                message.append('Failed to fetch illustration tags')
            except AttributeError:
                pass
        else:
            message.append(fetch_info(response))
        message = '\n'.join(message)
    return message


def get_response(link: str) -> requests.Response:
    """Manage the HTTP GET request for a link.

    Args:
        link: The URL for the request

    Returns:
        The requests Response object

    """
    logger = logging.getLogger(__name__)
    logger.info(f'Sending GET request to {link}')
    try:
        response = requests.get(link, timeout=1, stream=True,
                                headers={"Accept-Encoding": "deflate"})
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as inst:
        raise RequestError(link=link, error=inst)
    else:
        logger.info(f'Request completed, checking status')
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as inst:
            raise RequestError(link=link, error=inst)
    logger.info(f'No errors in request, returning')
    return response


def fetch_title(response: requests.Response) -> str:
    """Get the title from HTML page source.

    Args:
        response: The Response object that includes the HTML source

    Returns:
        A string containing the page title

    """
    logger = logging.getLogger(__name__)
    logger.info(f'Attempting to find page title for {response.url}')
    try:
        title = BeautifulSoup(response.text, 'html.parser').title.string.strip().replace('\n', '')
    except AttributeError:
        logger.info(f'No page title present for {response.url}')
        raise TitleError(link=response.url, error='No title present')
    logger.info(f'Page title found for {response.url}: {title}')
    return ' '.join(['[title]', title])


def fetch_info(response: requests.Response) -> str:
    """Get the size and type of the linked content.

    Args:
        response: The Response object that includes the necessary headers

    Returns:
        A string containing content type and size

    """
    logger = logging.getLogger(__name__)
    logger.info(f'Beginning to fetch info about {response.url}')
    message = [f'[{response.headers["content-type"]}]']
    try:
        logger.info('Getting size and converting it to something readable')
        message.append(size_convert(int(response.headers['content-length'])))
    except KeyError:
        logger.info('No content length header, size unknown')
        message.append('?B')
    return ' '.join(message)


def size_convert(size: int = 0) -> str:
    """Convert a size in bytes to human readable format.

    Args:
        size: The length of a file in bytes

    Returns:
        A human readable string for judging size of a file

    Notes:
        Uses the IEC prefix, not SI

    """
    size_name = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
    i = 0
    while size >= 1024:
        size /= 1024
        i += 1
    try:
        return str(round(size, 2)) + size_name[i]
    except IndexError:
        return str(round(size, 2)) + ' x ' + '1024^{i} bytes'
