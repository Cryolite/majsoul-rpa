#!/usr/bin/env python3

import time
from majsoul_rpa import RPA


if __name__ == '__main__':
    with RPA(proxy_port=8081, redis_port=6379) as rpa:
        p = rpa.wait(timeout=60.0)

        from majsoul_rpa.presentation import LoginPresentation
        if isinstance(p, LoginPresentation):
            p = p.login(rpa, timeout=60.0)

        from majsoul_rpa.presentation import AuthPresentation
        if isinstance(p, AuthPresentation):
            mail_address = input('メールアドレス: ')
            rpa.activate_browser()
            time.sleep(1.0)
            p.enter_mail_address(rpa, mail_address)
            auth_code = input('認証コード: ')
            rpa.activate_browser()
            time.sleep(1.0)
            p = p.enter_auth_code(rpa, auth_code)

        from majsoul_rpa.presentation import HomePresentation
        if not isinstance(p, HomePresentation):
            raise RuntimeError('Cound not transit to `home`.')
        print(f'account id: {rpa.get_account_id()}')
        p = p.create_room(rpa)

        print(f'room id: {p.room_id}')

        while p.num_cpus < 3:
            p = p.add_cpu(rpa, timeout=10.0)

        p = p.leave(rpa, timeout=10.0)
        if not isinstance(p, HomePresentation):
            raise RuntimeError('Cound not transit to `home`.')
