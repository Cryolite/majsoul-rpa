import datetime
import time
import logging
from typing import (Optional, Tuple, List,)
from PIL.Image import Image
from majsoul_rpa._impl.redis import Message
from majsoul_rpa.common import TimeoutType
from majsoul_rpa._impl import (Redis, BrowserBase, Template,)
from majsoul_rpa import common
from majsoul_rpa.presentation.presentation_base import (
    Timeout, InconsistentMessage, PresentationNotDetected, InvalidOperation,
    BrowserRefreshRequest, PresentationBase,)
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
    from majsoul_rpa import RPA

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

    __COMMON_MESSAGE_NAMES = (
        '.lq.Lobby.heatbeat',
        '.lq.Lobby.loginBeat',
        '.lq.NotifyReviveCoinUpdate',
        '.lq.NotifyGiftSendRefresh',
        '.lq.NotifyDailyTaskUpdate',
        '.lq.NotifyShopUpdate',
        '.lq.NotifyAccountChallengeTaskUpdate',
        '.lq.NotifyAccountUpdate',
        '.lq.NotifyActivityChange',
        '.lq.NotifyAnnouncementUpdate',
        '.lq.FastTest.authGame',
        '.lq.Lobby.oauth2Login',
        '.lq.FastTest.checkNetworkDelay',
        '.lq.FastTest.fetchGamePlayerState',
        '.lq.NotifyPlayerConnectionState',
        '.lq.NotifyGameBroadcast',
        '.lq.PlayerLeaving',
    )

    def __on_common_message(self, message: Message) -> None:
        _, name, request, _, _ = message

        if name == '.lq.Lobby.heatbeat':
            # 頻繁にやり取りされる．
            return

        if name == '.lq.Lobby.loginBeat':
            # まれにやり取りされる．
            logging.warning(message)
            return

        if name == '.lq.NotifyReviveCoinUpdate':
            # 日付（06:00:00 (UTC+0900)）を跨いだ場合．
            logging.info(message)
            return

        if name == '.lq.NotifyGiftSendRefresh':
            # 同上．
            logging.info(message)
            return

        if name == '.lq.NotifyDailyTaskUpdate':
            # 同上．
            logging.info(message)
            return

        if name == '.lq.NotifyShopUpdate':
            # 同上．
            logging.info(message)
            return

        if name == '.lq.Lobby.fetchShopInterval':
            # 同上．
            logging.info(message)
            return

        if name == '.lq.NotifyAccountChallengeTaskUpdate':
            # 同上．
            logging.info(message)
            return

        if name == '.lq.NotifyAccountUpdate':
            # 同上．
            logging.info(message)
            return

        if name == '.lq.NotifyActivityChange':
            # 同上？
            logging.info(message)
            return

        if name == '.lq.NotifyAnnouncementUpdate':
            # 告知の更新があった場合．
            logging.info(message)
            return

        if name == '.lq.FastTest.authGame':
            # ゲーム中にまれにやり取りされる．
            logging.info(message)
            return

        if name == '.lq.Lobby.oauth2Login':
            logging.warning(message)
            if request['reconnect']:
                # 通信が切断後，再接続した場合．
                return
            raise InconsistentMessage(message)

        if name == '.lq.FastTest.checkNetworkDelay':
            return

        if name == '.lq.FastTest.fetchGamePlayerState':
            logging.info(message)
            # TODO: 各プレイヤの接続状態の確認
            return

        if name == '.lq.NotifyPlayerConnectionState':
            logging.info(message)
            # TODO: 各プレイヤの接続状態の確認
            return

        if name == '.lq.NotifyGameBroadcast':
            logging.info(message)
            # TODO: スタンプその他の処理
            return

        if name == '.lq.PlayerLeaving':
            logging.info(message)
            # TODO: 離席判定をくらった場合の対処
            return

        raise AssertionError(message)

    def __init__(
        self, prev_presentation: Optional[PresentationBase], screenshot: Image,
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
                for i in range(4):
                    template = Template.open(f'template/match/marker{i}')
                    x, y, score = template.best_template_match(screenshot)
                    print(f'({x}, {y}): score = {score}')
                now = datetime.datetime.now(datetime.timezone.utc)
                screenshot.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
            raise PresentationNotDetected(
                'Could not detect `match_main`.', screenshot)

        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = self._get_redis().dequeue_message(deadline - now)
            if message is None:
                raise Timeout('Timeout', screenshot)
            _, name, request, response, timestamp = message

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.oauth2Auth':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.oauth2Check':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.oauth2Login':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchLastPrivacy':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchServerTime':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchServerSettings':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchConnectionInfo':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchClientValue':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchFriendList':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchFriendApplyList':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchRecentFriend':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchMailInfo':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchDailyTask':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchReviveCoinInfo':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchTitleList':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchBagInfo':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchShopInfo':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchShopInterval':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchActivityList':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchActivityInterval':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchAccountActivityData':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchActivityBuff':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchVipReward':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchMonthTicketInfo':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchAchievement':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchCommentSetting':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchAccountSettings':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchModNicknameTime':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchMisc':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchAnnouncement':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchRollingNotice':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.loginSuccess':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchCharacterInfo':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.Lobby.fetchAllCommonViews':
                logging.info(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.FastTest.syncGame':
                logging.info(message)
                self.__on_sync_game(message)
                continue

            # 中断していた対戦を再開した時のみ．
            if name == '.lq.FastTest.finishSyncGame':
                logging.info(message)
                return

            if name == '.lq.Lobby.modifyRoom':
                # 友人戦開始後に友人戦待機部屋の変更に関する API の
                # レスポンスメッセージが返ってきた場合．
                logging.info(message)
                continue

            if name == '.lq.NotifyRoomPlayerUpdate':
                # 友人戦開始後に友人戦待機部屋の変更通知が送られてきた場合．
                logging.info(message)
                continue

            if name == '.lq.NotifyRoomPlayerReady':
                # 同上．
                logging.info(message)
                continue

            if name == '.lq.NotifyRoomGameStart':
                # 友人戦開始．
                logging.info(message)
                uuid = request['game_uuid']
                self.__match_state._set_uuid(uuid)
                continue

            if name == '.lq.Lobby.startRoom':
                logging.info(message)
                continue

            if name == '.lq.FastTest.authGame':
                logging.info(message)
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
                    except KeyError as _:
                        # キャラクタ ID が不明なキャラクタと遭遇した場合
                        logging.warning('%s: %s: charid = %s', uuid, nickname, charid)
                        character = 'UNKNOWN'
                    player_map[account_id] = MatchPlayer(
                        account_id, nickname, level4, level3, character)
                players = []
                for i in range(4):
                    account_id = response['seat_list'][i]
                    if account_id == redis.account_id:
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
                logging.info(message)
                # TODO: 中断した対戦の再開処理？
                continue

            if name == '.lq.NotifyPlayerLoadGameReady':
                logging.info(message)
                continue

            if name == '.lq.ActionPrototype':
                step, action_name, data = _common.parse_action(request)
                action_info = {
                    'step': step, 'action_name': action_name, 'data': data
                }
                if step != self.__step:
                    raise InconsistentMessage(action_info, screenshot)
                self.__step += 1

                if action_name == 'ActionMJStart':
                    logging.info(action_info)
                    continue

                if action_name == 'ActionNewRound':
                    logging.info(action_info)
                    self.__events.append(NewRoundEvent(data, timestamp))
                    self.__round_state = RoundState(self.__match_state, data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                raise InconsistentMessage(action_info, screenshot)

            # `.lq.FastTest.authGame` に関する条件文は，この条件文より
            # 先になければならない．
            if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                self.__on_common_message(message)
                continue

            raise InconsistentMessage(message, screenshot)

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
        return self.__round_state.first_draw[self.seat]

    @property
    def yifa(self) -> List[bool]:
        return self.__round_state.yifa

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
        self, rpa: RPA, left: int, top: int, width: int, height: int, interval: TimeoutType,
        timeout: Timeout, edge_sigma: float=2.0, warp: bool=False) -> None:
        if isinstance(interval, (int, float,)):
            interval = datetime.timedelta(seconds=interval)

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)

        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                raise Timeout('Timeout', rpa.get_screenshot())

            rpa._click_region(left, top, width, height, edge_sigma=edge_sigma, warp=warp)
            message = rpa._get_redis().dequeue_message(interval)
            if message is None:
                continue
            _, name, _, _, _ = message

            if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                self.__on_common_message(message)
                continue

            if name == '.lq.FastTest.inputOperation':
                logging.info(message)
                break

            if name == '.lq.FastTest.inputChiPengGang':
                logging.info(message)
                break

            if name == '.lq.ActionPrototype':
                logging.info(message)
                break

            raise InconsistentMessage(message, rpa.get_screenshot())

        # 先読みしたメッセージの埋め戻し．
        rpa._get_redis().put_back(message)

    def __reset_to_prev_presentation(self, rpa: RPA, timeout: TimeoutType) -> None:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        # 報酬取得時などの追加の「確認」ボタンがあればクリックする．
        template = Template.open('template/match/match_result_confirm')
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                raise Timeout('Timeout', rpa.get_screenshot())
            try:
                template.wait_for_then_click(rpa._get_browser(), 5.0)
            except Timeout as _:
                break

        from majsoul_rpa.presentation.room.host import RoomHostPresentation
        if isinstance(self.__prev_presentation, RoomHostPresentation):
            now = datetime.datetime.now(datetime.timezone.utc)
            RoomHostPresentation._wait(rpa._get_browser(), deadline - now)
            now = datetime.datetime.now(datetime.timezone.utc)
            p = RoomHostPresentation._create(
                rpa.get_screenshot(), rpa._get_redis(), deadline - now)
            self._set_new_presentation(p)
            return

        # TODO: 中断していた対戦を再開した場合に対処する．
        # この場合， `self.__prev_presentation` は `None` になっている．

        raise NotImplementedError(type(self.__prev_presentation))

    def __on_end_of_match(self, rpa: RPA, deadline: datetime.datetime) -> None:
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = self._get_redis().dequeue_message(deadline - now)
            if message is None:
                raise Timeout('Timeout', rpa.get_screenshot())
            direction, name, request, _, _ = message

            if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                self.__on_common_message(message)
                continue

            if name == '.lq.FastTest.inputChiPengGang':
                # `.lq.FastTest.inputChiPengGang` のレスポンスメッセージが
                # 遅れて返ってくることがあるので，それに対する workaround．
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchAccountInfo':
                logging.info(message)
                # TODO: メッセージ内容の処理．
                # イベント中のみ？
                continue
                #now = datetime.datetime.now(datetime.timezone.utc)
                #self.__reset_to_prev_presentation(rpa, deadline - now)
                #return

            if name == '.lq.NotifyAccountUpdate':
                logging.info(message)
                # TODO: メッセージ内容の処理．
                continue

            if name == '.lq.NotifyGameFinishReward':
                logging.info(message)
                # TODO: メッセージ内容の処理．
                continue

            if name == '.lq.NotifyActivityReward':
                logging.info(message)
                # TODO: メッセージ内容の処理．
                continue

            if name == '.lq.NotifyActivityPoint':
                logging.info(message)
                # TODO: メッセージ内容の処理．
                continue

            if name == '.lq.NotifyActivityPointV2':
                logging.info(message)
                # TODO: メッセージ内容の処理．

                # これ以上メッセージが無いならばホーム画面へ戻る．
                message = self._get_redis().dequeue_message(5)
                if message is None:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    self.__reset_to_prev_presentation(rpa, deadline - now)
                    return

                # 先読みしたメッセージを埋め戻して次へ．
                self._get_redis().put_back(message)
                continue

            if name == '.lq.NotifyLeaderboardPoint':
                logging.info(message)
                # TODO: メッセージ内容の処理．
                continue

            if name == '.lq.Lobby.fetchRoom':
                # 先読みしたメッセージの埋め戻し．
                self._get_redis().put_back(message)

                now = datetime.datetime.now(datetime.timezone.utc)
                self.__reset_to_prev_presentation(rpa, deadline - now)
                return

            raise InconsistentMessage(message, rpa.get_screenshot())

    def __workaround_for_reordered_actions(
        self, rpa: RPA, message: Message, expected_step: int, timeout: TimeoutType) -> Message:
        # `.lq.ActionPrototype` が `step` 順通りに来ない場合があるので，
        # メッセージを先読みして `step` 順通りに並べ替える．
        if message is None:
            raise ValueError('`message` is `None`.')
        if message[1] != '.lq.ActionPrototype':
            raise ValueError(message)

        if expected_step < 0:
            raise ValueError(expected_step)

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        messages: List[Message] = []
        while True:
            assert(message is not None)
            _, name, request, _, _ = message

            flag = False

            if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                self.__on_common_message(message)
                flag = True

            if name == '.lq.ActionPrototype':
                step, action_name, data = _common.parse_action(request)
                action_info = {
                    'step': step, 'action_name': action_name, 'data': data
                }
                if step < expected_step:
                    raise InconsistentMessage(action_info, rpa.get_screenshot())
                while len(messages) <= step - expected_step:
                    messages.append(None)
                messages[step - expected_step] = message
                if messages.count(None) == 0:
                    result = messages.pop(0)
                    while len(messages) > 0:
                        message = messages.pop(-1)
                        rpa._get_redis().put_back(message)
                    return result
                flag = True

            if not flag:
                action_infos: List[object] = []
                for m in messages:
                    if m is None:
                        action_info = None
                    else:
                        _, name, request, _, _ = m
                        assert(name == '.lq.ActionPrototype')
                        step, action_name, data = _common.parse_action(request)
                        action_info = {
                            'step': step,
                            'action_name': action_name,
                            'data': data
                        }
                    action_infos.append(action_info)
                error_message = {
                    'expected_step': expected_step,
                    'actions': action_infos,
                    'message': message
                }
                raise InconsistentMessage(error_message, rpa.get_screenshot())

            now = datetime.datetime.now(datetime.timezone.utc)
            message = rpa._get_redis().dequeue_message(deadline - now)
            if message is None:
                raise Timeout('Timeout.', rpa.get_screenshot())

    def __workaround_for_skipped_confirm_new_round(
        self, rpa: RPA, message: Message, deadline: datetime.datetime) -> None:
        # `.lq.FastTest.confirmNewRound` のやり取りが飛ばされた場合の workaround. この場合，次局の `.lq.ActionPrototype`
        # メッセージが `step` 順に来ないことがあるので， `step` 順に並べ替える workaround も行う．
        if message is None:
            raise ValueError('`message` is `None`.')
        _, name, request, _, _ = message
        if name != '.lq.ActionPrototype':
            raise InconsistentMessage(message, rpa.get_screenshot())

        step, action_name, _ = _common.parse_action(request)
        if step != 0:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = self.__workaround_for_reordered_actions(
                rpa, message, 0, deadline - now)

        assert(message is not None)
        _, name, request, _, _ = message
        assert(name == '.lq.ActionPrototype')
        step, action_name, _ = _common.parse_action(request)
        assert(step == 0)
        assert(action_name == 'ActionNewRound')
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

    def __on_end_of_round(self, rpa: RPA, deadline: datetime.datetime) -> None:
        template = Template.open('template/match/round_result_confirm')
        round_result_confirmed = False
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                raise Timeout('Timeout.', rpa.get_screenshot())

            if not round_result_confirmed and template.match(rpa.get_screenshot()):
                template.click(rpa._get_browser())
                round_result_confirmed = True

            now = datetime.datetime.now(datetime.timezone.utc)
            message = self._get_redis().dequeue_message(deadline - now)
            if message is None:
                continue
            _, name, request, _, _ = message

            if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                self.__on_common_message(message)
                continue

            if name == '.lq.FastTest.inputOperation':
                # `.lq.FastTest.inputOperation` のレスポンスメッセージが
                # 遅れて返ってくることがあるので，それに対する workaround．
                logging.info(message)
                continue

            if name == '.lq.FastTest.inputChiPengGang':
                # `.lq.FastTest.inputChiPengGang` のレスポンスメッセージが
                # 遅れて返ってくることがあるので，それに対する workaround．
                logging.info(message)
                continue

            if name == '.lq.NotifyActivityChange':
                logging.info(message)
                # TODO: メッセージ内容の解析
                continue

            if name == '.lq.FastTest.confirmNewRound':
                # 対局終了時 (次局がある場合)
                logging.info(message)
                while True:
                    # `ActionNewRound` メッセージを待つ．
                    now = datetime.datetime.now(datetime.timezone.utc)
                    message = rpa._get_redis().dequeue_message(deadline - now)
                    if message is None:
                        raise Timeout('Timeout', rpa.get_screenshot())
                    direction, name, request, response, timestamp = message
                    if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                        self.__on_common_message(message)
                        continue
                    if name == '.lq.ActionPrototype':
                        step, action_name, data = _common.parse_action(request)
                        action_info = {
                            'step': step,
                            'action_name': action_name,
                            'data': data
                        }
                        if action_name == 'ActionNewRound':
                            # 先読みしたメッセージの埋め戻し．
                            rpa._get_redis().put_back(message)
                            break
                        raise InconsistentMessage(
                            action_info, rpa.get_screenshot())
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
                    raise InconsistentMessage(
                        {'step': step, 'action_name': action_name, 'data': data},
                        rpa.get_screenshot())
                while True:
                    # `.lq.FastTest.confirmNewRound` のレスポンスメッセージを
                    # 待つ．
                    now = datetime.datetime.now(datetime.timezone.utc)
                    next_message = rpa._get_redis().dequeue_message(deadline - now)
                    if next_message is None:
                        raise Timeout('Timeout', rpa.get_screenshot())
                    _, next_name, _, _, _ = next_message
                    if next_name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                        self.__on_common_message(next_message)
                        continue
                    if next_name == '.lq.ActionPrototype':
                        # `.lq.FastTest.confirmNewRound` と `ActionNewRound` の
                        # やり取りを飛ばして，次局の `step = 1` の
                        # `.lq.ActionPrototype` が飛んでくる場合があるので，
                        # その現象に対する workaround.
                        # 先読みしたメッセージを埋め戻しておく．
                        rpa._get_redis().put_back(next_message)
                        self.__workaround_for_skipped_confirm_new_round(
                            rpa, message, deadline)
                        return
                    if next_name == '.lq.FastTest.confirmNewRound':
                        logging.info(next_name)
                        break
                    if data['ju'] == self.seat:
                        # 次局の親が自分である場合．
                        # 極めて稀な状況で， `.lq.FastTest.confirmNewRound` の
                        # レスポンスメッセージが返ってこない場合がある？
                        logging.warning(message)
                        break
                    raise InconsistentMessage(
                        next_message, rpa.get_screenshot())
                # `ActionNewRound` を Redis のメッセージキューに埋め戻した上で
                # 制御フローをユーザ側に返す．
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
                logging.info(message)
                # TODO: メッセージ内容の処理．
                template = Template.open('template/match/match_result_confirm')
                template.wait_until_then_click(rpa._get_browser(), deadline)
                self.__on_end_of_match(rpa, deadline)
                return

            raise InconsistentMessage(message, rpa.get_screenshot())

    def __on_sync_game(self, message: Message) -> None:
        direction, name, request, response, timestamp = message
        if direction != 'outbound':
            raise ValueError(message)
        if name != '.lq.FastTest.syncGame':
            raise ValueError(message)

        game_restore = response['game_restore']

        if game_restore['game_state'] != 1:
            raise NotImplementedError(message)

        actions: List[object] = game_restore['actions']
        if len(actions) == 0:
            raise InconsistentMessage(message)
        if len(actions) != response['step']:
            raise InconsistentMessage(message)

        action = actions.pop(0)
        step, name, data = _common.parse_action(action, restore=True)
        if step != 0:
            raise InconsistentMessage(action)
        if name != 'ActionNewRound':
            raise InconsistentMessage(action)
        self.__step = 0
        self.__events.clear()
        self.__events.append(NewRoundEvent(data, timestamp))
        self.__round_state = RoundState(self.__match_state, data)
        if 'operation' in data and len(data['operation']['operation_list']) > 0:
            self.__operation_list = OperationList(data['operation'])
        else:
            self.__operation_list = None
        self.__step += 1

        for action in actions:
            step, name, data = _common.parse_action(action, restore=True)
            if step != self.__step:
                raise InconsistentMessage(action)

            if name == 'ActionDealTile':
                self.__events.append(ZimoEvent(data, timestamp))
                self.__round_state._on_zimo(data)
                if 'operation' in data and len(data['operation']['operation_list']) > 0:
                    self.__operation_list = OperationList(data['operation'])
                else:
                    self.__operation_list = None
                self.__step += 1
                continue

            if name == 'ActionDiscardTile':
                self.__events.append(DapaiEvent(data, timestamp))
                self.__round_state._on_dapai(data)
                if 'operation' in data and len(data['operation']['operation_list']) > 0:
                    self.__operation_list = OperationList(data['operation'])
                else:
                    self.__operation_list = None
                self.__step += 1
                continue

            if name == 'ActionChiPengGang':
                self.__events.append(ChiPengGangEvent(data, timestamp))
                self.__round_state._on_chipenggang(data)
                if 'operation' in data and len(data['operation']['operation_list']) > 0:
                    self.__operation_list = OperationList(data['operation'])
                else:
                    self.__operation_list = None
                self.__step += 1
                continue

            if name == 'ActionAnGangAddGang':
                self.__events.append(AngangJiagangEvent(data, timestamp))
                self.__round_state._on_angang_jiagang(data)
                if 'operation' in data and len(data['operation']['operation_list']) > 0:
                    self.__operation_list = OperationList(data['operation'])
                else:
                    self.__operation_list = None
                self.__step += 1
                continue

            if name == 'ActionHule':
                raise InconsistentMessage(action)

            if name == 'ActionNoTile':
                raise InconsistentMessage(action)

            if name == 'ActionLiuJu':
                raise InconsistentMessage(action)

            raise InconsistentMessage(action)

    def _wait_impl(self, rpa: RPA, timeout: TimeoutType=300.0) -> None:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = self._get_redis().dequeue_message(deadline - now)
            if message is None:
                raise Timeout('Timeout', rpa.get_screenshot())
            _, name, request, _, timestamp = message

            if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                self.__on_common_message(message)
                continue

            if name == '.lq.ActionPrototype':
                step, action_name, data = _common.parse_action(request)
                action_info = {
                    'step': step, 'action_name': action_name, 'data': data
                }

                if step != self.__step:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    message = self.__workaround_for_reordered_actions(
                        rpa, message, self.__step, deadline - now)
                    assert(message is not None)
                    _, name, request, _, timestamp = message
                    assert(name == '.lq.ActionPrototype')
                    step, action_name, data = _common.parse_action(request)
                    assert(step == self.__step)
                    action_info = {
                        'step': step, 'action_name': action_name, 'data': data
                    }
                self.__step += 1

                if action_name == 'ActionMJStart':
                    raise InconsistentMessage(action_info, rpa.get_screenshot())

                if action_name == 'ActionNewRound':
                    raise InconsistentMessage(action_info, rpa.get_screenshot())

                if action_name == 'ActionDealTile':
                    logging.info(action_info)
                    self.__events.append(ZimoEvent(data, timestamp))
                    self.__round_state._on_zimo(data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                if action_name == 'ActionDiscardTile':
                    logging.info(action_info)
                    self.__events.append(DapaiEvent(data, timestamp))
                    self.__round_state._on_dapai(data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                if action_name == 'ActionChiPengGang':
                    logging.info(action_info)
                    self.__events.append(ChiPengGangEvent(data, timestamp))
                    self.__round_state._on_chipenggang(data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                if action_name == 'ActionAnGangAddGang':
                    logging.info(action_info)
                    self.__events.append(AngangJiagangEvent(data, timestamp))
                    self.__round_state._on_angang_jiagang(data)
                    if 'operation' in data:
                        if len(data['operation']['operation_list']) == 0:
                            return
                        self.__operation_list = OperationList(data['operation'])
                    return

                if action_name == 'ActionHule':
                    logging.info(action_info)
                    self.__events.append(HuleEvent(data, timestamp))

                    template = Template.open('template/match/hule_confirm')
                    click_count = 0
                    while True:
                        if datetime.datetime.now(datetime.timezone.utc) > deadline:
                            raise Timeout('Timeout.', rpa.get_screenshot())

                        # 和了画面の「確認」ボタンをクリックする．ただし，
                        # 和了画面がスキップされて次局がいきなり開始される
                        # 場合があるため，その現象に対する workaround を行う．
                        if template.match(rpa.get_screenshot()):
                            template.click(rpa._get_browser())
                            click_count += 1
                            if click_count == len(data['hules']):
                                break
                            continue

                        message1 = rpa._get_redis().dequeue_message(0.1)
                        if message1 is None:
                            continue
                        _, name1, _, _, _ = message1

                        if name1 in MatchPresentation.__COMMON_MESSAGE_NAMES:
                            self.__on_common_message(message1)
                            continue

                        if name1 == '.lq.FastTest.inputOperation':
                            # 自摸和の選択に対するレスポンスメッセージが
                            # `ActionHule` の後に飛んできた場合．
                            logging.info(message1)
                            continue

                        if name1 == '.lq.FastTest.inputChiPengGang':
                            # 自家のチー・ポン・カンの選択よりも他家の和了が
                            # 優先されて，かつ `.lq.FastTest.inputChiPengGang`
                            # のレスポンスメッセージが `ActionHule` の後に
                            # 飛んできた場合．
                            logging.info(message1)
                            continue

                        if name1 == '.lq.NotifyGameEndResult':
                            # 和了画面の「確認」ボタンをクリックする前に
                            # `.lq.NotifyGameEndResult` メッセージが飛んできた
                            # 場合．
                            # 先読みしたメッセージを埋め戻す．
                            rpa._get_redis().put_back(message1)
                            continue

                        if name1 == '.lq.ActionPrototype':
                            # 和了画面がスキップされて次局が開始された場合．
                            # 先読みしたメッセージを埋め戻す．
                            rpa._get_redis().put_back(message1)
                            break

                        # `.lq.FastTest.confirmNewRound` が
                        # やり取りされている場合，画面の描画が
                        # おかしくなっている可能性が高いので
                        # ブラウザの再読み込みを要求する．
                        if name1 == '.lq.FastTest.confirmNewRound':
                            logging.warning(message1)
                            raise BrowserRefreshRequest(
                                'Request to refresh the browser.',
                                rpa._get_browser(), rpa.get_screenshot())

                        raise InconsistentMessage(message1)

                    self.__on_end_of_round(rpa, deadline)
                    return

                if action_name == 'ActionNoTile':
                    logging.info(action_info)
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
                    logging.info(action_info)
                    self.__events.append(LiujuEvent(data, timestamp))

                    self.__on_end_of_round(rpa, deadline)
                    return

            if name == '.lq.FastTest.inputOperation':
                logging.info(message)
                continue

            if name == '.lq.FastTest.inputChiPengGang':
                logging.info(message)
                continue

            if name == '.lq.FastTest.syncGame':
                logging.warning(message)
                self.__on_sync_game(message)
                return

            if name == '.lq.FastTest.finishSyncGame':
                logging.warning(message)
                return

            raise InconsistentMessage(message, rpa.get_screenshot())

    def wait(self, rpa: RPA, timeout: TimeoutType=300.0):
        self._assert_not_stale()

        if self.__operation_list is not None:
            raise InvalidOperation(
                'Must select an operation.', rpa.get_screenshot())
        return self._wait_impl(rpa, timeout)

    def __dapai(self, rpa: RPA, index: int, forbidden_tiles: List[str]) -> None:
        if index is None:
            raise InvalidOperation('Must specify an index for dapai.', rpa.get_screenshot())
        num_tiles = len(self.__round_state.shoupai)
        num_tiles += 0 if (self.__round_state.zimopai is None) else 1
        if index >= num_tiles:
            raise InvalidOperation('Out of index for dapai.', rpa.get_screenshot())

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
        # `timeout=5.0` だと画面の演出が固まった際に短すぎることがある．
        self.__robust_click_region(
            rpa, left, top, width, height, interval=1.0, timeout=25.0,
            edge_sigma=1.0, warp=False)

    def select_operation(
        self, rpa: RPA, operation, index: Optional[int]=None, timeout: TimeoutType=300.0) -> None:
        self._assert_not_stale()

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
            # 選択肢をスキップする．ラグ読みされるのを防ぐため，スキップの UI 操作は可能な限り短時間で行う
            # 必要がある．このため，他家の打牌に対するチー・ポン・カン・ロンをスキップする場合は
            # 「鳴き無し」ボタンをクリックすることによりスキップする（選択肢が出た後でも「鳴き無し」ボタンを
            # クリックすると「スキップ」ボタンをクリックしたのと同じ効果がある）．スキップできたら再度
            # 「鳴き無し」ボタンをクリックして鳴きができる状態に戻す．
            rpa._click_region(14, 623, 43, 43, edge_sigma=1.0, warp=True)
            while True:
                now = datetime.datetime.now(datetime.timezone.utc)
                message = rpa._get_redis().dequeue_message(deadline - now)
                if message is None:
                    raise Timeout('Timeout', rpa.get_screenshot())
                _, name, request, _, _ = message
                if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                    self.__on_common_message(message)
                    continue
                if name == '.lq.FastTest.inputOperation':
                    raise InconsistentMessage(message, rpa.get_screenshot())
                if name == '.lq.FastTest.inputChiPengGang':
                    break
                if name == '.lq.ActionPrototype':
                    break
            # 先読みしたメッセージを埋め戻す．
            rpa._get_redis().put_back(message)
            rpa._click_region(14, 623, 43, 43, edge_sigma=1.0)

            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, DapaiOperation):
            # 打牌
            if self.ju == self.seat and self.first_draw:
                # 自分が親であるとき，配牌の演出で牌が動いているので，
                # その演出が終了するまで待ってから打牌しないと
                # 意図しない牌をクリックして捨ててしまう場合がある．
                time.sleep(1.0)
            self.__dapai(rpa, index, operation.forbidden_tiles)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, ChiOperation):
            # 手牌の上にカーソルがあると和牌候補が表示されて
            # テンプレートマッチングを邪魔することがあるので
            # 手牌が無い適当な位置にカーソルを移動する．
            rpa._move_to_region(987, 806, 132, 57, edge_sigma=1.0)
            templates = tuple(
                Template.open(f'template/match/chi{i}') for i in range(2))
            try:
                # `timeout` を短めに設定しておかないと，他家の栄和に
                # 邪魔された際に和了画面に反応できなくなる．
                Template.wait_for_one_of_then_click(templates, rpa._get_browser(), timeout=5.0)
            except Timeout as _:
                # 他家のポン，槓もしくは栄和に邪魔された可能性がある．
                while True:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    message = rpa._get_redis().dequeue_message(deadline - now)
                    if message is None:
                        ss = rpa.get_screenshot()
                        now = datetime.datetime.now(datetime.timezone.utc)
                        ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                        raise NotImplementedError()
                    _, name, request, _, _ = message
                    if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                        self.__on_common_message(message)
                        continue
                    if name == '.lq.ActionPrototype':
                        _, action_name, _ = _common.parse_action(request)
                        if action_name in ('ActionChiPengGang', 'ActionHule',):
                            # 他家のポン，槓もしくは栄和に邪魔されていた．
                            # 先読みしたメッセージを埋め戻す．
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
                        # 画面の描画が乱れて「チー」ボタンをクリックできない
                        # 状態になっている可能性が高い．従って，ブラウザの
                        # リフレッシュを促す．
                        raise BrowserRefreshRequest(
                            'A rendering problem may occur.',
                            rpa._get_browser(), rpa.get_screenshot())
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
            # チーの直後に手牌の一部がスライドする場合があるため，
            # そのスライドが終わるのを待つための sleep を入れないと
            # 捨て牌選択で意図しない牌をクリックする可能性がある．
            time.sleep(1.0)
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
                Template.wait_for_one_of_then_click(templates, rpa._get_browser(), timeout=5.0)
            except Timeout as _:
                # 他家の栄和に邪魔された可能性がある．
                while True:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    message = rpa._get_redis().dequeue_message(deadline - now)
                    if message is None:
                        ss = rpa.get_screenshot()
                        now = datetime.datetime.now(datetime.timezone.utc)
                        ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                        raise NotImplementedError()
                    _, name, request, _, _ = message
                    if name in MatchPresentation.__COMMON_MESSAGE_NAMES:
                        self.__on_common_message(message)
                        continue
                    if name == '.lq.ActionPrototype':
                        _, action_name, _ = _common.parse_action(request)
                        if action_name == 'ActionHule':
                            # 他家の栄和に邪魔されていた．
                            # 先読みしたメッセージを埋め戻す．
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
                        # 画面の描画が乱れて「ポン」ボタンをクリックできない
                        # 状態になっている可能性が高い．従って，ブラウザの
                        # リフレッシュを促す．
                        raise BrowserRefreshRequest(
                            'A rendering problem may occur.',
                            rpa._get_browser(), rpa.get_screenshot())
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
            # ポンの直後に手牌の一部がスライドする場合があるため，
            # そのスライドが終わるのを待つための sleep を入れないと
            # 捨て牌選択で意図しない牌をクリックする可能性がある．
            time.sleep(1.0)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, AngangOperation):
            # 手牌の上にカーソルがあると和牌候補が表示されて
            # テンプレートマッチングを邪魔することがあるので
            # 手牌が無い適当な位置にカーソルを移動する．
            rpa._move_to_region(986, 806, 134, 57, edge_sigma=1.0)
            templates = tuple(Template.open(f'template/match/gang{i}') for i in range(2))
            try:
                Template.wait_for_one_of_then_click(templates, rpa._get_browser(), 10.0)
            except Timeout as _:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError()
            if len(operation.combinations) >= 2:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError()
            # 暗槓の直後に手牌の一部がスライドする場合があるため，
            # そのスライドが終わるのを待つための sleep を入れないと
            # 捨て牌選択で意図しない牌をクリックする可能性がある．
            time.sleep(1.0)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, DaminggangOperation):
            template = Template.open('template/match/gang0')
            try:
                template.wait_for_then_click(rpa._get_browser(), 10.0)
            except Timeout as _:
                # TODO: 他家の栄和に邪魔された可能性がある．
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError()
            if len(operation.combinations) >= 2:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError()
            # 大明槓の直後に手牌の一部がスライドする場合があるため，
            # そのスライドが終わるのを待つための sleep を入れないと
            # 捨て牌選択で意図しない牌をクリックする可能性がある．
            time.sleep(1.0)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, JiagangOperation):
            # 手牌の上にカーソルがあると和牌候補が表示されて
            # テンプレートマッチングを邪魔することがあるので
            # 手牌が無い適当な位置にカーソルを移動する．
            rpa._move_to_region(986, 806, 134, 57, edge_sigma=1.0)
            template = Template.open('template/match/gang0')
            try:
                template.wait_for_then_click(rpa._get_browser(), 10.0)
            except Timeout as _:
                ss = rpa.get_screenshot()
                now = datetime.datetime.now(datetime.timezone.utc)
                ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                raise NotImplementedError()
            if len(operation.combinations) >= 2:
                if len(operation.combinations) == 2:
                    if index == 0:
                        left = 600
                    elif index == 1:
                        left = 960
                    else:
                        raise InvalidOperation(
                            f'{index}: out-of-range index', rpa.get_screenshot())
                else:
                    ss = rpa.get_screenshot()
                    now = datetime.datetime.now(datetime.timezone.utc)
                    ss.save(now.strftime('%Y-%m-%d-%H-%M-%S.png'))
                    raise NotImplementedError()
                rpa._click_region(left, 691, 320, 120)
            # 加槓の直後に手牌の一部がスライドする場合があるため，
            # そのスライドが終わるのを待つための sleep を入れないと
            # 捨て牌選択で意図しない牌をクリックする可能性がある．
            time.sleep(1.0)
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
                template.wait_for_then_click(rpa._get_browser(), 5.0)
            except Timeout as _:
                # 画面の描画が乱れて「立直」ボタンをクリックできない
                # 状態になっている可能性が高い．従って，ブラウザの
                # リフレッシュを促す．
                raise BrowserRefreshRequest(
                    'A rendering problem may occur.', rpa._get_browser(), rpa.get_screenshot())
            if index < len(self.shoupai):
                if self.shoupai[index] not in operation.candidate_dapai_list:
                    raise InvalidOperation(index, rpa.get_screenshot())
            elif index == len(self.shoupai):
                if self.zimopai not in operation.candidate_dapai_list:
                    raise InvalidOperation('', rpa.get_screenshot())
            else:
                raise InvalidOperation(f'{index}: Out of index.', rpa.get_screenshot())
            self.__dapai(rpa, index, [])
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, ZimohuOperation):
            # 自摸和．タメツモを防ぐため，自摸和の UI 操作は可能な限り短時間で行う必要がある．このため，
            # 「自動和了」ボタンをクリックすることによりスキップする（自摸和の選択肢が出た後でも
            # 「自動和了」ボタンをクリックすると「ツモ」ボタンをクリックしたのと同じ効果がある）．
            rpa._click_region(14, 557, 43, 43, edge_sigma=1.0, warp=True)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, RongOperation):
            # 栄和．タメロンを防ぐため，栄和の UI 操作は可能な限り短時間で行う必要がある．このため，
            # 「自動和了」ボタンをクリックすることによりスキップする（栄和の選択肢が出た後でも
            # 「自動和了」ボタンをクリックすると「ロン」ボタンをクリックしたのと同じ効果がある）．
            rpa._click_region(14, 557, 43, 43, edge_sigma=1.0, warp=True)
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        if isinstance(operation, JiuzhongjiupaiOperation):
            template = Template.open('template/match/liuju')
            try:
                template.wait_for_then_click(rpa._get_browser(), 5.0)
            except Timeout as _:
                # 画面の描画が乱れて「流局」ボタンをクリックできない
                # 状態になっている可能性が高い．従って，ブラウザの
                # リフレッシュを促す．
                raise BrowserRefreshRequest(
                    'A rendering problem may occur.', rpa._get_browser(), rpa.get_screenshot())
            self.__operation_list = None
            now = datetime.datetime.now(datetime.timezone.utc)
            self._wait_impl(rpa, deadline - now)
            return

        raise InvalidOperation(f'''An invalid operation.
operation: {operation}
index: {index}''', rpa.get_screenshot())
