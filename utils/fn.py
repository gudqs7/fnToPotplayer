import hashlib
import json
import random
import time
from time import sleep

import requests

from utils.log import logger

baseUrl = "xxx"
fn_token = 'xxx'
api_key = 'NDzZTVxnRKP8Z0jXg1VAMonaG8akvh'
api_secret = '16CCEB3D-AB42-077D-36A1-F355324E4237'


def set_global_info(url, token):
    global baseUrl, fn_token
    baseUrl = url
    fn_token = token


def get_md5(text: str) -> str:
    """
    计算字符串的MD5哈希值

    参数:
        text (str): 要计算哈希的文本字符串

    返回:
        str: 32位十六进制格式的MD5哈希值

    示例:
        >>> get_md5("Hello, World!")
        '65a8e27d8879283831b664bd8b7f0ad4'
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def generate_random_digits(length=6):
    """生成指定位数的随机数字字符串（0-9）"""
    return ''.join(str(random.randint(0, 9)) for _ in range(length))


def gen_fn_authx(url, data):
    # nonce=102364&timestamp=1751540090490&sign=ae2381cf8eb78bf1d585c622e8906767
    nonce = generate_random_digits()
    timestamp = int(time.time() * 1000)

    if data is None:
        data_json = ''
    else:
        data_json = json.dumps(data)

    data_json_md5 = get_md5(data_json)
    sign_array = [api_key, url, nonce, str(timestamp), data_json_md5, api_secret]

    sign_str = '_'.join(sign_array)

    sign = get_md5(sign_str)
    return f'nonce={nonce}&timestamp={timestamp}&sign={sign}'


def fn_api(url, data, try_times=0):
    full_url = baseUrl + url
    authx = gen_fn_authx(url, data)
    headers = {"Content-Type": "application/json", "Authorization": fn_token, "authx": authx}

    if data is None:
        response = requests.get(full_url, headers=headers)
    else:
        response = requests.post(full_url, headers=headers, json=data)
    res = response.json()
    if 'code' in res:
        if res['code'] == 5000 and res['msg'] == 'invalid sign':
            if try_times > 2:
                return False, f'尝试次数过多 try_times = {try_times}'
            sleep(0.3)
            logger.info(f'fn_api 请求时签名错误，重试中 try_times = {try_times}')
            return fn_api(url, data, try_times + 1)
        if res['code'] != 0:
            return False, res['msg']
        else:
            return True, res['data']
    else:
        logger.error(f'fn_api 请求失败 - res = {res}')
        return False, res
