#!/usr/bin/env python3

import datetime
import time
import logging
from typing import (Optional, Tuple, List,)
from PIL.Image import Image
from majsoul_rpa.common import TimeoutType
from majsoul_rpa._impl import (Redis, BrowserBase, Template,)
from majsoul_rpa import common
from majsoul_rpa.presentation.presentation_base import (
    Timeout, InconsistentMessage, PresentationNotDetected, InvalidOperation,
    PresentationBase,)
import majsoul_rpa.presentation.match._common as _common
from majsoul_rpa.presentation.match.event import (
    NewRoundEvent, ZimoEvent, DapaiEvent, ChiPengGangEvent, AngangJiagangEvent,
    HuleEvent, NoTileEvent, LiujuEvent)
from majsoul_rpa.presentation.match.state import (
    MatchPlayer, MatchState, RoundState,)
from majsoul_rpa.presentation.match.operation import(
    DapaiOperation, ChiOperation, PengOperation, AngangOperation,
    DaminggangOperation, JiagangOperation, LiqiOperation, ZimohuOperation,
    RongOperation, JiuzhongjiupaiOperation, OperationList,)


class MatchPresentation(PresentationBase):
    @staticmethod
    def _wait(browser: BrowserBase, timeout: TimeoutType=60.0) -> None:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                raise Timeout('Timeout.', browser.get_screenshot())
            templates = [f'template/match/marker{i}' for i in range(4)]
            if Template.match_one_of(browser.get_screenshot(), templates) != -1:
                break

    def __init__(
        self, prev_presentation: PresentationBase, screenshot: Image,
        redis: Redis, timeout: TimeoutType=60.0,
        *, match_state: MatchState=MatchState()) -> None:
        super(MatchPresentation, self).__init__(redis)

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)

        self.__prev_presentation = prev_presentation
        self.__step = 0
        self.__events = []
        self.__match_state = match_state
        self.__round_state = None
        self.__operation_list = None

        templates = [f'template/match/marker{i}' for i in range(4)]
        if Template.match_one_of(screenshot, templates) == -1:
            if True:
                # For postmortem.
                now = datetime.datetime.now(datetime.timezone.utc)
                screenshot.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
            raise PresentationNotDetected(
                'Could not detect `match_main`.', screenshot)

        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = self._get_redis().dequeue_message(deadline - now)
            direction, name, request, response, timestamp = message

            if name == '.lq.Lobby.modifyRoom':
                continue

            if name == '.lq.NotifyRoomGameStart':
                uuid = request['game_uuid']
                self.__match_state._set_uuid(uuid)
                continue

            if name == '.lq.Lobby.startRoom':
                continue

            if name == '.lq.FastTest.authGame':
                uuid = request['game_uuid']
                self.__match_state._set_uuid(uuid)

                # TODO: ゲーム設定の確認

                player_map = {}
                for p in response['players']:
                    account_id = p['account_id']
                    nickname = p['nickname']
                    level4 = common.id2level(p['level']['id'])
                    level3 = common.id2level(p['level3']['id'])
                    charid = p['character']['charid']
                    try:
                        character = common.id2character(charid)
                    except KeyError as e:
                        # キャラクタ ID が不明なキャラクタと遭遇した場合
                        logging.warning(
                            f'{uuid}: {nickname}: charid = {charid}')
                        character = 'UNKNOWN'
                    player_map[account_id] = MatchPlayer(
                        account_id, nickname, level4, level3, character)
                players = []
                for i in range(4):
                    account_id = response['seat_list'][i]
                    if account_id == redis.get_account_id():
                        self.__match_state._set_seat(i)
                    if account_id == 0:
                        player = MatchPlayer(
                            0, 'CPU', '初心1', '初心1', '一姫')
                        players.append(player)
                    else:
                        players.append(player_map[account_id])
                self.__match_state._set_players(players)
                continue

            if name == '.lq.FastTest.enterGame':
                # TODO: 中断した対戦の再開処理？
                continue

            if name == '.lq.NotifyPlayerLoadGameReady':
                continue

            if name == '.lq.ActionPrototype':
                step, action_name, data = _common.parse_action(request)
                if step != self.__step:
                    raise InconsistentMessage(
                        'An inconsistent message.', self.screenshot)
                self.__step += 1

                if action_name == 'ActionMJStart':
                    continue

                if action_name == 'ActionNewRound':
                    self.__events.append(NewRoundEvent(data, timestamp))
                    self.__round_state = RoundState(self.__match_state, data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                raise InconsistentMessage(f'''An inconsistent action:
step: {step}
name: {action_name}
action: {data}''', screenshot)

            if name == '.lq.Lobby.heatbeat':
                continue

            if name == '.lq.NotifyReviveCoinUpdate':
                # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                continue

            if name == '.lq.NotifyGiftSendRefresh':
                # 同上．
                continue

            if name == '.lq.NotifyDailyTaskUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyShopUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyAccountChallengeTaskUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyAnnouncementUpdate':
                # 告知の更新があった場合．
                continue

            if name == '.lq.FastTest.authGame':
                # ゲーム中にまれにやり取りされる．
                continue

            if name == '.lq.FastTest.checkNetworkDelay':
                continue

            if name == '.lq.FastTest.fetchGamePlayerState':
                # TODO: 各プレイヤの接続状態の確認
                continue

            if name == '.lq.NotifyPlayerConnectionState':
                # TODO: 各プレイヤの接続状態の確認
                continue

            if name == '.lq.NotifyGameBroadcast':
                # TODO: スタンプその他の処理
                continue

            if name == '.lq.PlayerLeaving':
                # TODO: 離席判定をくらった場合の対処
                continue

            raise InconsistentMessage(f'''An inconsistent message:
direction: {direction}
name: {name}
request: {request}
response: {response}
timestamp: {timestamp}''', screenshot)

    @property
    def uuid(self) -> str:
        return self.__match_state.uuid

    @property
    def seat(self) -> int:
        return self.__match_state.seat

    @property
    def players(self) -> List[MatchPlayer]:
        return self.__match_state.players

    @property
    def chang(self) -> int:
        return self.__round_state.chang

    @property
    def ju(self) -> int:
        return self.__round_state.ju

    @property
    def ben(self) -> int:
        return self.__round_state.ben

    @property
    def liqibang(self) -> int:
        return self.__round_state.liqibang

    @property
    def dora_indicators(self) -> List[str]:
        return self.__round_state.dora_indicators

    @property
    def left_tile_count(self) -> int:
        return self.__round_state.left_tile_count

    @property
    def scores(self) -> List[int]:
        return self.__round_state.scores

    @property
    def shoupai(self) -> List[str]:
        return self.__round_state.shoupai

    @property
    def zimopai(self) -> Optional[str]:
        return self.__round_state.zimopai

    @property
    def he(self) -> List[List[Tuple[str, bool]]]:
        return self.__round_state.he

    @property
    def fulu(self) -> List[List[Tuple[str, Optional[int], Optional[int], List[str]]]]:
        return self.__round_state.fulu

    @property
    def liqi(self) -> List[bool]:
        return self.__round_state.liqi

    @property
    def wliqi(self) -> List[bool]:
        return self.__round_state.wliqi

    @property
    def first_draw(self) -> bool:
        return self.__round_state.__first_draw[self.seat]

    @property
    def yifa(self) -> List[bool]:
        return self.__round_state.__yifa

    @property
    def lingshang_zimo(self) -> bool:
        return self.__round_state.lingshang_zimo[self.seat]

    @property
    def prev_dapai_seat(self) -> Optional[int]:
        return self.__round_state.prev_dapai_seat

    @property
    def prev_dapai(self) -> Optional[int]:
        return self.__round_state.prev_dapai

    @property
    def operation_list(self) -> Optional[OperationList]:
        return self.__operation_list

    @property
    def events(self) -> List[object]:
        return self.__events

    def __robust_click_region(
        self, rpa, left: int, top: int, width: int, height: int,
        interval: TimeoutType, timeout: Timeout, edge_sigma: float=2.0,
        warp: bool=False) -> None:
        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if isinstance(interval, (int, float,)):
            interval = datetime.timedelta(seconds=interval)

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)

        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                raise Timeout('Timeout', rpa.get_screenshot())

            rpa._click_region(
                left, top, width, height, edge_sigma=edge_sigma, warp=warp)
            message = rpa._get_redis().dequeue_message(interval)
            if message is None:
                continue
            direction, name, request, response, timestamp = message

            if name == '.lq.Lobby.heatbeat':
                continue

            if name == '.lq.NotifyReviveCoinUpdate':
                # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                continue

            if name == '.lq.NotifyGiftSendRefresh':
                # 同上．
                continue

            if name == '.lq.NotifyDailyTaskUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyShopUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyAccountChallengeTaskUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyAnnouncementUpdate':
                # 告知の更新があった場合．
                continue

            if name == '.lq.FastTest.authGame':
                # ゲーム中にまれにやり取りされる．
                continue

            if name == '.lq.FastTest.checkNetworkDelay':
                continue

            if name == '.lq.FastTest.fetchGamePlayerState':
                # TODO: 各プレイヤの接続状態の確認．
                continue

            if name == '.lq.NotifyPlayerConnectionState':
                # TODO: 各プレイヤの接続状態の確認
                continue

            if name == '.lq.NotifyGameBroadcast':
                # TODO: スタンプその他の処理
                continue

            if name == '.lq.PlayerLeaving':
                # TODO: 離席判定をくらった場合の対処
                continue

            if name == '.lq.FastTest.inputOperation':
                break

            if name == '.lq.FastTest.inputChiPengGang':
                break

            if name == '.lq.ActionPrototype':
                break

        rpa._get_redis().put_back(message)

    def __on_end_of_match(self, rpa, deadline: datetime.datetime) -> None:
        from majsoul_rpa import RPA
        rpa: RPA = rpa

        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            if now > deadline:
                raise Timeout('Timeout.', rpa.get_screenshot())

            message = self._get_redis().dequeue_message()
            if message is None:
                raise InconsistentMessage(
                    'Unexpected message order', rpa.get_screenshot())
            direction, name, request, response, timestamp = message

            if name == '.lq.Lobby.heatbeat':
                continue

            if name == '.lq.NotifyReviveCoinUpdate':
                # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                logging.info(message)
                continue

            if name == '.lq.NotifyGiftSendRefresh':
                # 同上．
                logging.info(message)
                continue

            if name == '.lq.NotifyDailyTaskUpdate':
                # 同上．
                logging.info(message)
                continue

            if name == '.lq.NotifyShopUpdate':
                # 同上．
                logging.info(message)
                continue

            if name == '.lq.NotifyAccountChallengeTaskUpdate':
                # 同上．
                logging.info(message)
                continue

            if name == '.lq.NotifyAnnouncementUpdate':
                # 告知の更新があった場合．
                logging.info(message)
                continue

            if name == '.lq.FastTest.authGame':
                # ゲーム中にまれにやり取りされる．
                logging.info(message)
                continue

            if name == '.lq.FastTest.checkNetworkDelay':
                continue

            if name == '.lq.Lobby.fetchAccountInfo':
                # TODO: メッセージ内容の処理．
                # イベント中のみ？
                logging.info(message)
                continue

            if name == '.lq.NotifyAccountUpdate':
                # TODO: メッセージ内容の処理．
                logging.info(message)
                continue

            if name == '.lq.NotifyGameFinishReward':
                # TODO: メッセージ内容の処理．
                logging.info(message)
                continue

            if name == '.lq.NotifyActivityReward':
                # TODO: メッセージ内容の処理．
                logging.info(message)
                continue

            if name == '.lq.NotifyActivityPoint':
                # TODO: メッセージ内容の処理．
                logging.info(message)
                continue

            if name == '.lq.NotifyLeaderboardPoint':
                # TODO: メッセージ内容の処理．
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchRoom':
                # 先読みしたメッセージの埋め戻し
                self._get_redis().put_back(message)

                # 報酬取得時などの追加の「確認」ボタンがあればクリックする．
                template = Template.open('template/match/match_result_confirm')
                while True:
                    if datetime.datetime.now(datetime.timezone.utc) > deadline:
                        raise Timeout('Timeout', rpa.get_screenshot())
                    try:
                        template.wait_for_then_click(rpa._get_browser(), 5.0)
                    except Timeout as e:
                        break

                from majsoul_rpa.presentation.room.host import RoomHostPresentation
                if isinstance(self.__prev_presentation, RoomHostPresentation):
                    now = datetime.datetime.now(datetime.timezone.utc)
                    p = RoomHostPresentation._return_from_match(
                        rpa._get_browser(), rpa._get_redis(),
                        self.__prev_presentation, deadline - now)
                    self._set_new_presentation(p)
                    return

                raise NotImplementedError(type(self.__prev_presentation))
                return

            raise InconsistentMessage(message, rpa.get_screenshot())

    def __on_end_of_round(self, rpa, deadline: datetime.datetime) -> None:
        from majsoul_rpa import RPA
        rpa: RPA = rpa

        template = Template.open('template/match/round_result_confirm')
        template.wait_until_then_click(rpa._get_browser(), deadline)
        time.sleep(1.0)

        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                raise Timeout('Timeout.', rpa.get_screenshot())

            message = self._get_redis().dequeue_message()
            if message is None:
                raise InconsistentMessage(
                    'Unexpected message order', rpa.get_screenshot())
            direction, name, request, response, timestamp = message

            if name == '.lq.Lobby.heatbeat':
                continue

            if name == '.lq.NotifyReviveCoinUpdate':
                # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                continue

            if name == '.lq.NotifyGiftSendRefresh':
                # 同上．
                continue

            if name == '.lq.NotifyDailyTaskUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyShopUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyAccountChallengeTaskUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyAnnouncementUpdate':
                # 告知の更新があった場合．
                continue

            if name == '.lq.FastTest.authGame':
                # ゲーム中にまれにやり取りされる．
                continue

            if name == '.lq.FastTest.checkNetworkDelay':
                continue

            if name == '.lq.NotifyActivityChange':
                # TODO: メッセージ内容の解析
                continue

            if name == '.lq.FastTest.confirmNewRound':
                # 対局終了時 (次局がある場合)
                while True:
                    # `ActionNewRound` メッセージを待つ．
                    if datetime.datetime.now(datetime.timezone.utc) > deadline:
                        raise Timeout('Timeout', rpa.get_screenshot())
                    now = datetime.datetime.now(datetime.timezone.utc)
                    message = rpa._get_redis().dequeue_message(deadline - now)
                    if message is None:
                        continue
                    direction, name, request, response, timestamp = message
                    if name == '.lq.Lobby.heatbeat':
                        continue
                    if name == '.lq.NotifyReviveCoinUpdate':
                        # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                        continue
                    if name == '.lq.NotifyGiftSendRefresh':
                        # 同上．
                        continue
                    if name == '.lq.NotifyDailyTaskUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyShopUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyAccountChallengeTaskUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyAnnouncementUpdate':
                        # 告知の更新があった場合．
                        continue
                    if name == '.lq.FastTest.authGame':
                        # ゲーム中にまれにやり取りされる．
                        continue
                    if name == '.lq.FastTest.checkNetworkDelay':
                        continue
                    if name == '.lq.FastTest.fetchGamePlayerState':
                        # TODO: 各プレイヤの接続状態の確認
                        continue
                    if name == '.lq.NotifyPlayerConnectionState':
                        # TODO: 各プレイヤの接続状態の確認
                        continue
                    if name == '.lq.NotifyGameBroadcast':
                        # TODO: スタンプその他の処理
                        continue
                    if name == '.lq.PlayerLeaving':
                        # TODO: 離席判定をくらった場合の対処
                        continue
                    if name == '.lq.ActionPrototype':
                        step, action_name, data = _common.parse_action(request)
                        if action_name == 'ActionNewRound':
                            rpa._get_redis().put_back(message)
                            break
                        raise InconsistentMessage(message, rpa.get_screenshot())
                    raise InconsistentMessage(message, rpa.get_screenshot())

                now = datetime.datetime.now(datetime.timezone.utc)
                MatchPresentation._wait(rpa._get_browser(), deadline - now)
                now = datetime.datetime.now(datetime.timezone.utc)
                p = MatchPresentation(
                    self.__prev_presentation, rpa.get_screenshot(),
                    self._get_redis(), deadline - now,
                    match_state=self.__match_state)
                self._set_new_presentation(p)
                return

            if name == '.lq.ActionPrototype':
                # `.lq.FastTest.confirmNewRound` のレスポンスメッセージと
                # `ActionNewRound` メッセージの順序が逆転する場合があるので，
                # その場合に対する workaround.
                step, action_name, data = _common.parse_action(request)
                if action_name != 'ActionNewRound':
                    raise InconsistentMessage(message, rpa.get_screenshot())
                while True:
                    # `.lq.FastTest.confirmNewRound` のレスポンスメッセージを
                    # 待つ．
                    if datetime.datetime.now(datetime.timezone.utc) > deadline:
                        raise Timeout('Timeout', rpa.get_screenshot())
                    now = datetime.datetime.now(datetime.timezone.utc)
                    next_message = rpa._get_redis().dequeue_message(deadline - now)
                    if next_message is None:
                        continue
                    _, next_name, _, _, _ = next_message
                    if next_name == '.lq.Lobby.heatbeat':
                        continue
                    if next_name == '.lq.NotifyReviveCoinUpdate':
                        # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                        continue
                    if next_name == '.lq.NotifyGiftSendRefresh':
                        # 同上．
                        continue
                    if next_name == '.lq.NotifyDailyTaskUpdate':
                        # 同上．
                        continue
                    if next_name == '.lq.NotifyShopUpdate':
                        # 同上．
                        continue
                    if next_name == '.lq.NotifyAccountChallengeTaskUpdate':
                        # 同上．
                        continue
                    if next_name == '.lq.NotifyAnnouncementUpdate':
                        # 告知の更新があった場合．
                        continue
                    if next_name == '.lq.FastTest.authGame':
                        # ゲーム中にまれにやり取りされる．
                        continue
                    if next_name == '.lq.FastTest.checkNetworkDelay':
                        raise InconsistentMessage(
                            next_message, rpa.get_screenshot())
                    if next_name == '.lq.FastTest.fetchGamePlayerState':
                        # TODO: 各プレイヤの接続状態の確認
                        raise InconsistentMessage(
                            next_message, rpa.get_screenshot())
                    if next_name == '.lq.NotifyPlayerConnectionState':
                        # TODO: 各プレイヤの接続状態の確認
                        continue
                    if next_name == '.lq.NotifyGameBroadcast':
                        # TODO: スタンプその他の処理
                        continue
                    if next_name == '.lq.PlayerLeaving':
                        # TODO: 離席判定をくらった場合の対処
                        continue
                    if next_name == '.lq.ActionPrototype':
                        raise InconsistentMessage(
                            next_message, rpa.get_screenshot())
                    if next_name == '.lq.FastTest.confirmNewRound':
                        break
                    raise InconsistentMessage(
                        next_message, rpa.get_screenshot())
                rpa._get_redis().put_back(message)
                now = datetime.datetime.now(datetime.timezone.utc)
                MatchPresentation._wait(rpa._get_browser(), deadline - now)
                now = datetime.datetime.now(datetime.timezone.utc)
                p = MatchPresentation(
                    self.__prev_presentation, rpa.get_screenshot(),
                    self._get_redis(), deadline - now,
                    match_state=self.__match_state)
                self._set_new_presentation(p)
                return

            if name == '.lq.NotifyGameEndResult':
                # ゲーム終了時
                # TODO: メッセージ内容の処理．
                template = Template.open('template/match/match_result_confirm')
                template.wait_until_then_click(rpa._get_browser(), deadline)
                self.__on_end_of_match(rpa, deadline)
                return

            raise InconsistentMessage(message, rpa.get_screenshot())

    def _wait_impl(self, rpa, timeout: TimeoutType=300.0) -> None:
        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = self._get_redis().dequeue_message(deadline - now)
            direction, name, request, response, timestamp = message

            if name == '.lq.Lobby.heatbeat':
                continue

            if name == '.lq.NotifyReviveCoinUpdate':
                # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                continue

            if name == '.lq.NotifyGiftSendRefresh':
                # 同上．
                continue

            if name == '.lq.NotifyDailyTaskUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyShopUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyAccountChallengeTaskUpdate':
                # 同上．
                continue

            if name == '.lq.NotifyAnnouncementUpdate':
                # 告知の更新があった場合．
                continue

            if name == '.lq.FastTest.authGame':
                # ゲーム中にまれにやり取りされる．
                continue

            if name == '.lq.FastTest.checkNetworkDelay':
                continue

            if name == '.lq.FastTest.fetchGamePlayerState':
                # TODO: 各プレイヤの接続状態の確認．
                continue

            if name == '.lq.NotifyPlayerConnectionState':
                # TODO: 各プレイヤの接続状態の確認
                continue

            if name == '.lq.NotifyGameBroadcast':
                # TODO: スタンプその他の処理
                continue

            if name == '.lq.ActionPrototype':
                step, action_name, data = _common.parse_action(request)
                if step != self.__step:
                    raise InconsistentMessage(
                        'An inconsistent message.', rpa.get_screenshot())
                self.__step += 1

                if action_name == 'ActionMJStart':
                    raise InconsistentMessage(
                        'An inconsistent message.', rpa.get_screenshot())

                if action_name == 'ActionNewRound':
                    raise InconsistentMessage(
                        'An inconsistent message.', rpa.get_screenshot())

                if action_name == 'ActionDealTile':
                    self.__events.append(ZimoEvent(data, timestamp))
                    self.__round_state._on_zimo(data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                if action_name == 'ActionDiscardTile':
                    self.__events.append(DapaiEvent(data, timestamp))
                    self.__round_state._on_dapai(data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                if action_name == 'ActionChiPengGang':
                    self.__events.append(ChiPengGangEvent(data, timestamp))
                    self.__round_state._on_chipenggang(data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                if action_name == 'ActionAnGangAddGang':
                    self.__events.append(AngangJiagangEvent(data, timestamp))
                    self.__round_state._on_angang_jiagang(data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                if action_name == 'ActionHule':
                    self.__events.append(HuleEvent(data, timestamp))

                    template = Template.open('template/match/hule_confirm')
                    for i in range(len(data['hules'])):
                        template.wait_until_then_click(
                            rpa._get_browser(), deadline)

                    self.__on_end_of_round(rpa, deadline)
                    return

                if action_name == 'ActionNoTile':
                    self.__events.append(NoTileEvent(data, timestamp))

                    template = Template.open('template/match/no_tile_confirm')
                    template.wait_until_then_click(rpa._get_browser(), deadline)

                    if data['liujumanguan']:
                        # 流し満貫達成者が居る場合．
                        # 流し満貫達成者が居る場合，和了と同じ演出があるので，
                        # それに対する「確認」ボタンをクリックする必要がある．
                        template = Template.open('template/match/hule_confirm')
                        for i in range(len(data['scores'])):
                            template.wait_until_then_click(
                                rpa._get_browser(), deadline)

                    self.__on_end_of_round(rpa, deadline)
                    return

                if action_name == 'ActionLiuJu':
                    self.__events.append(LiujuEvent(data, timestamp))

                    self.__on_end_of_round(rpa, deadline)
                    return

            if name == '.lq.FastTest.inputOperation':
                continue

            if name == '.lq.FastTest.inputChiPengGang':
                continue

            if name == '.lq.PlayerLeaving':
                # TODO: 離席判定をくらった場合の対処
                continue

            raise InconsistentMessage(f'''An inconsistent message:
direction: {direction}
name: {name}
request: {request}
response: {response}
timestamp: {timestamp}''', rpa.get_screenshot())

    def wait(self, rpa, timeout: TimeoutType=300.0):
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if self.__operation_list is not None:
            raise InvalidOperation(
                'Must select an operation.', rpa.get_screenshot())
        return self._wait_impl(rpa, timeout)

    def __dapai(self, rpa, index: int, forbidden_tiles: List[str]) -> None:
        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if index is None:
            raise InvalidOperation(
                'Must specify an index for dapai.', rpa.get_screenshot())
        num_tiles = len(self.__round_state.shoupai)
        num_tiles += 0 if (self.__round_state.zimopai is None) else 1
        if index >= num_tiles:
            raise InvalidOperation(
                'Out of index for dapai.', rpa.get_screenshot())

        if self.zimopai is None:
            # 副露直後の打牌で食い替えできない牌を
            # 切ろうとしていないかを確認する．
            if self.shoupai[index] in forbidden_tiles:
                raise InvalidOperation(
                    'An invalid operation.', rpa.get_screenshot())

        if (self.zimopai is not None) and index == num_tiles - 1:
            # 自摸切り
            if index == 13:
                left = 1487
                top = 922
                width = 89
                height = 149
            elif index == 10:
                left = 1203
                top = 922
                width = 89
                height = 149
            elif index == 7:
                left = 918
                top = 922
                width = 89
                height = 149
            elif index == 4:
                left = 633
                top = 922
                width = 90
                height = 149
            elif index == 1:
                left = 224
                top = 922
                width = 89
                height = 149
        else:
            # 手出し
            # 手牌の座標
            left = round(224 + index * 94.91)
            top = 922
            width = round(312 + index * 94.91) - left + 1
            height = 149

        # 牌の1割内側をクリックする．
        # （牌の外周ぎりぎりは隣の牌を触りうるため）
        left += round(width * 0.1)
        top += round(height * 0.1)
        width = round(width * 0.8)
        height = round(height * 0.7) # `height * 0.8` ではクリックに失敗する．
        self.__robust_click_region(
            rpa, left, top, width, height, interval=1.0, timeout=5.0,
            edge_sigma=1.0, warp=False)

    def select_operation(
        self, rpa, operation, index: Optional[int]=None,
        timeout: TimeoutType=300.0) -> None:
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        if self.__operation_list is None:
            raise InvalidOperation(
                'No operation exists for now.', rpa.get_screenshot())

        if operation is not None:
            operation_exists = False
            operation_type = type(operation)
            for op in self.__operation_list:
                if isinstance(op, operation_type):
                    operation = op
                    operation_exists = True
                    break
            if not operation_exists:
                raise InvalidOperation(
                    'An invalid operation.', rpa.get_screenshot())

        if operation is None:
            # 選択肢をスキップする．ラグ読みされるのを防ぐため，スキップの
            # UI 操作は可能な限り短時間で行う必要がある．この目的を
            # 達成するために以下の工夫を行う．
            #
            #   * 上家以外の打牌に対するチー・ポン・カン・ロンをスキップする
            #     場合は，「スキップ」のボタンが出現してくる場所を（ボタンが
            #     出現するタイミング以前から）連打する．
            #   * 上家の打牌に対するチー・ポン・カン・ロンをスキップする
            #     場合は，「鳴き無し」ボタンをクリックすることにより
            #     スキップする（選択肢が出た後でも「鳴き無し」ボタンを
            #     クリックすると「スキップ」ボタンをクリックしたのと同じ
            #     効果がある）．上家の打牌に対するスキップをこのような
            #     特殊な操作で行う理由は，仮に上家の打牌に対するスキップを
            #     前項と同じ方法（「スキップ」ボタンの連打）で行うと，自身の
            #     自摸に対する選択肢（立直・ツモ・カン）もスキップしてしまう
            #     場合があるためである．
            skip_by_melding_off = False
            for o in self.__operation_list:
                if isinstance(o, (ChiOperation, PengOperation, DaminggangOperation, RongOperation,)):
                    assert(self.prev_dapai_seat is not None)
                    if (self.seat + 4 - self.prev_dapai_seat) % 4 == 1:
                        skip_by_melding_off = True

            if skip_by_melding_off:
                # 上家の打牌に対する選択肢を「鳴き無し」ボタンを
                # クリックすることでスキップする．スキップできたら再度
                # 「鳴き無し」ボタンをクリックして鳴きができる状態に戻す．
                rpa._click_region(14, 610, 43, 44, edge_sigma=1.0, warp=True)
                while True:
                    if datetime.datetime.now(datetime.timezone.utc) > deadline:
                        raise Timeout('Timeout', rpa.get_screenshot())
                    message = rpa._get_redis().dequeue_message(0.0)
                    if message is None:
                        continue
                    direction, name, request, response, timestamp = message
                    if name == '.lq.Lobby.heatbeat':
                        continue
                    if name == '.lq.NotifyReviveCoinUpdate':
                        # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                        continue
                    if name == '.lq.NotifyGiftSendRefresh':
                        # 同上．
                        continue
                    if name == '.lq.NotifyDailyTaskUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyShopUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyAccountChallengeTaskUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyAnnouncementUpdate':
                        # 告知の更新があった場合．
                        continue
                    if name == '.lq.FastTest.authGame':
                        # ゲーム中にまれにやり取りされる．
                        continue
                    if name == '.lq.FastTest.checkNetworkDelay':
                        continue
                    if name == '.lq.FastTest.fetchGamePlayerState':
                        # TODO: 各プレイヤの接続状態の確認．
                        continue
                    if name == '.lq.NotifyPlayerConnectionState':
                        # TODO: 各プレイヤの接続状態の確認
                        continue
                    if name == '.lq.NotifyGameBroadcast':
                        # TODO: スタンプその他の処理
                        continue
                    if name == '.lq.PlayerLeaving':
                        # TODO: 離席判定をくらった場合の対処
                        continue
                    if name == '.lq.FastTest.inputOperation':
                        raise InconsistentMessage(message, rpa.get_screenshot())
                    if name == '.lq.FastTest.inputChiPengGang':
                        break
                    if name == '.lq.ActionPrototype':
                        break
                rpa._get_redis().put_back(message)
                rpa._click_region(14, 610, 43, 44, edge_sigma=1.0)
            else:
                # 上家以外の打牌に対する選択肢を「スキップ」ボタンを
                # 連打することでスキップする．「スキップ」ボタンの
                # template の region は以下でコメントアウトしている範囲だが，
                # 選択肢が少し右からスクロールインしてくる形で
                # 表示されるため，以下の region の左側をあまりに早く
                # クリックすると「スキップ」以外のボタンがクリックされる
                # 可能性がある．そのため，クリックする region を若干右側に
                # 限定している．
                #self.__robust_click_region(
                #    rpa, 1227, 811, 164, 50, interval=0.2, timeout=5.0,
                #    edge_sigma=1.0, warp=True)
                self.__robust_click_region(
                    rpa, 1309, 811, 82, 50, interval=0.2, timeout=5.0,
                    edge_sigma=1.0, warp=True)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, DapaiOperation):
            # 打牌
            self.__dapai(rpa, index, operation.forbidden_tiles)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, ChiOperation):
            templates = tuple(
                Template.open(f'template/match/chi{i}') for i in range(2))
            try:
                # `timeout` を短めに設定しておかないと，他家の栄和に
                # 邪魔された際に和了画面に反応できなくなる．
                Template.wait_for_one_of_then_click(
                    templates, rpa._get_browser(), timeout=5.0)
            except Timeout as e:
                # 他家のポン，槓もしくは栄和に邪魔された可能性がある．
                while True:
                    if datetime.datetime.now(datetime.timezone.utc) > deadline:
                        ss = rpa.get_screenshot()
                        now = datetime.datetime.now(datetime.timezone.utc)
                        ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                        raise NotImplementedError
                    message = rpa._get_redis().dequeue_message()
                    if message is None:
                        ss = rpa.get_screenshot()
                        now = datetime.datetime.now(datetime.timezone.utc)
                        ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                        raise NotImplementedError
                    direction, name, request, response, timestamp = message
                    if name == '.lq.Lobby.heatbeat':
                        continue
                    if name == '.lq.NotifyReviveCoinUpdate':
                        # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                        continue
                    if name == '.lq.NotifyGiftSendRefresh':
                        # 同上．
                        continue
                    if name == '.lq.NotifyDailyTaskUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyShopUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyAccountChallengeTaskUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyAnnouncementUpdate':
                        # 告知の更新があった場合．
                        continue
                    if name == '.lq.FastTest.authGame':
                        # ゲーム中にまれにやり取りされる．
                        continue
                    if name == '.lq.FastTest.checkNetworkDelay':
                        continue
                    if name == '.lq.FastTest.fetchGamePlayerState':
                        # TODO: 各プレイヤの接続状態の確認．
                        continue
                    if name == '.lq.NotifyPlayerConnectionState':
                        # TODO: 各プレイヤの接続状態の確認
                        continue
                    if name == '.lq.NotifyGameBroadcast':
                        # TODO: スタンプその他の処理
                        continue
                    if name == '.lq.PlayerLeaving':
                        # TODO: 離席判定をくらった場合の対処
                        continue
                    if name == '.lq.ActionPrototype':
                        step, action_name, data = _common.parse_action(request)
                        if action_name in ('ActionChiPengGang', 'ActionHule',):
                            # 他家のポン，槓もしくは栄和に邪魔されていた．
                            rpa._get_redis().put_back(message)
                            self.__operation_list = None
                            now = datetime.datetime.now(datetime.timezone.utc)
                            self._wait_impl(rpa, deadline - now)
                            return
                        ss = rpa.get_screenshot()
                        now = datetime.datetime.now(datetime.timezone.utc)
                        ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                        raise InconsistentMessage(message, rpa.get_screenshot())
                    if name == '.lq.FastTest.inputOperation':
                        raise InconsistentMessage(message, rpa.get_screenshot())
                    if name == '.lq.FastTest.inputChiPengGang':
                        raise InconsistentMessage(message, rpa.get_screenshot())
                    raise InconsistentMessage(message, rpa.get_screenshot())
            if len(operation.combinations) >= 2:
                if index is None:
                    raise InvalidOperation(
                        'Must specify an index.', rpa.get_screenshot())
                if len(operation.combinations) == 2:
                    if index == 0:
                        left = 780
                    elif index == 1:
                        left = 980
                    else:
                        raise InvalidOperation(
                            f'{index}: out-of-range index', rpa.get_screenshot())
                elif len(operation.combinations) == 3:
                    if index == 0:
                        left = 680
                    elif index == 1:
                        left = 880
                    elif index == 2:
                        left = 1080
                    else:
                        raise InvalidOperation(
                            f'{index}: out-of-range index', rpa.get_screenshot())
                elif len(operation.combinations) == 4:
                    if index == 0:
                        left = 580
                    elif index == 1:
                        left = 780
                    elif index == 2:
                        left = 980
                    elif index == 3:
                        left = 1180
                    else:
                        raise InvalidOperation(
                            f'{index}: out-of-range index', rpa.get_screenshot())
                elif len(operation.combinations) == 5:
                    if index == 0:
                        left = 480
                    elif index == 1:
                        left = 680
                    elif index == 2:
                        left = 880
                    elif index == 3:
                        left = 1080
                    elif index == 4:
                        left = 1280
                    else:
                        raise InvalidOperation(
                            f'{index}: out-of-range index', rpa.get_screenshot())
                else:
                    ss = rpa.get_screenshot()
                    now = datetime.datetime.now(datetime.timezone.utc)
                    ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                    raise AssertionError(len(operation.combinations))
                rpa._click_region(left, 691, 160, 120)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, PengOperation):
            templates = tuple(
                Template.open(f'template/match/peng{i}') for i in range(2))
            try:
                # `timeout` を短めに設定しておかないと，他家の栄和に
                # 邪魔された際に和了画面に反応できなくなる．
                Template.wait_for_one_of_then_click(
                    templates, rpa._get_browser(), timeout=5.0)
            except Timeout as e:
                # TODO: 他家の栄和に邪魔された可能性がある．
                while True:
                    if datetime.datetime.now(datetime.timezone.utc) > deadline:
                        ss = rpa.get_screenshot()
                        now = datetime.datetime.now(datetime.timezone.utc)
                        ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                        raise NotImplementedError
                    message = rpa._get_redis().dequeue_message()
                    if message is None:
                        ss = rpa.get_screenshot()
                        now = datetime.datetime.now(datetime.timezone.utc)
                        ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                        raise NotImplementedError
                    direction, name, request, response, timestamp = message
                    if name == '.lq.Lobby.heatbeat':
                        continue
                    if name == '.lq.NotifyReviveCoinUpdate':
                        # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
                        continue
                    if name == '.lq.NotifyGiftSendRefresh':
                        # 同上．
                        continue
                    if name == '.lq.NotifyDailyTaskUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyShopUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyAccountChallengeTaskUpdate':
                        # 同上．
                        continue
                    if name == '.lq.NotifyAnnouncementUpdate':
                        # 告知の更新があった場合．
                        continue
                    if name == '.lq.FastTest.authGame':
                        # ゲーム中にまれにやり取りされる．
                        continue
                    if name == '.lq.FastTest.checkNetworkDelay':
                        continue
                    if name == '.lq.FastTest.fetchGamePlayerState':
                        # TODO: 各プレイヤの接続状態の確認．
                        continue
                    if name == '.lq.NotifyPlayerConnectionState':
                        # TODO: 各プレイヤの接続状態の確認
                        continue
                    if name == '.lq.NotifyGameBroadcast':
                        # TODO: スタンプその他の処理
                        continue
                    if name == '.lq.PlayerLeaving':
                        # TODO: 離席判定をくらった場合の対処
                        continue
                    if name == '.lq.ActionPrototype':
                        step, action_name, data = _common.parse_action(request)
                        if action_name == 'ActionHule':
                            # 他家の栄和に邪魔されていた．
                            rpa._get_redis().put_back(message)
                            self.__operation_list = None
                            now = datetime.datetime.now(datetime.timezone.utc)
                            self._wait_impl(rpa, deadline - now)
                            return
                        ss = rpa.get_screenshot()
                        now = datetime.datetime.now(datetime.timezone.utc)
                        ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                        raise InconsistentMessage(message, rpa.get_screenshot())
                    if name == '.lq.FastTest.inputOperation':
                        raise InconsistentMessage(message, rpa.get_screenshot())
                    if name == '.lq.FastTest.inputChiPengGang':
                        raise InconsistentMessage(message, rpa.get_screenshot())
                    raise InconsistentMessage(message, rpa.get_screenshot())
            if len(operation.combinations) >= 2:
                if len(operation.combinations) == 2:
                    if index == 0:
                        left = 780
                    elif index == 1:
                        left = 980
                    else:
                        raise InvalidOperation(
                            f'{index}: out-of-range index', rpa.get_screenshot())
                else:
                    ss = rpa.get_screenshot()
                    now = datetime.datetime.now(datetime.timezone.utc)
                    ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                    raise AssertionError(len(operation.combinations))
                rpa._click_region(left, 691, 160, 120)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, AngangOperation):
            # 手牌の上にカーソルがあると和牌候補が表示されて
            # テンプレートマッチングを邪魔することがあるので
            # 手牌が無い適当な位置にカーソルを移動する．
            rpa._move_to_region(986, 806, 134, 57, edge_sigma=1.0)
            templates = tuple(
                Template.open(f'template/match/gang{i}') for i in range(2))
            try:
                Template.wait_for_one_of_then_click(
                    templates, rpa._get_browser(), 10.0)
            except Timeout as e:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError
            if len(operation.combinations) >= 2:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, DaminggangOperation):
            ss = rpa.get_screenshot()
            now = datetime.datetime.now(datetime.timezone.utc)
            ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
            raise NotImplementedError

        if isinstance(operation, JiagangOperation):
            # 手牌の上にカーソルがあると和牌候補が表示されて
            # テンプレートマッチングを邪魔することがあるので
            # 手牌が無い適当な位置にカーソルを移動する．
            rpa._move_to_region(986, 806, 134, 57, edge_sigma=1.0)
            template = Template.open('template/match/gang0')
            try:
                template.wait_for_then_click(rpa._get_browser(), 10.0)
            except Timeout as e:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError
            if len(operation.combinations) >= 2:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, LiqiOperation):
            # 手牌の上にカーソルがあると和牌候補が表示されて
            # テンプレートマッチングを邪魔することがあるので
            # 手牌が無い適当な位置にカーソルを移動する．
            rpa._move_to_region(976, 812, 147, 51, edge_sigma=1.0)
            template = Template.open('template/match/liqi')
            try:
                template.wait_for_then_click(rpa._get_browser(), 10.0)
            except Timeout as e:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise
            if index < len(self.shoupai):
                if self.shoupai[index] not in operation.candidate_dapai_list:
                    raise InvalidOperation(index, rpa.get_screenshot())
            elif index == len(self.shoupai):
                if self.zimopai not in operation.candidate_dapai_list:
                    raise InvalidOperation('', rpa.get_screenshot())
            else:
                raise InvalidOperation(
                    f'{index}: Out of index.', rpa.get_screenshot())
            self.__dapai(rpa, index, [])
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, ZimohuOperation):
            # 手牌の上にカーソルがあると和牌候補が表示されて
            # テンプレートマッチングを邪魔することがあるので
            # 手牌が無い適当な位置にカーソルを移動する．
            rpa._move_to_region(966, 807, 154, 56, edge_sigma=1.0)
            template = Template.open('template/match/zimohu')
            try:
                template.wait_for_then_click(rpa._get_browser(), 10.0)
            except Timeout as e:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, RongOperation):
            template = Template.open('template/match/rong')
            try:
                template.wait_for_then_click(rpa._get_browser(), 10.0)
            except Timeout as e:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, JiuzhongjiupaiOperation):
            template = Template.open('template/match/liuju')
            try:
                template.wait_for_then_click(rpa._get_browser(), 10.0)
            except Timeout as e:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        raise InvalidOperation(f'''An invalid operation.
operation: {operation}
index: {index}''', rpa.get_screenshot())
