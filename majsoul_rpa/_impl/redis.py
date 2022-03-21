#!/usr/bin/env python3

import datetime
import subprocess
import json
import base64
from typing import (Optional, Tuple)
import redis
from google.protobuf.message_factory import MessageFactory
import google.protobuf.json_format
from majsoul_rpa._impl import mahjongsoul_pb2
from majsoul_rpa.common import TimeoutType


Message = Tuple[str, str, object, Optional[object], datetime.datetime]


class Redis(object):
    def __init__(self, host='redis', port=6379):
        self.__redis = redis.Redis(host, port)

        self.__message_type_map = {}
        for sdesc in mahjongsoul_pb2.DESCRIPTOR.services_by_name.values():
            for mdesc in sdesc.methods:
                self.__message_type_map['.' + mdesc.full_name] \
                    = (MessageFactory().GetPrototype(mdesc.input_type),
                    MessageFactory().GetPrototype(mdesc.output_type))
        for tdesc in mahjongsoul_pb2.DESCRIPTOR.message_types_by_name.values():
            self.__message_type_map['.' + tdesc.full_name] \
                = (MessageFactory().GetPrototype(tdesc), None)

        self.__put_back_messages = []
        self.__account_id = None

    # account id が取得できる WebSocket メッセージ一覧
    __ACCOUNT_ID_MESSAGES = {
        '.lq.Lobby.oauth2Login': ['account_id'],
        '.lq.Lobby.createRoom': ['room', 'owner_id'],
    }

    def dequeue_message(self, timeout: TimeoutType) -> Optional[Message]:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)

        if timeout.total_seconds() <= 0.0:
            return None

        if len(self.__put_back_messages) > 0:
            return self.__put_back_messages.pop(0)

        message: Optional[Tuple[str, bytes]] = self.__redis.blpop(
            'message_queue', timeout.total_seconds())
        if message is None:
            return None
        assert(message[0] == b'message_queue')
        _, message = message

        message = message.decode('UTF-8')
        message = json.loads(message)
        request_direction: str = message['request_direction']
        request: str = message['request']
        response: Optional[str] = message['response']
        timestamp = message['timestamp']

        # JSON 化するためにエンコードしていたデータをデコードする．
        request = base64.b64decode(request)
        if response is not None:
            response = base64.b64decode(response)
        timestamp = datetime.datetime.fromtimestamp(
            timestamp, datetime.timezone.utc)

        def _unwrap_message(message) -> Tuple[str, bytes]:
            wrapper = mahjongsoul_pb2.Wrapper()
            wrapper.ParseFromString(message)
            return (wrapper.name, wrapper.data)

        if request[0] == 1:
            # レスポンスが必要無いリクエストメッセージでメッセージ番号の
            # 2バイトが無い．
            name, request = _unwrap_message(request[1:])
        elif request[0] == 2:
            # 対応するレスポンスメッセージが存在するリクエストメッセージで，
            # メッセージ番号を格納するための2バイトが存在し，また，
            # レスポンスメッセージのパースのために名前を取り出す必要がある．
            name, request = _unwrap_message(request[3:])
        else:
            raise RuntimeError(f'{request[0]}: unknown request type.')

        if response is not None:
            if response[0] != 3:
                raise RuntimeError(f'{response[0]}: unknown response type.')
            _, response = _unwrap_message(response[3:])
            if _ != '':
                raise RuntimeError(f'{_}: unknown response name.')

        # Protocol Buffers メッセージを JSONizable object 形式に変換する．
        def _jsonize(name: str, data: bytes, is_response: bool) -> object:
            if is_response:
                try:
                    parser = self.__message_type_map[name][1]()
                except IndexError as e:
                    proc = subprocess.run(
                        ['protoc', '--decode_raw'], input=data,
                        capture_output=True)
                    rc = proc.returncode
                    stdout = proc.stdout.decode('UTF-8')
                    stderr = proc.stderr.decode('UTF-8')
                    raise RuntimeError(f'''A new API found:
  name: {name}
  data: {data}

===============================
Output of `protoc --decode_raw`
===============================
{stdout}''')
            else:
                try:
                    parser = self.__message_type_map[name][0]()
                except KeyError as e:
                    proc = subprocess.run(
                        ['protoc', '--decode_raw'], input=data,
                        capture_output=True)
                    rc = proc.returncode
                    stdout = proc.stdout.decode('UTF-8')
                    stderr = proc.stderr.decode('UTF-8')
                    raise RuntimeError(f'''A new API found:
  name: {name}
  data: {data}

===============================
Output of `protoc --decode_raw`
===============================
{stdout}''')
            parser.ParseFromString(data)

            jsonized = google.protobuf.json_format.MessageToDict(
                parser, including_default_value_fields=True,
                preserving_proto_field_name=True)
            return jsonized

        request = _jsonize(name, request, False)
        if response is not None:
            response = _jsonize(name, response, True)

        # account id が載っているメッセージなら account id を抽出する．
        if name in Redis.__ACCOUNT_ID_MESSAGES:
            if response is None:
                raise RuntimeError('Message without any response.')
            account_id = response
            keys = Redis.__ACCOUNT_ID_MESSAGES[name]
            for key in keys:
                if key not in account_id:
                    raise RuntimeError(
                        f'''{name}: {key}: Could not find account id field:
{response}''')
                account_id = account_id[key]
            if self.__account_id is None:
                self.__account_id = account_id
            elif account_id != self.__account_id:
                raise RuntimeError('Inconsistent account IDs.')

        return (request_direction, name, request, response, timestamp)

    def put_back(self, message: Message) -> None:
        self.__put_back_messages.insert(0, message)

    @property
    def account_id(self) -> Optional[int]:
        return self.__account_id
