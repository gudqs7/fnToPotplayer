import hashlib
import json
import random
import time
from time import sleep
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit

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
    """生成指定位数的随机数字字符串，首位不为 0。"""
    if length <= 0:
        return ''
    lower = 0 if length == 1 else 10 ** (length - 1)
    upper = 10 ** length - 1
    return str(random.randint(lower, upper))


def _json_dumps_compact(data):
    """与前端 JSON.stringify 保持一致，不能使用 Python 默认的空格分隔。"""
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def _get_sign_query(url):
    """
    按飞牛影视前端的 URLSearchParams 逻辑处理 GET 参数：
    同名参数取最后一个值，按参数名排序，URL 编解码后再参与签名。
    """
    params = {}
    for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=True):
        if value not in ('undefined', 'null'):
            params[key] = value
    query = urlencode(sorted(params.items())).replace('+', '%20')
    return unquote(query)


def _get_sign_body(url, data):
    if data is None:
        return _get_sign_query(url)
    return _json_dumps_compact(data)


def gen_fn_authx(url, data):
    # nonce=102364&timestamp=1751540090490&sign=ae2381cf8eb78bf1d585c622e8906767
    nonce = generate_random_digits()
    timestamp = int(time.time() * 1000)
    path = urlsplit(url).path
    data_json_md5 = get_md5(_get_sign_body(url, data))
    sign_array = [api_key, path, nonce, str(timestamp), data_json_md5, api_secret]

    sign_str = '_'.join(sign_array)

    sign = get_md5(sign_str)
    return f'nonce={nonce}&timestamp={timestamp}&sign={sign}'


def fn_api(url, data, try_times=0):
    full_url = baseUrl.rstrip('/') + url
    authx = gen_fn_authx(url, data)
    headers = {
        "Content-Type": "application/json",
        "Authorization": fn_token,
        "authx": authx,
        "X-Trim-Client": "web",
        "X-Trim-Client-Version": "629",
    }

    if data is None:
        response = requests.get(full_url, headers=headers)
    else:
        body = _json_dumps_compact(data).encode('utf-8')
        response = requests.post(full_url, headers=headers, data=body)
    res = response.json()
    if 'code' in res:
        if res['code'] == 5000:
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
