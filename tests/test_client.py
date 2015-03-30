import socket

from mock import Mock, call
from monitron.client import ClientThread


def create_message_generator(number_of_messages, number_of_chunks):
    """
    Return an iterator to be used as a `socket.recv` side effect that returns 
    `number_of_messages` messages split in `number_of_chunks` chunks.
    """
    total_messages = 'message\r\n' * number_of_messages
    message_length = len(total_messages)
    chunk_length = message_length / number_of_chunks 
    excess_chunk = message_length % chunk_length
    messages = [total_messages[i:i+chunk_length] 
            for i in range(0, message_length, chunk_length)]
    # add excess to the end
    if excess_chunk:
        messages[-1] += total_messages[-excess_chunk:]
    
    return messages


def test_receiving_a_message_in_one_block():
    client_thread = ClientThread(None, None, None)
    mock_conn = Mock(spec=socket.socket)
    mock_conn.recv.side_effect = create_message_generator(1, 1)

    message, remainder = client_thread._receive_message(mock_conn)

    print message, remainder
    assert message == 'message'
    assert remainder == ''
    mock_conn.assert_has_calls([call.recv(4096)])

def test_a_message_spanning_three_blocks():
    client_thread = ClientThread(None, None, None)
    mock_conn = Mock(spec=socket.socket)
    mock_conn.recv.side_effect = create_message_generator(1, 3)

    message, remainder = client_thread._receive_message(mock_conn)

    assert message == 'message'
    assert remainder == ''
    mock_conn.assert_has_calls([call.recv(4096), call.recv(4096), call.recv(4096)])

def test_two_messages_spanning_five_blocks():
    client_thread = ClientThread(None, None, None)
    mock_conn = Mock(spec=socket.socket)
    mock_conn.recv.side_effect = create_message_generator(2, 7)

    message1, remainder = client_thread._receive_message(mock_conn)
    message2, remainder = client_thread._receive_message(mock_conn, remainder)
    
    assert message1 == 'message'
    assert message2 == 'message'
    assert remainder == ''
    mock_conn.assert_has_calls([call.recv(4096), call.recv(4096), call.recv(4096), call.recv(4096), call.recv(4096)])
