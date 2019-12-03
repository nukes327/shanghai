#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Connections module for Shanghai.

Manages the connection to an IRC server,
Receives and sends data

"""

import logging
import socket
import ssl
from time import sleep
from typing import List

from .exceptions import ShangSockError


class ShangSock:
    """Socket object for the bot."""

    def __init__(self, server: str, port: int,
                 ssl_flag: bool, *, timeout: float = 0.5):
        """Initialize values for socket object.

        Args:
            server:   The server to bind the socket to
            port:     The port to connect to the server through
            ssl_flag: Whether SSL should be used to wrap the socket or not
            timeout:  The timeout for the socket

        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = server
        self.port = port
        self.ssl = ssl_flag
        self.timeout = timeout
        self.__receive_cache: List[str] = []

    def connect(self) -> None:
        """Create socket and bind it to given server and port.

        Notes:
            Only connects to the server the object was initialized with
            All IRC protocol should be handled by the caller

        """
        logger = logging.getLogger(__name__)
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
            try:
                self.sock = context.wrap_socket(self.sock, server_hostname=self.server)
            except socket.timeout as inst:
                logger.warning('SSL handshake attempt timed out', exc_info=inst)
                self.reconnect()
            logger.info('SSL Socket ready for use')
        else:
            logger.info('Socket ready for use')

    def reconnect(self, delay: int = 10, increasing: bool = True) -> None:
        """Attempt reconnection to a socket when connect times out.

        Args:
            delay:      Initial delay in seconds before attempting to reconnect
            increasing: Whether or not the function should increase the delay
                        after every failed connection attempt

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
        """Unbind socket from server.

        Notes:
            As with other methods in this class, IRC protocol should be handled
            by the user before calling these methods.

        """
        logging.getLogger(__name__).info('Shutting down socket')
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def send(self, message: str) -> None:
        """Encode string to bytes and send it to socket.

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

    def receive(self) -> str:
        """Receive a delimited IRC message from socket.

        Returns:
            A *single* message from the socket as a string,
            or an empty string if there is nothing to receive

        Notes:
            Any remaining data after forming and returning a message from
            received data is cached to be processed next time the method is called.

            If there is a cache present, it will be checked first for a complete
            message to be returned, in which case it will be returned without
            receiving more data from the socket. Otherwise, the incomplete data
            will form the beginning of the string built from received data.

        """
        logger = logging.getLogger(__name__)
        logger.debug(f'Current cache: {self.__receive_cache}')

        if self.__receive_cache:
            logger.debug('More data waiting in cache, checking it first')
            message = ''.join(self.__receive_cache).partition('\r\n')
            if message[1]:
                logger.debug('Complete message was remaining in cache')
                logger.debug(f'Caching {message[2]}')
                self.__receive_cache = [message[2]]
                logger.debug(f'Returning {message[0]}')
                return ''.join([message[0], message[1]])
        else:
            logger.debug('No cached data present')

        try:
            logger.debug('Receiving from socket')
            data = self.sock.recv(4096)
        except socket.timeout:
            logger.debug('Socket timeout, nothing to receive')
            return ''
        if not data:
            logger.warning('Unexpected disconnection while attempting to receive data')
            self.__receive_cache = []
            raise ShangSockError(error='Unexpected Disconnect')

        logger.debug('Data received, merging with cache and separating by CRLF')
        decoded = bytes.decode(data, encoding='utf-8')
        cache = ''.join(self.__receive_cache)
        message = ''.join([cache, decoded]).partition('\r\n')
        if message[1]:  # BUG: Probably fails with IndexError exception if there is no CRLF
            logger.debug('CRLF present, so a complete message is ready')
            logger.debug(f'Caching {message[2]}')
            self.__receive_cache = [message[2]]
            logger.debug(f'Returning {message[0]}')
            return ''.join([message[0], message[1]])
        else:
            logger.debug('No CRLF present, so there is no complete message ready')
            logger.debug(f'Caching {message[0]}')
            self.__receive_cache = [message[0]]
        return ''
