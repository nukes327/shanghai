#!/usr/bin/env python3
"""What's actually run to use the bot

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
from time import sleep

import shanghai.shanghai as shanghai


def init_shanghai():
    """Create an empty shanghai config with necessary sections and keys"""
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

def init_apis():
    """Create an empty apis config with necessary sections and keys"""
    config = configparser.ConfigParser()
    config['pixiv'] = {
        'username': '',
        'password': ''}
    with open('config/apis.ini', 'w+') as conffile:
        config.write(conffile)

def init_logging():
    """Generate a standard logging config file"""
    config = configparser.ConfigParser()
    config['loggers'] = {'keys': 'root'}
    config['handlers'] = {'keys': 'systemFileHandler, systemStreamHandler'}
    config['formatters'] = {'keys': 'systemFormatter'}
    config['logger_root'] = {
        'level': 'INFO',
        'handlers': 'systemFileHandler, systemStreamHandler'}
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
    config['formatter_systemFormatter'] = {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'datefmt': ''}
    with open('config/logging.ini', 'w+') as conffile:
        config.write(conffile)

def main():
    """Main loop/code for initializing and running the bot

    Notes:
        While this does check for presence of the necessary inis,
        it does not check for syntactical validity of any of the
        configs other than the logging config, as it is actually
        loaded right away
        This may be changed later to load the config parsers now,
        and init the bot with those rather than the bot loading the
        configs itself later

    """
    if not os.path.isfile('config/logging.ini'):
        print('No logging file found, making a new one', file=sys.stderr)
        init_logging()
    try:
        logging.config.fileConfig('config/logging.ini')
    except KeyError as inst:
        print(f'There was an error reading the logging config: {inst}',
              'Renaming the old one and generating a new one',
              sep='\n', file=sys.stderr)
        os.replace('config/logging.ini', 'config/logging.ini.old')
        init_logging()
        logging.config.fileConfig('config/logging.ini')
    logger = logging.getLogger(__name__)
    logger.info('Logging configuration loaded')
    if not os.path.isfile('config/apis.ini'):
        logger.warning('Apis config file missing, generating an emtpy one and continuing')
        init_apis()
    if not os.path.isfile('config/shanghai.ini'):
        logger.error('Main shanghai config file missing, generating an empty one and stopping')
        init_shanghai()
    else:
        logger.info('Necessary configuration files are present, continuing')
        doll = shanghai.Bot()

if __name__ == '__main__':
    main()
