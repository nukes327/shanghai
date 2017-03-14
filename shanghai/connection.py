#!/usr/bin/env python3
"""Connections module for Shanghai

Manages the connection to an IRC server,
Receives and sends data

"""

import logging
import socket
import ssl
from time import sleep

from .exceptions import ShangSockError


class ShangSock:
    """The socket object for the bot"""
    def __init__(self, server: str, port: int,
                 ssl_flag: bool, *, timeout: float = 0.5):
        """Inits values for the socket object

        Args:
            server: The server to bind the socket to
            port: The port to connect to the server through
            ssl_flag: Whether SSL should be used to wrap the socket or not
            timeout: The timeout for the socket

        """
        self.sock = None
        self.server = server
        self.port = port
        self.ssl = ssl_flag
        self.timeout = timeout

    def connect(self) -> None:
        """Creates socket and binds it to given server and port

        Notes:
            Only connects to the server the object was initialized with
            All IRC protocol should be handled by the caller

        """
        logger = logging.getLogger(__name__)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        logger.debug(f'Timeout set to {self.timeout}')
        logger.info(f'Attempting to bind socket to {self.server}:{self.port}')
        try:
            self.sock.connect((self.server, self.port))
        except socket.timeout as inst:
            logger.warning(f'Failed to bind socket to {self.server}:{self.port} before timeout',
                           exc_info=inst)
            self.reconnect()
        logger.info(f'Connected to {self.server}:{self.port}')
        if self.ssl:
            logger.info('Creating an SSL context and wrapping the socket')
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(self.sock, server_hostname=self.server)
            logger.info('SSL Socket ready for use')
        else:
            logger.info('Socket ready for use')

    def reconnect(self, delay: int = 10, increasing: bool = True) -> None:
        """Attempts reconnects to a socket when connect timed out

        Args:
            delay: Initial delay in seconds before attempting to reconnect
            increasing: Whether or not the function should increase the
                delay every failed connection attempt

        """
        logger = logging.getLogger(__name__)
        while True:
            sleep(delay)
            try:
                self.sock.connect((self.server, self.port))
            except socket.timeout as inst:
                logger.warning('Failed to bind socket during reconnect attempt '
                               f'after a delay of {delay} seconds.', exc_info=inst)
                delay += 5 * increasing
            else:
                break

    def disconnect(self) -> None:
        """Unbinds the socket from the server

        Notes:
            As with other methods in this class, IRC protocol should
            be handled by the user before calling these methods.

        """
        logging.getLogger(__name__).info('Shutting down socket')
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

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

    def receive(self, *, cache: list = []) -> str:
        """Receives a delimited IRC message from the socket

        Args:
            cache: A default empty list used for caching of excess received data

        Returns:
            A *single* message from the socket as a string,
            or an empty string if there is nothing to receive

        Notes:
            Any excess is cached to be handled at next call
            Fully delimited excess will be returned at next call without recving from the socket
            Incomplete excess will be returned after more data is recv'd to complete it

        """
        logger = logging.getLogger(__name__)

        if cache:
            logger.debug('More data waiting in cache, checking it first')
            message = ''.join(cache).partition('\r\n')
            if message[1]:
                cache = message[2]
                return ''.join([message[0], message[1]])

        try:
            logger.debug('Receiving from socket')
            data = self.sock.recv(4096)
        except socket.timeout as inst:
            logger.debug('Socket timeout, nothing to receive', exc_info=inst)
            return ''
        if not data:
            logger.warning('Unexpected disconnection while attempting to receive data')
            cache = []
            raise ShangSockError(error='Unexpected Disconnect')

        logger.debug('Data received, merging with cache and separating by CRLF')
        message = ''.join(cache)
        message = ''.join([message, data]).partition('\r\n')
        if message[1]:
            cache = message[2]
            return ''.join([message[0], message[1]])
        cache = message[0]
        return ''
