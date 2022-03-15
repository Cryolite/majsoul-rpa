#!/usr/bin/env python3

import re
import datetime
import time
import logging
import email.policy
import email.parser
from email.message import (EmailMessage,)
from typing import (Optional, List,)
import boto3
from majsoul_rpa.common import TimeoutType


class YostarLogin:
    def __init__(self, config: object) -> None:
        authentication_config = config['authentication']
        method = authentication_config['method']
        if method != 's3':
            raise NotImplementedError(
                f'{method}: Authentication method not implemented.')

        self.__email_address = authentication_config['email_address']
        if 'aws_profile' not in authentication_config:
            s3_client = boto3.resource('s3')
        else:
            aws_profile = authentication_config['aws_profile']
            session = boto3.Session(profile_name=aws_profile)
            s3_client = session.resource('s3')
        bucket_name = authentication_config['bucket_name']
        self.__s3_bucket = s3_client.Bucket(bucket_name)
        self.__key_prefix = authentication_config['key_prefix']

    def get_email_address(self) -> str:
        return self.__email_address

    def __get_authentication_emails(self) -> List[EmailMessage]:
        objects = self.__s3_bucket.objects.filter(Prefix=self.__key_prefix)

        emails = {}

        for obj in objects:
            key = obj.key
            obj = obj.get()
            obj = obj['Body']
            obj = obj.read()
            email_parser = email.parser.BytesParser(policy=email.policy.default)
            obj = email_parser.parsebytes(obj)
            emails[key] = obj

        return emails

    def __get_auth_code(
            self, *, start_time: datetime.datetime) -> Optional[str]:
        emails = self.__get_authentication_emails()

        target_date = None
        target_content = None

        def delete_object(key: str) -> None:
            self.__s3_bucket.delete_objects(
                Delete={
                    'Objects': [
                        {
                            'Key': key,
                        },
                    ],
                }
            )

        for key, email in emails.items():
            if 'Date' not in email:
                delete_object(key)
                logging.info(f'Deleted the S3 object `{key}`.')
                continue
            date = datetime.datetime.strptime(
                email['Date'], '%a, %d %b %Y %H:%M:%S %z')

            if 'To' not in email:
                delete_object(key)
                logging.info(f'Deleted the S3 object `{key}`.')
                continue
            if email['To'] != self.__email_address:
                # 宛先が異なるメールは他のクローラに対して送られた
                # メールの可能性があるので無視する．
                continue

            if 'From' not in email:
                delete_object(key)
                logging.info(f'Deleted the S3 object `{key}`.')
                continue
            if email['From'] != 'info@mail.yostar.co.jp':
                # 差出人が `info@mail.yostar.co.jp` でないメールは
                # ログイン以外の用件に関するものである可能性があるので
                # 無視する．
                continue

            # `Subject` が「Eメールアドレスの確認」でないメールは
            # ログイン以外の用件に関するものである可能性があるので
            # 無視する．
            if 'Subject' not in email:
                continue
            if email['Subject'] != 'Eメールアドレスの確認':
                continue

            now = datetime.datetime.now(tz=datetime.timezone.utc)
            if date < now - datetime.timedelta(minutes=30):
                # 認証コードの有効期限が30分なので，30分以上前に送られた
                # メールは無条件で削除する．
                delete_object(key)
                logging.info(f'Deleted the S3 object `{key}`.')
                continue

            if date < start_time:
                # ログイン開始前に送られたメールを無条件で削除する．
                delete_object(key)
                logging.info(f'Deleted the S3 object `{key}`.')
                continue
            if target_date is not None and date < target_date:
                # すでに他のログインメールが存在する場合，
                # 古いほうのメールを削除する．
                delete_object(key)
                logging.info(f'Deleted the S3 object `{key}`.')
                continue

            target_date = date
            body = email.get_body()
            target_content = body.get_content()

            delete_object(key)
            logging.info(f'Deleted the S3 object `{key}`.')

        if target_content is None:
            return None

        m = re.search('>(\\d{6})<', target_content)
        if m is None:
            return None

        return m.group(1)

    def get_auth_code(self, *, start_time: datetime.datetime,
                      timeout: TimeoutType) -> str:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)

        while True:
            auth_code = self.__get_auth_code(start_time=start_time)
            if auth_code is not None:
                break

            time.sleep(1.0)
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            if now > start_time + timeout:
                raise RuntimeError(
                    'Extraction of the authentication has timed out.')

        return auth_code
