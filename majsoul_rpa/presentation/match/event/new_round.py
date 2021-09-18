#!/usr/bin/env python3


import datetime
from typing import (Optional, List,)
from majsoul_rpa.presentation.match.event._base import EventBase


class NewRoundEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime.datetime) -> None:
        super(NewRoundEvent, self).__init__(timestamp)
        self.__chang = data['chang']
        self.__ju = data['ju']
        self.__ben = data['ben']
        self.__liqibang = data['liqibang']
        self.__dora_indicators = data['doras']
        self.__left_tile_count = data['left_tile_count']
        self.__scores = data['scores']
        self.__shoupai = data['tiles'][:13]
        if len(data['tiles']) == 14:
            self.__zimopai = data['tiles'][13]
        else:
            self.__zimopai = None

    @property
    def chang(self) -> int:
        assert(self.__chang >= 0)
        assert(self.__chang < 3)
        return self.__chang

    @property
    def ju(self) -> int:
        assert(self.__ju >= 0)
        assert(self.__ju < 4)
        return self.__ju

    @property
    def ben(self) -> int:
        assert(self.__ben >= 0)
        return self.__ben

    @property
    def liqibang(self) -> int:
        assert(self.__liqibang >= 0)
        return self.__liqibang

    @property
    def dora_indicators(self) -> List[str]:
        assert(len(self.__dora_indicators) >= 1)
        assert(len(self.__dora_indicators) <= 5)
        return self.__dora_indicators

    @property
    def left_tile_count(self) -> int:
        assert(self.__left_tile_count < 70)
        assert(self.__left_tile_count >= 0)
        return self.__left_tile_count

    @property
    def scores(self) -> List[int]:
        assert(len(self.__scores) in (4, 3))
        return self.__scores

    @property
    def shoupai(self) -> List[str]:
        assert(len(self.__shoupai) == 13)
        return self.__shoupai

    @property
    def zimopai(self) -> Optional[str]:
        return self.__zimopai
