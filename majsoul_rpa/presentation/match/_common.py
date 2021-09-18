#!/usr/bin/env python3

import base64
from typing import Tuple
from google.protobuf.message_factory import MessageFactory
import google.protobuf.json_format
import majsoul_rpa._impl.mahjongsoul_pb2 as mahjongsoul_pb2


_MESSAGE_TYPE_MAP = {}
for tdesc in mahjongsoul_pb2.DESCRIPTOR.message_types_by_name.values():
    name = '.' + tdesc.full_name
    _MESSAGE_TYPE_MAP[name] = MessageFactory().GetPrototype(tdesc)


def parse_action(message: object) -> Tuple[int, str, object]:
    step: int = message['step']
    name: str = message['name']
    data: str = message['data']
    data = base64.b64decode(data)

    parser = _MESSAGE_TYPE_MAP[f'.lq.{name}']()
    parser.ParseFromString(data)
    result = google.protobuf.json_format.MessageToDict(
        parser, including_default_value_fields=True,
        preserving_proto_field_name=True)

    return step, name, result
