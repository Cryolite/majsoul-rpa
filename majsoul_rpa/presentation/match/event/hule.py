#!/usr/bin/env python3

import datetime
from typing import List
from majsoul_rpa.presentation.match.event._base import EventBase


class HuleEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime.datetime) -> None:
        super(HuleEvent, self).__init__(timestamp)
        # TODO: data['hules']
        self.__old_scores = data['old_scores']
        self.__delta_scores = data['delta_scores']
        self.__scores = data['scores']

    @property
    def old_scores(self) -> List[int]:
        assert(len(self.__old_scores) in (4, 3))
        return self.__old_scores

    @property
    def delta_scores(self) -> List[int]:
        assert(len(self.__delta_scores) in (4, 3))
        return self.__delta_scores

    @property
    def scores(self) -> List[int]:
        assert(len(self.__scores) in (4, 3))
        return self.__scores
