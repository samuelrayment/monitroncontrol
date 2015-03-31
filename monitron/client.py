# -*- coding: utf-8 -*-
"""
This module contains all code for connecting as a client to a monitron
server and receiving build status updates.
"""
import socket
import threading
import json

from enum import Enum


class BuildStatusUpdate(object):
    """
    Status update message detailing the current build state from the server 
    """
    def __init__(self, status):
        self.status = status

    def __eq__(self, other):
        return self.status == other.status


class BuildStatus(Enum):
    """
    Enum for the current build status
    """
    Failing = 'failing'
    Acknowledged = 'acknowledged'
    Passing = 'passing'


class ClientThread(threading.Thread):
    """ 
    Client Thread that connects to the running monitron server and sends build
    status updates to the send_queue.
    """
    socket_timeout = 10
    message_chunk_size = 4096
    message_separator = '\r\n'

    def __init__(self, server, port, send_queue):
        super(ClientThread, self).__init__()
        self.server = server
        self.port = port
        self.send_queue = send_queue
    
    def run(self):
        conn = socket.create_connection((self.server, self.port), self.socket_timeout)
        remainder = ''
        while True:
            remainder = self.read_and_send_on_message(conn, remainder)

    def read_and_send_on_message(self, conn, remainder=''):
        message, remainder = self._receive_message(conn, remainder)
        json_message = json.loads(message)
        # TODO catch ValueError
        self.send_queue.put(self._parse_json_to_status_update(json_message))
        return remainder

    def _parse_json_to_status_update(self, json_message):
        """ Return a `BuildStatusUpdate` based on the passed in json_message """
        if len(json_message['failing']) > 0:
            return BuildStatusUpdate(BuildStatus.Failing)
        elif len(json_message['acknowledged']) > 0:
            return BuildStatusUpdate(BuildStatus.Acknowledged)
        else:
            return BuildStatusUpdate(BuildStatus.Passing)

    def _receive_message(self, conn, remainder=''):
        message_data = [remainder] if remainder else []
        while True:
            try:
                message_part = conn.recv(self.message_chunk_size)
                message_data.append(message_part)
                # this is not efficient as we join alot but we need to cope
                # with separators on boundaries of reads, this passes the tests
                # and I can come back and write something better later.
                complete_message = ''.join(message_data)
                separator_index = complete_message.find(self.message_separator)
                if separator_index > 0:
                    # we've found the end of the message
                    return complete_message[:separator_index], complete_message[separator_index + len(self.message_separator):]
            except socket.error as e:
                # TODO logging
                print e
                raise
            if message_part == '':
                # socket error
                print 'socket error'
                return ('', '')
