#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Contains methods that reference APIs used by bot."""

import configparser
from functools import lru_cache
import logging

import pixivpy3  # type: ignore

from .exceptions import APIError


@lru_cache(maxsize=32)
def pixiv_tags(illust_id: int, conf: configparser.SectionProxy) -> str:
    """Fetch and return illustration tags from pixiv.

    Args:
        illust_id: The ID of the illustration
        conf: A configparser section containing user/password info

    Returns:
        A string containing tags for the illustration with given ID

    """
    logger = logging.getLogger(__name__)
    logger.info(f'Beginning API call to get info on ID {illust_id}')
    api = pixivpy3.AppPixivAPI()
    logger.debug(f'Using username: {conf["username"]}, password: {conf["password"]}')
    api.login(conf['username'], conf['password'])
    try:
        json_result = api.illust_detail(illust_id, req_auth=True)
    except pixivpy3.PixivError as inst:
        logger.error(inst)
        raise APIError(error=inst)
    illust = json_result.illust
    return ' '.join(['[tags]', ', '.join([tag.name for tag in illust.tags])])
