import re
import datetime
import logging
import json
import base64
import wsproto
from redis import Redis


__redis = Redis(host='redis')
__message_queue = {}


def websocket_message(flow) -> None:
    global __redis
    global __message_queue

    # mitmproxy のバージョンによる違いを吸収する．
    if hasattr(flow, 'websocket'):
        websocket_data = flow.websocket
    else:
        websocket_data = flow

    # WebSocket の最後のメッセージを取得する．
    if len(websocket_data.messages) == 0:
        raise RuntimeError(f'`len(websocket_data.messages)` == 0')
    message = websocket_data.messages[-1]

    if message.type != wsproto.frame_protocol.Opcode.BINARY:
        raise RuntimeError(
            f'{message.type}: An unsupported WebSocket message type.')

    if message.from_client:
        direction = 'outbound'
    else:
        direction = 'inbound'

    content = message.content

    m = re.search(b'^(?:\x01|\x02..)\n.(.*?)\x12', content, flags=re.DOTALL)
    if m is not None:
        type_ = content[0]
        assert(type_ in [1, 2])

        number = None
        if type_ == 2:
            number = int.from_bytes(content[1:2], byteorder='little')

        name = m.group(1).decode('UTF-8')

        if type_ == 2:
            # レスポンスメッセージを期待するリクエストメッセージの処理．
            # 対応するレスポンスメッセージが検出されるまでメッセージを
            # キューに保存しておく．
            if number in __message_queue:
                prev_request = __message_queue[number]
                logging.warning(f'''There is not any response message\
 for the following WebSocket request message:
direction: {prev_request['direction']}
content: {prev_request['request']}''')

            __message_queue[number] = {
                'direction': direction,
                'name': name,
                'request': content
            }

            return

        # レスポンスを必要としないリクエストメッセージの処理．
        assert(type_ == 1)
        assert(number is None)

        request_direction = direction
        request = content

        if request_direction == 'outbound':
            direction = 'inbound'
        else:
            assert(request_direction == 'inbound')
            direction = 'outbound'
        response = None
    else:
        # レスポンスメッセージ．
        # キューから対応するリクエストメッセージを探し出す．
        m = re.search(b'^\x03..\n\x00\x12', content, flags=re.DOTALL)
        if m is None:
            raise RuntimeError(f'''An unknown WebSocket message:
direction: {direction}
content: {content}''')

        number = int.from_bytes(content[1:2], byteorder='little')
        if number not in __message_queue:
            raise RuntimeError(f'''An WebSocket response message\
 that does not match to any request message:
direction: {direction}
content: {content}''')

        request_direction = __message_queue[number]['direction']
        name = __message_queue[number]['name']
        request = __message_queue[number]['request']
        response = content
        del __message_queue[number]

    # リクエストとレスポンスの方向が整合しているか確認する．
    if request_direction == 'inbound':
        if direction == 'inbound':
            raise RuntimeError('Both request and response WebSocket\
 messages are inbound.')
        assert(direction == 'outbound')
    else:
        assert(request_direction == 'outbound')
        if direction == 'outbound':
            raise RuntimeError('Both request and response WebSocket\
 messages are outbound.')
        assert(direction == 'inbound')

    # Redis に enqueue できるよう JSON にできる形式にエンコードする．
    request = base64.b64encode(request).decode('UTF-8')
    if response is not None:
        response = base64.b64encode(response).decode('UTF-8')
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    data = {
        'request_direction': request_direction,
        'request': request,
        'response': response,
        'timestamp': now.timestamp()
    }

    data = json.dumps(data, allow_nan=False, separators=(',', ':'))
    data = data.encode('UTF-8')
    __redis.rpush('message_queue', data)
