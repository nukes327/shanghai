#!/usr/bin/env python3
"""Connections module for Shanghai

Manages the connection to an IRC server,
Receives and sends data

"""

import logging
import socket

from .exceptions import ShangSockError


class ShangSock:
    """The socket object for the bot"""
    def __init__(self, server: str, port: int,
                 ssl: bool, *, timeout: float = 0.5):
        """Inits values for the socket object

        Args:
            server: The server to bind the socket to
            port: The port to connect to the server through
            ssl: Whether SSL should be used to wrap the socket or not
            timeout: The timeout for the socket

        """
        self.sock = None
        self.server = server
        self.port = port
        self.ssl = ssl
        self.timeout = timeout

    def connect(self) -> None:
        """Creates socket and binds it to given server and port

        Notes:
            Only connects to the server the object was initialized with
            All IRC protocol should be handled by the caller

        """
        logger = logging.getLogger(__name__)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        logger.debug(f'Timeout set to {timeout}')
        logger.info(f'Attempting to bind socket to {server}:{port}')
        try:
            s.connect((server, port))
        except socket.timeout as inst:
            logger.warning(f'Failed to bind socket to {server}:{port} before timeout')
            # Should do something here rather than pass
            pass
        logger.info(f'Connected to {server}:{port}')
        if ssl:
            logger.info('Creating an SSL context and wrapping the socket')
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(s, server_hostname=server)
            logger.info('SSL Socket ready for use')
        else:
            self.irc = s
            logger.info('Socket ready for use')

    def reconnect(self) -> None:

    def disconnect(self) -> None:
        """Unbinds the socket from the server

        Notes:
            As with other methods in this class, IRC protocol should
            be handled by the user before calling these methods.

        """
        self.irc.shutdown(socket.SHUT_RDWR)
        self.irc.close()

    def send(self, message: str) -> None:
        """Encodes a string to bytes and sends it to the socket

        Args:
            message: The message (including CRLF) to send

        """
        logger = logging.getLogger(__name__)
        total = 0
        logger.debug('Beginning send to socket')
        while total < len(message):
            sent = self.sock.send(str.encode(message))
            if not sent:
                raise RuntimeError('Socket connection lost')
            total += sent
            logger.debug(f'Total sent: {total}')
        logger.debug('Send complete')

    def receive(self, *, delimited: list = [], incomplete: list = []) -> str:
        """Receives a delimited IRC message from the socket

        Args:
            delimited: A default empty list used for memoization of
                complete delimited messages
            incomplete: A default empty list used for memoization of
                incomplete, non-delimited messages

        Notes:
            This returns a *single* message from the socket as a string.
            *Any* excess is saved in the default lists to be handled at next call
            Fully delimited excess will be returned at next call without recving from the socket
            Incomplete excess will be returned after more data is recv'd to complete it

        """
        pass
