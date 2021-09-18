#!/usr/bin/env python3

import time
from majsoul_rpa import RPA
from majsoul_rpa.presentation import RoomHostPresentation
from majsoul_rpa.presentation.match.operation import DapaiOperation
from majsoul_rpa.presentation.match import MatchPresentation


if __name__ == '__main__':
    with RPA(proxy_port=8081, redis_port=6379) as rpa:
        p = rpa.wait(timeout=20.0)

        from majsoul_rpa.presentation import LoginPresentation
        if isinstance(p, LoginPresentation):
            p.login(rpa, timeout=60.0)
            if p.new_presentation is None:
                raise RuntimeError('Could not transit to `auth`.')
            p = p.new_presentation

        from majsoul_rpa.presentation import AuthPresentation
        if isinstance(p, AuthPresentation):
            mail_address = input('メールアドレス: ')
            rpa.activate_browser()
            time.sleep(1.0)
            p.enter_mail_address(rpa, mail_address)
            auth_code = input('認証コード: ')
            rpa.activate_browser()
            time.sleep(1.0)
            p.enter_auth_code(rpa, auth_code, timeout=60.0)
            if p.new_presentation is None:
                raise RuntimeError('Could not transit to `home`.')
            p = p.new_presentation

        from majsoul_rpa.presentation import HomePresentation
        p: HomePresentation = p
        print(f'account id: {rpa.get_account_id()}')
        p.create_room(rpa, timeout=60.0)
        if p.new_presentation is None:
            raise RuntimeError('Could not transit to `room_host`.')
        p = p.new_presentation

        print(f'room id: {p.room_id}')

        while p.num_cpus < 3:
            p.add_cpu(rpa, timeout=10.0)
        p.start(rpa, timeout=60.0)
        if p.new_presentation is None:
            raise RuntimeError('Could not transit to `match_main`.')
        p = p.new_presentation

        print(f'UUID: {p.uuid}')
        seat = None
        for i, player in enumerate(p.players):
            if player.account_id == rpa.get_account_id():
                assert(seat is None)
                seat = i
            print(f'{player.name} ({player.level4}, {player.character})')
        assert(seat is not None)
        changs = ['東', '南', '西', '北']
        print(f'{changs[p.chang]}{p.ju + 1}局{p.ben}本場'
              f' (供託{p.liqibang}本)')
        print(f'スコア: {",".join([str(s) for s in p.scores])}')
        print(f'表ドラ表示牌: {p.dora_indicators[0]}')
        print(f'自風: {changs[seat]}')
        print(f'手牌: {",".join(p.shoupai)}')
        if p.zimopai is not None:
            print(f'自摸牌: {p.zimopai}')

        while True:
            ops = p.operation_list
            if ops is not None:
                moqie = False
                for op in ops:
                    if isinstance(op, DapaiOperation):
                        moqie = True
                        break
                if moqie:
                    time.sleep(0.1)
                    p.select_operation(rpa, op, 13)
                else:
                    p.select_operation(rpa, None)
            else:
                p.wait(rpa)

            if p.new_presentation is not None:
                p = p.new_presentation
                if isinstance(p, MatchPresentation):
                    continue
                assert(isinstance(p, RoomHostPresentation))
                break

        p.leave(rpa)
        p = p.new_presentation
        assert(isinstance(p, HomePresentation))
