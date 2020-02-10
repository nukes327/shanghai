#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Main module for Shanghai.

Shanghai is an IRC chat bot that will respond to simple commands, and
scan incoming links to post information on the content to the channel.

TODO:
    Actually write the code
    Move Exceptions to own file
    Better parser?

"""

import configparser
import logging
import re

# import fuckit

from . import connection
from . import exceptions
from . import scraping


_MSPLIT = re.compile(
    r"""
  :
  (?P<user>[^!]*)
  !\S*?\s*?
  PRIVMSG
  \s*?
  (?P<chan>\S*)
  \s*?
  :(?P<msg>[^\r\n]*)
""",
    re.VERBOSE | re.IGNORECASE,
)

_LINKS = re.compile(r"\bhttps?://[^. ]+\.[^. \t\n\r\f\v][^ \n\r]+")


class Bot:
    """Main class to handle bot functionality."""

    def __init__(
        self, config: str = "config/shanghai.ini", chancoms: str = "config/commands.ini", apis: str = "config/apis.ini",
    ):
        """Initialize bot.

        Args:
            config:   Bot specific config file path
            chancoms: Channel commands config file path
            apis:     API config file path

        """
        logger = logging.getLogger(__name__)

        self.config = configparser.ConfigParser()
        with open(config) as conffile:
            self.config.read_file(conffile)
        logger.info("Primary shanghai config loaded")

        self.apiconf = configparser.ConfigParser()
        with open(apis) as apisfile:
            self.apiconf.read_file(apisfile)
        logger.info("Apis config loaded")

        self.chancoms = configparser.ConfigParser()
        with open(chancoms) as comsfile:
            self.chancoms.read_file(comsfile)
        logger.info("Channel specific command config loaded")

        # Saving the channel commands ini file location to write later
        # This is almost certainly going to get changed eventually, as it feels sloppy
        self.chanfile = chancoms

        self.syscoms = {"quit": self.quit, "join": self.join}
        self.match = None
        self.message = None

        default = self.config["DEFAULT"]
        self.irc = connection.ShangSock(default["server"], default.getint("port"), default.getboolean("ssl"))
        self.connect()

    def connect(self) -> None:
        """Connect to and send necessary information to IRC server per protocol.

        Notes:
            The response checking in here is kinda hacky with regexes right now
            It'll be changed when I've got a proper scanner/parser for IRC ABNF
            implemented and working

        Todo:
            Implement parsing grammar with Lark or PLY, stop using regex for this

        """
        logger = logging.getLogger(__name__)
        default = self.config["DEFAULT"]

        self.irc.connect()
        logger.info("Socket bound to server, beginning connection protocol")

        if default["password"]:
            logger.debug(f'Sending password, password is {default["password"]}')
            self.irc.send(f'PASS {default["password"]}\r\n')
        else:
            logger.debug("No connection password is set, not using")

        validnick = False
        logger.debug(f'Entering nick validation loop, attempting {default["nick"]}')
        while not validnick:
            logger.debug(f'Setting nick to {default["nick"]}')
            self.irc.send(f'NICK {default["nick"]}\r\n')
            response = self.irc.receive()
            if response:
                if re.search(r"\b433", response):
                    logger.warning(f'Nick in use: {default["nick"]}')
                    default["nick"] = input("Input a new bot nick: ")
                    logger.info(f'New nick input: {default["nick"]}')
                else:
                    logger.debug(f"Unexpected message {response}, but continuing")
                    validnick = True
            else:
                validnick = True
                logger.info(f'Server accepted nick: {default["nick"]}')

        logger.debug(f'Setting user information, realname {default["realname"]}')
        self.irc.send(f'USER {default["nick"]} 0 * :{default["realname"]}\r\n')

        success = False
        while not success:
            logger.debug(f"Waiting for server to verify auth success...")
            response = self.irc.receive()
            logger.debug(f"Received {response}")
            if response:
                if re.search(r"\b001", response):
                    logger.debug(f"Server sent welcome reply, connection complete")
                    success = True
                elif re.search(r"\b422", response):
                    logger.debug("Server sent NOMOTD, but havent received welcome")
                elif re.search(r"\b376", response):
                    logger.debug("Server sent ENDOFMOTD, but havent received welcome")
                else:
                    logger.debug("Server sent an unexpected message")
        logger.info("Server authentication completed")

    def join(self, channel: str) -> None:
        """Join channel.

        Args:
            channel: Channel bot will attempt to join

        Todo:
            Specification includes KEY parameter for locked channels

        """
        logger = logging.getLogger(__name__)
        logger.info(f"Joining channel {channel}")
        self.irc.send(f"JOIN {channel}\r\n")

    def part(self, channel: str) -> None:
        """Leave channel.

        Args:
            channel: Channel bot will leave

        Todo:
            Specification includes part message

        """
        logger = logging.getLogger(__name__)
        logger.info(f"Leaving channel {channel}")
        self.irc.send(f"PART {channel}\r\n")

    def quit(self) -> None:
        """Quit server and stop bot.

        Notes:
            This does not automatically leave any currently joined channels

        Todo:
            Specification includes quit message

        """
        logger = logging.getLogger(__name__)
        logger.info("Quitting server")
        self.irc.send("QUIT\r\n")
        self.irc.disconnect()
        logger.info("Halting execution")
        exit()

    def send(self, message: str, channel: str) -> None:
        """Send message to channel.

        Args:
            message: Message to be sent
            channel: Channel to send message to

        """
        logger = logging.getLogger(__name__)
        logger.debug(f"Sending {message} to {channel}")
        self.irc.send(f"PRIVMSG {channel} :{message}\r\n")
