#!/usr/bin/env bash

import re
from majsoul_rpa.presentation.presentation_base import InconsistentMessage
from typing import (Optional, Tuple, List, Iterable,)
from majsoul_rpa.common import Player


class MatchPlayer(Player):
    def __init__(
        self, account_id: int, name: str, level4: str, level3: str,
        character: str) -> None:
        super(MatchPlayer, self).__init__(account_id, name)
        self.__level4 = level4
        self.__level3 = level3
        self.__character = character

    @property
    def level4(self) -> str:
        return self.__level4

    @property
    def level3(self) -> str:
        return self.__level3

    @property
    def character(self) -> str:
        return self.__character


class MatchState(object):
    def __init__(self) -> None:
        self.__uuid = None
        self.__seat = None
        self.__players = []

    def _set_uuid(self, uuid: str) -> None:
        import sys
        import traceback
        if self.__uuid is None:
            self.__uuid = uuid
        elif uuid != self.__uuid:
            raise ValueError(f'''An inconsistent UUIDs.
Old one: {self.__uuid}
New one: {uuid}''')

    def _set_seat(self, seat: int) -> None:
        if self.__seat is not None:
            raise RuntimeError('`_set_seat` is called multiple times.')
        self.__seat = seat

    def _set_players(self, players: Iterable[MatchPlayer]) -> None:
        if len(self.__players) > 0:
            raise RuntimeError('`_set_players` is called multiple times.')
        self.__players = [p for p in players]

    @property
    def uuid(self) -> str:
        if self.__uuid is None:
            raise ValueError('UUID has not been initialized yet.')
        return self.__uuid

    @property
    def seat(self) -> int:
        if self.__seat is None:
            raise ValueError('`seat` has not been initialized yet.')
        return self.__seat

    @property
    def players(self) -> List[MatchPlayer]:
        if self.__players is None:
            raise ValueError('Players have not been initialized yet.')
        return self.__players


class RoundState(object):
    def __init__(self, match_state: MatchState, data: object) -> None:
        self.__match_state = match_state
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
        self.__he = [[]] * 4
        self.__fulu = [[]] * 4
        self.__liqi = [False] * 4
        self.__wliqi = [False] * 4
        self.__first_draw = [True] * 4
        self.__yifa = [False] * 4
        self.__lingshang_zimo = [False] * 4
        self.__prev_dapai_seat = None
        self.__prev_dapai = None

    def __hand_in(self) -> None:
        # 自摸牌を手牌に組み入れて理牌する．
        assert(self.__zimopai is not None)
        self.__shoupai.append(self.__zimopai)
        self.__zimopai = None

        # 理牌
        shoupai = [re.sub("^([1-9])([mpsz])$", "\\2\\1@", t) for t in self.__shoupai]
        shoupai = [re.sub("^0([mps])$", "\\g<1>5!", t) for t in shoupai]
        shoupai.sort()
        shoupai = [re.sub("^([mps])5!$", "0\\1", t) for t in shoupai]
        self.__shoupai = [re.sub("^([mpsz])([1-9])@$", "\\2\\1", t) for t in shoupai]

    def _on_zimo(self, data: object) -> None:
        if data['seat'] == self.__match_state.seat:
            assert(self.__zimopai is None)
            self.__zimopai = data['tile']
        else:
            if data['tile'] != '':
                raise ValueError(
                    f"data['seat'] = {data['seat']}, "
                    f"data['tile'] = {data['tile']}")
            if 'operation' in data:
                raise ValueError('')

        if len(data['doras']) > 0:
            # 新ドラを表示する．
            self.__dora_indicators = data['doras']
        self.__left_tile_count = data['left_tile_count']

        if 'liqi' in data:
            liqi = data['liqi']
            self.__scores[liqi['seat']] = liqi['score']
            self.__liqibang += 1

        self.__prev_dapai_seat = None
        self.__prev_dapai = None

    def _on_dapai(self, data: object) -> None:
        assert(self.__prev_dapai_seat is None)
        assert(self.__prev_dapai is None)

        seat = data['seat']

        if seat == self.__match_state.seat:
            if data['moqie']:
                assert(self.__zimopai is not None)
                assert(self.__zimopai == data['tile'])
                self.__zimopai = None
            else:
                # 手出し．
                for i, tile in enumerate(self.__shoupai):
                    if tile == data['tile']:
                        break
                assert(i < len(self.__shoupai))
                self.__shoupai.pop(i)
                if self.__zimopai is not None:
                    # 自摸牌を手牌に組み入れる．
                    self.__hand_in()
            assert('operation' not in data)

        if len(data['doras']) > 0:
            # 新ドラを表示する．
            self.__dora_indicators = data['doras']

        self.__he[seat].append((data['tile'], data['moqie']))

        if data['is_liqi']:
            self.__liqi[seat] = True
            self.__yifa[seat] = True
        elif data['is_wliqi']:
            self.__wliqi[seat] = True
            self.__yifa[seat] = True
        else:
            self.__yifa[seat] = False
        self.__first_draw[seat] = False
        self.__lingshang_zimo[seat] = False

        self.__prev_dapai_seat = seat
        self.__prev_dapai = data['tile']

    def _on_chipenggang(self, data: object) -> None:
        seat = data['seat']

        assert(self.__prev_dapai_seat is not None)
        assert(seat != self.__prev_dapai_seat)
        assert(self.__prev_dapai is not None)

        if seat == self.__match_state.seat:
            # 手牌から副露牌を抜く．
            for tile in data['tiles'][:-1]:
                for i, t in enumerate(self.__shoupai):
                    if t == tile:
                        break
                assert(i < len(self.__shoupai))
                self.__shoupai.pop(i)

        assert(self.__zimopai is None)

        type_ = ('チー', 'ポン', '大明槓')[data['type']]
        from_ = data['froms'][-1]
        he_index = len(self.__he[from_]) - 1
        self.__fulu[seat].append((type_, from_, he_index, data['tiles']))

        if 'liqi' in data:
            liqi = data['liqi']
            self.__scores[liqi['seat']] = liqi['score']
            self.__liqibang += 1

        self.__first_draw = [False] * 4
        self.__yifa = [False] * 4
        if type_ == '大明槓':
            self.__lingshang_zimo[seat] = True

        self.__prev_dapai_seat = None
        self.__prev_dapai = None

        assert(seat == self.__match_state.seat or 'operation' not in data)

    def _on_angang_jiagang(self, data: object) -> None:
        assert(self.__prev_dapai_seat is None)
        assert(self.__prev_dapai is None)

        seat = data['seat']

        assert(
            (seat == self.__match_state.seat) == (self.__zimopai is not None))

        if seat == self.__match_state.seat:
            # 手牌もしくは自摸牌から副露牌を抜く．
            if data['tiles'] in ('0m', '5m',):
                tiles = ('0m', '5m',)
            elif data['tiles'] in ('0p', '5p',):
                tiles = ('0p', '5p',)
            elif data['tiles'] in ('0s', '5s',):
                tiles = ('0s', '5s',)
            else:
                tiles = (data['tiles'],)
            count = 0
            i = 0
            while i < len(self.__shoupai):
                tile = self.__shoupai[i]
                if tile in tiles:
                    self.__shoupai.pop(i)
                    count += 1
                    continue
                i += 1
            if data['type'] == 2:
                # 加槓の場合
                if count != 1:
                    if count != 0:
                        raise InconsistentMessage('An inconsistent message')
                    if self.__zimopai is None:
                        raise InconsistentMessage('An inconsistent message')
                    if self.__zimopai not in tiles:
                        raise InconsistentMessage('An inconsistent message')
                    self.__zimopai = None
                    count += 1
                assert(count == 1)
            elif data['type'] == 3:
                # 暗槓の場合
                if count != 4:
                    if count != 3:
                        raise InconsistentMessage('An inconsistent message')
                    if self.__zimopai is None:
                        raise InconsistentMessage('An inconsistent message')
                    if self.__zimopai not in tiles:
                        raise InconsistentMessage('An inconsistent message')
                    self.__zimopai = None
                    count += 1
                assert(count == 4)

            if self.__zimopai is not None:
                # 自摸牌を手牌に組み入れる．
                self.__hand_in()

        assert(data['type'] in (2, 3))
        type_ = (None, None, '加槓', '暗槓')[data['type']]
        if data['type'] == 2:
            # 加槓の場合，既存のポンを加槓に置き換える．
            for i, fulu in enumerate(self.__fulu[seat]):
                if fulu[3] == data['tiles'][:-1]:
                    break
            assert(i < len(self.__fulu[seat]))
            from_ = self.__fulu[seat][i][1]
            he_index = self.__fulu[seat][i][2]
            self.__fulu[seat][i] = (type_, from_, he_index, data['tiles'])
        else:
            # 暗槓の場合．
            self.__fulu[seat].append((type_, None, None, data['tiles']))

        if len(data['doras']) > 0:
            # 新ドラを表示する．
            self.__dora_indicators = data['doras']

        self.__first_draw = [False] * 4
        self.__yifa = [False] * 4
        self.__lingshang_zimo[seat] = True

        # 槍槓があるので暗槓・加槓は捨て牌とみなす．
        self.__prev_dapai_seat = seat
        self.__prev_dapai = data['tiles'][-1]

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
        assert(self.__left_tile_count >= 0)
        assert(self.__left_tile_count < 70)
        return self.__left_tile_count

    @property
    def scores(self) -> List[int]:
        assert(len(self.__scores) in (4, 3))
        return self.__scores

    @property
    def shoupai(self) -> List[str]:
        return self.__shoupai

    @property
    def zimopai(self) -> Optional[str]:
        return self.__zimopai

    @property
    def he(self) -> List[List[Tuple[str, bool]]]:
        assert(len(self.__he) in (4, 3))
        for he_ in self.__he:
            assert(len(he_) <= 24)
        return self.__he

    @property
    def fulu(self) -> List[List[Tuple[str, Optional[int], Optional[int], List[str]]]]:
        assert(len(self.__fulu) in (4, 3))
        for fulu_ in self.__fulu:
            for type_, from_, he_index, tiles in fulu_:
                assert(type_ in ('チー', 'ポン', '大明槓', '暗槓', '加槓'))
                assert(from_ != self.__match_state.seat)
                assert(from_ >= 0)
                assert(from_ < 4)
                assert(he_index < len(self.__fulu[from_]))
                assert(type_ not in ('チー', 'ポン') or len(tiles) == 3)
                assert(
                    type_ not in ('大明槓', '暗槓', '加槓') or len(tiles) == 4)
        return self.__fulu

    @property
    def liqi(self) -> List[bool]:
        assert(len(self.__liqi) in (4, 3))
        assert(len(self.__liqi) == len(self.__wliqi))
        for i in range(len(self.__liqi)):
            assert(not (self.__liqi[i] and self.__wliqi[i]))
        return self.__liqi

    @property
    def wliqi(self) -> List[bool]:
        assert(len(self.__wliqi) in (4, 3))
        assert(len(self.__wliqi) == len(self.__liqi))
        for i in range(len(self.__wliqi)):
            assert(not (self.__liqi[i] and self.__wliqi[i]))
        return self.__wliqi

    @property
    def first_draw(self) -> List[bool]:
        assert(len(self.__first_draw) in (4, 3))
        return self.__first_draw

    @property
    def yifa(self) -> List[bool]:
        assert(len(self.__yifa) in (4, 3))
        return self.__yifa

    @property
    def lingshang_zimo(self) -> List[bool]:
        assert(len(self.__lingshang_zimo) in (4, 3))
        return self.__lingshang_zimo

    @property
    def prev_dapai_seat(self) -> Optional[int]:
        return self.__prev_dapai_seat

    @property
    def prev_dapai(self) -> Optional[str]:
        return self.__prev_dapai
