#!/usr/bin/env python3


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
