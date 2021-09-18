#!/usr/bin/env python3


import datetime
from typing import (Union,)


_LEVEL_ID_MAP = {
    10101: '初心1',
    10102: '初心2',
    10103: '初心3',
    10201: '雀士1',
    10202: '雀士2',
    10203: '雀士3',
    10301: '雀傑1',
    10302: '雀傑2',
    10303: '雀傑3',
    10401: '雀豪1',
    10402: '雀豪2',
    10403: '雀豪3',
    10501: '雀聖1',
    10502: '雀聖2',
    10503: '雀聖3',
    10601: '魂天',
    20101: '初心1',
    20102: '初心2',
    20103: '初心3',
    20201: '雀士1',
    20202: '雀士2',
    20203: '雀士3',
    20301: '雀傑1',
    20302: '雀傑2',
    20303: '雀傑3',
    20401: '雀豪1',
    20402: '雀豪2',
    20403: '雀豪3',
    20501: '雀聖1',
    20502: '雀聖2',
    20503: '雀聖3',
    20601: '魂天',
}


def id2level(level_id: int) -> str:
    return _LEVEL_ID_MAP[level_id]


_CHARACTER_ID_MAP = {
    200001: '一姫',
    200032: 'エリサ'
}


def id2character(character_id: int) -> str:
    return _CHARACTER_ID_MAP[character_id]


TimeoutType = Union[int, float, datetime.timedelta]


class Player(object):
    def __init__(self, account_id: int, name: str) -> None:
        self.__account_id = account_id
        self.__name = name

    @property
    def account_id(self) -> int:
        return self.__account_id

    @property
    def name(self) -> str:
        return self.__name
