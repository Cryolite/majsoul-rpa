#!/usr/bin/env python3

from typing import (Tuple, List, Iterable,)


class DapaiOperation(object):
    def __init__(self, forbidden_tiles: Iterable[str]) -> None:
        self.__forbidden_tiles = [t for t in forbidden_tiles]

    @property
    def type(self) -> str:
        return '打牌'

    @property
    def forbidden_tiles(self) -> List[str]:
        return self.__forbidden_tiles


class ChiOperation(object):
    def __init__(self, combinations: Iterable[str]) -> None:
        self.__combinations = []
        for combination in combinations:
            tiles = combination.split('|')
            assert(len(tiles) == 2)
            self.__combinations.append(tuple(t for t in tiles))

    @property
    def type(self) -> str:
        return 'チー'

    @property
    def combinations(self) -> List[Tuple[str]]:
        return self.__combinations


class PengOperation(object):
    def __init__(self, combinations: Iterable[str]) -> None:
        self.__combinations = []
        for combination in combinations:
            tiles = combination.split('|')
            assert(len(tiles) == 2)
            self.__combinations.append(tuple(t for t in tiles))

    @property
    def type(self) -> str:
        return 'ポン'

    @property
    def combinations(self) -> List[Tuple[str]]:
        return self.__combinations


class AngangOperation(object):
    def __init__(self, combinations: Iterable[str]) -> None:
        self.__combinations = []
        for combination in combinations:
            tiles = combination.split('|')
            assert(len(tiles) == 4)
            self.__combinations.append(tuple(t for t in tiles))

    @property
    def type(self) -> str:
        return '暗槓'

    @property
    def combinations(self) -> List[Tuple[str]]:
        return self.__combinations


class DaminggangOperation(object):
    def __init__(self, combinations: Iterable[str]) -> None:
        self.__combinations = []
        for combination in combinations:
            tiles = combination.split('|')
            assert(len(tiles) == 3)
            self.__combinations.append(tuple(t for t in tiles))

    @property
    def type(self) -> str:
        return '大明槓'

    @property
    def combinations(self) -> List[Tuple[str]]:
        return self.__combinations


class JiagangOperation(object):
    def __init__(self, combinations: Iterable[str]) -> None:
        self.__combinations = []
        for combination in combinations:
            tiles = combination.split('|')
            assert(len(tiles) == 4)
            self.__combinations.append(tuple(t for t in tiles))

    @property
    def type(self) -> str:
        return '加槓'

    @property
    def combinations(self) -> List[Tuple[str]]:
        return self.__combinations


class LiqiOperation(object):
    def __init__(self, combinations: Iterable[str]) -> None:
        self.__candidate_dapai_list = [t for t in combinations]

    @property
    def type(self) -> str:
        return '立直'

    @property
    def candidate_dapai_list(self) -> List[str]:
        return self.__candidate_dapai_list


class ZimohuOperation(object):
    def __init__(self) -> None:
        pass

    @property
    def type(self) -> str:
        return '自摸和'


class RongOperation(object):
    def __init__(self) -> None:
        pass

    @property
    def type(self) -> str:
        return 'ロン'


class JiuzhongjiupaiOperation(object):
    def __init__(self) -> None:
        pass

    @property
    def type(self) -> str:
        return '九種九牌'


class OperationList(object):
    def __init__(self, operation_list: object) -> None:
        self.__basic_time = operation_list['time_fixed']
        self.__extra_time = operation_list['time_add']
        self.__operations = []
        for operation in operation_list['operation_list']:
            if operation['type'] == 1:
                op = DapaiOperation(operation['combination'])
                self.__operations.append(op)
            elif operation['type'] == 2:
                op = ChiOperation(operation['combination'])
                self.__operations.append(op)
            elif operation['type'] == 3:
                op = PengOperation(operation['combination'])
                self.__operations.append(op)
            elif operation['type'] == 4:
                op = AngangOperation(operation['combination'])
                self.__operations.append(op)
            elif operation['type'] == 5:
                op = DaminggangOperation(operation['combination'])
                self.__operations.append(op)
            elif operation['type'] == 6:
                op = JiagangOperation(operation['combination'])
                self.__operations.append(op)
            elif operation['type'] == 7:
                op = LiqiOperation(operation['combination'])
                self.__operations.append(op)
            elif operation['type'] == 8:
                op = ZimohuOperation()
                self.__operations.append(op)
            elif operation['type'] == 9:
                op = RongOperation()
                self.__operations.append(op)
            elif operation['type'] == 10:
                op = JiuzhongjiupaiOperation()
                self.__operations.append(op)
            else:
                raise ValueError(f'type == {operation["type"]}')

    @property
    def basic_time(self) -> int:
        return self.__basic_time // 1000

    @property
    def extra_time(self) -> int:
        return self.__extra_time // 1000

    def __iter__(self):
        return iter(self.__operations)
