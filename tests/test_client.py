# -*- coding: utf-8 -*-
import socket
from queue import Queue

from nose_parameterized import parameterized, param
from mock import Mock, call, patch
from monitron.client import ClientThread, BuildStatusUpdate, BuildStatus


def create_message_generator(number_of_messages, number_of_chunks):
    """
    Return an iterator to be used as a `socket.recv` side effect that returns 
    `number_of_messages` messages split in `number_of_chunks` chunks.
    """
    total_messages = b'message\n' * number_of_messages
    message_length = len(total_messages)
    chunk_length = message_length // number_of_chunks
    excess_chunk = message_length - chunk_length * number_of_chunks 
    messages = [total_messages[i:i+chunk_length] 
            for i in range(0, number_of_chunks * chunk_length, chunk_length)]
    # add excess to the end
    if excess_chunk:
        messages[-1] += total_messages[-excess_chunk:]
    
    return messages


@parameterized([
    (1, 1), (1, 3), (2, 7), (2,5)
])
def test_receiving_a_message_in_chunks(message_count, chunks):
    client_thread = ClientThread(None, None, None)
    mock_conn = Mock(spec=socket.socket)
    mock_conn.recv.side_effect = create_message_generator(message_count, chunks)

    remainder = ''
    for i in range(message_count):
        message, remainder = client_thread._receive_message(mock_conn, remainder)
        assert message == 'message'

    print('remainder: %s' % remainder)
    print('rem len: %d' % len(remainder))
    assert remainder == ''
    mock_conn.assert_has_calls([call.recv(4096)] * chunks)


@patch.object(ClientThread, '_receive_message')
def test_read_and_send_on_message_parses_message_and_send_failure_to_queue(mock_receive):
    message = '{"type":"builds","error":"","failing":[{"name":"Failing Build","building":false,"user":"","url":"http://localhost:8000/job/Failing%20Build/","number_of_failures":1,"failing_since":1425590828000}],"acknowledged":[],"healthy":[]}'
    mock_receive.return_value = (message, 'b')
    mock_conn = Mock(spec=socket.socket)
    mock_queue = Mock(spec=Queue)

    client_thread = ClientThread(None, None, mock_queue)

    remainder = client_thread.read_and_send_on_message(mock_conn, '')

    assert remainder == 'b'
    mock_queue.assert_has_calls([
        call.put(BuildStatusUpdate(BuildStatus.Failing))
    ])
    mock_receive.assert_has_calls([
        call(mock_conn, '')
    ])

    
@patch.object(ClientThread, '_receive_message')
def test_read_and_send_on_message_parses_message_and_send_acknowledged_to_queue(mock_receive):
    message = '{"type":"builds","error":"","failing":[],"acknowledged":[{"name":"Build","building":false,"user":"","url":"http://localhost:8000/job/Failing%20Build/","number_of_failures":0,"failing_since":0}],"healthy":[]}'
    mock_receive.return_value = (message, 'b')
    mock_conn = Mock(spec=socket.socket)
    mock_queue = Mock(spec=Queue)

    client_thread = ClientThread(None, None, mock_queue)

    remainder = client_thread.read_and_send_on_message(mock_conn, '')

    assert remainder == 'b'
    mock_queue.assert_has_calls([
        call.put(BuildStatusUpdate(BuildStatus.Acknowledged))
    ])
    mock_receive.assert_has_calls([
        call(mock_conn, '')
    ])


@patch.object(ClientThread, '_receive_message')
def test_read_and_send_on_message_parses_message_and_send_passing_to_queue(mock_receive):
    message = '{"type":"builds","error":"","failing":[],"acknowledged":[],"healthy":[{"name":"Build","building":false,"user":"","url":"http://localhost:8000/job/Failing%20Build/","number_of_failures":0,"failing_since":0}]}'
    mock_receive.return_value = (message, 'b')
    mock_conn = Mock(spec=socket.socket)
    mock_queue = Mock(spec=Queue)

    client_thread = ClientThread(None, None, mock_queue)

    remainder = client_thread.read_and_send_on_message(mock_conn, '')

    assert remainder == 'b'
    mock_queue.assert_has_calls([
        call.put(BuildStatusUpdate(BuildStatus.Passing))
    ])
    mock_receive.assert_has_calls([
        call(mock_conn, '')
    ])
