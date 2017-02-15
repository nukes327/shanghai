#!/usr/bin/env python3
"""This is the main module for Shanghai

Shanghai is an IRC chat bot that will respond to simple commands, and
scan incoming links to post information on the content to the channel.

TODO:
    Actually write the code
    Move Exceptions to own file
    Better parser?

"""

import configparser
import getpass
import logging
from logging.handlers import RotatingFileHandler
import re
import socket
import ssl
import time
import json

import fuckit

# from linkscanning import LinkScanner
from . import exceptions


_MSPLIT = re.compile(r"""
  :
  (?P<user>[^!]*)
  !\S*?\s*?
  PRIVMSG
  \s*?
  (?P<chan>\S*)
  \s*?
  :(?P<msg>[^\r\n]*)
""", re.VERBOSE | re.IGNORECASE)

_LINKS = re.compile(r"\bhttps?://[^. ]+\.[^. \t\n\r\f\v][^ \n\r]+")


class Bot:
    Channel = str
    Command = str
    Filename = str
    Flag = bool
    Message = str
    Time = time.struct_time
    User = str

    def __init__(self,
                 config: Filename = "shanghai.ini",
                 chancoms: Filename = "commands.ini"):
        self.config = configparser.ConfigParser()
        # Load config here
        self.users = None
        self.chancoms = configparser.ConfigParser()
        # Load channel commands here
        self.chanfile = chancoms
        self.syscoms = None # Methods dictionary here
        self.match = None
        self.message = None
        self.irc = None
        self.logger = self.logging_setup()
        self.logger.info('This is still a test')
        self.scanner = None

    def logging_setup(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler('shanghai.log', 'a', 10 * 1024 * 1024, 10)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

if __name__ == '__main__':
    shanghai = Bot()
