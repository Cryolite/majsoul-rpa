import base64
from typing import (Tuple,)
from google.protobuf.message_factory import MessageFactory
import google.protobuf.json_format
import majsoul_rpa._impl.mahjongsoul_pb2 as mahjongsoul_pb2


_MESSAGE_TYPE_MAP = {}
for tdesc in mahjongsoul_pb2.DESCRIPTOR.message_types_by_name.values():
    _name = '.' + tdesc.full_name
    _MESSAGE_TYPE_MAP[_name] = MessageFactory().GetPrototype(tdesc)


def _decode_bytes(buf: bytes) -> bytearray:
    keys = [132, 94, 78, 66, 57, 162, 31, 96, 28]
    decode = bytearray()
    for i, _byte in enumerate(buf):
        mask = ((23 ^ len(buf)) + 5 * i + keys[i % len(keys)]) & 255
        _byte ^= mask
        decode += _byte.to_bytes(1, 'little')
    return decode


def parse_action(message: object, *, restore: bool=False) -> Tuple[int, str, object]:
    step: int = message['step']
    name: str = message['name']
    encoded_data: str = message['data']
    data: bytes = base64.b64decode(encoded_data)

    if not restore:
        data = _decode_bytes(data)

    parser = _MESSAGE_TYPE_MAP[f'.lq.{name}']()
    parser.ParseFromString(data)
    result = google.protobuf.json_format.MessageToDict(
        parser, including_default_value_fields=True,
        preserving_proto_field_name=True)

    return step, name, result
