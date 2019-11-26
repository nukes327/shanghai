#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Main file used to run bot.

Notes:
    This script generates missing config files as necessary
    If this detects an invalid logging config it will append a .old to the old
    config, *replacing* any previous old config

"""

import configparser
import logging
import logging.config
import os
import sys

import shanghai.shanghai as shanghai
from shanghai.exceptions import ShanghaiError


def init_logging() -> None:
    """Check and recovery process for logging preparation."""
    while True:
        try:
            logging.config.fileConfig('config/logging.ini')
        except KeyError as inst:
            logging_config_recovery(inst)
        except FileNotFoundError as inst:
            logging_logfile_recovery(inst)
        except PermissionError as inst:
            raise ShanghaiError(error=f'No access to default log file - {inst}')
        except Exception as inst:
            raise ShanghaiError(error=f'Unexpected exception, contact maintainer - {inst}')
        else:
            break


def logging_config_recovery(issue: KeyError) -> None:
    """Recovery checks and actions for accessing the logging configuration."""
    print(f'There was an error reading the logging config: {issue}',
          'Proceding with recovery',
          sep='\n', file=sys.stderr)
    try:
        os.replace('config/logging.ini', 'config/logging.ini.old')
    except FileNotFoundError:
        try:
            os.mkdir('config')
        except FileExistsError:
            pass
        else:
            print('Config directory was absent, created and continuing',
                  file=sys.stderr)
    else:
        print('Renamed old file to logging.ini.old',
              file=sys.stderr)
    finally:
        print('Creating new logging.ini',
              file=sys.stderr)
        create_logging_config()


def logging_logfile_recovery(issue: FileNotFoundError) -> None:
    """Recovery checks and actions for accessing the logfile."""
    print(f'There was an error locating the log file or directory: {issue}',
          file=sys.stderr)
    try:
        os.mkdir('logs')
    except FileExistsError as inst:
        raise ShanghaiError(error=f'Unexpected exception, contact maintainer - {inst}')
    else:
        print('Log directory was absent, created and continuing',
              file=sys.stderr)


def create_logging_config() -> None:
    """Generate a standard logging config file."""
    config = configparser.ConfigParser()
    config['loggers'] = {'keys': 'root'}
    config['handlers'] = {'keys': 'systemFileHandler, systemStreamHandler, errorFileHandler'}
    config['formatters'] = {'keys': 'systemFormatter'}
    config['logger_root'] = {
        'level': 'INFO',
        'handlers': 'systemFileHandler, systemStreamHandler, errorFileHandler'}
    config['handler_systemFileHandler'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'level': 'INFO',
        'formatter': 'systemFormatter',
        'args': "('logs/shanghai.log', 'a', 10 * 1024 * 1024, 10,)"}
    config['handler_systemStreamHandler'] = {
        'class': 'StreamHandler',
        'level': 'WARNING',
        'formatter': 'systemFormatter',
        'args': '(sys.stderr,)'}
    config['handler_errorFileHandler'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'level': 'WARNING',
        'formatter': 'systemFormatter',
        'args': "('logs/shanghai_errors.log', 'a', 10 * 1024 * 1024, 10,)"}
    config['formatter_systemFormatter'] = {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'datefmt': ''}
    with open('config/logging.ini', 'w+') as conffile:
        config.write(conffile)


def create_api_config() -> None:
    """Create an empty apis config with necessary sections and keys."""
    config = configparser.ConfigParser()
    config['pixiv'] = {
        'username': '',
        'password': ''}
    with open('config/apis.ini', 'w+') as conffile:
        config.write(conffile)


def create_shanghai_config() -> None:
    """Create an empty shanghai config with necessary sections and keys."""
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'owner': '',
        'nick': '',
        'realname': '',
        'password': '',
        'prefix': ',',
        'server': '',
        'port': '6697',
        'ssl': 'yes'}
    with open('config/shanghai.ini', 'w+') as conffile:
        config.write(conffile)


def main() -> None:
    """Initialize and run bot.

    Notes:
        While this does check for presence of the necessary inis,
        it does not check for syntactical validity of any of the
        configs other than the logging config, as it is actually
        loaded right away
        This may be changed later to load the config parsers now,
        and init the bot with those rather than the bot loading the
        configs itself later

    """
    init_logging()
    logger = logging.getLogger(__name__)
    logger.info('Logging configuration loaded')
    if not os.path.isfile('config/apis.ini'):
        logger.warning('Apis config file missing, generating an empty one and continuing')
        create_api_config()
    if not os.path.isfile('config/shanghai.ini'):
        logger.error('Main shanghai config file missing, generating an empty one and stopping')
        create_shanghai_config()
    else:
        logger.info('Necessary configuration files are present, continuing')
        shanghai.Bot()  # Verifying bot construction / initialization


if __name__ == '__main__':
    main()
