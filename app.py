import os
import re
import subprocess
import threading
import time

from flask import Flask, render_template, request, jsonify, Response

from utils.fn import fn_api, set_global_info
from utils.logger import logger
from utils.potplayer import stop_sec_pot

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

pipe_index = 0
pipe_cache = {}
pipe_process_cache = {}

pot_path = "C:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe"


def activate_window_by_pid(pid, sleep=0):
    if os.name != 'nt':
        time.sleep(1.5)
        return

    from utils.windows_tool import activate_window_by_win32

    def activate_loop():
        for _ in range(100):
            time.sleep(0.5)
            if activate_window_by_win32(pid):
                return

    threading.Thread(target=activate_loop).start()
    time.sleep(sleep)


def seconds_to_hms(seconds):
    # 计算小时、分钟和秒
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    # 格式化为两位数，不足补零
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/movie', methods=['POST'])
def movie():
    # 获取表单数据
    # 获取 item guid 和 media guid （可选，用于指定特定文件）
    item_guid = request.form.get('item_guid')
    base_url = request.form.get('base_url')
    hostname = request.form.get('hostname')
    token = request.form.get('token')

    set_global_info(base_url, token)

    # 根据 item guid 获取影视信息，包括播放开始时间，标题
    success, res = fn_api('/v/api/v1/play/info', {'item_guid': item_guid})
    if not success:
        logger.error(f'获取影视信息失败 - item_guid = {item_guid} 错误信息={res}')
        return jsonify({'status': 'fail'})

    media_guid = res['media_guid'] or ''
    ts = res['ts']
    title = res['item']['title']

    # 根据 item guid 获取文件流信息，拼接smb文件参数
    success, res = fn_api('/v/api/v1/stream/list/' + item_guid, None)
    if not success or not res['files'] or not res['video_streams']:
        logger.error(f'获取影视流信息失败 - item_guid = {item_guid} 错误信息={res}')
        return jsonify({'status': 'fail'})

    if media_guid == '':
        media_guid = res['files'][0]['guid']

    video_guid = res['video_streams'][0]['guid']
    # 根据 media guid 获取 video_streams 对象
    for stream in res['video_streams']:
        stream_media_guid = stream['media_guid']
        if stream_media_guid == media_guid:
            video_guid = stream['guid']
            break

    file_path = res['files'][0]['path']
    # 根据 media guid 获取 files 对象
    for file in res['files']:
        file_guid = file['guid']
        if file_guid == media_guid:
            file_path = file['path']
            break

    # 移除 '/vol1/1000'
    pattern = r'/vol\d/\d{4}/'
    path_without_prefix = re.sub(pattern, '', file_path)
    # 将所有 '/' 替换为 '\\'
    windows_path = path_without_prefix.replace('/', '\\')
    smb_url = f'\\\\{hostname}\\{windows_path}'

    logger.info(f'获取到相关文件信息：{file_path}，SMB地址：{smb_url}')

    time_cmd = '/seek=' + seconds_to_hms(ts)
    title = '/title=' + title

    cmd = [pot_path, smb_url, time_cmd, title]

    logger.info(f'执行cmd，参数：{cmd}')
    player = subprocess.Popen(cmd)
    activate_window_by_pid(player.pid, sleep=1)

    stop_sec = stop_sec_pot(player.pid)
    if stop_sec is None:
        return jsonify({'status': 'fail'})

    logger.info(f'检测到PotPlayer已关闭，关闭时进度为：{seconds_to_hms(stop_sec)}')

    # 修改时间
    success, res = fn_api('/v/api/v1/play/record', {'item_guid': item_guid, 'media_guid': media_guid, 'video_guid': video_guid, 'ts': stop_sec})
    if not success:
        logger.error(f'修改进度失败 - item_guid = {item_guid} stop_sec = {stop_sec} 错误信息={res}')
        return jsonify({'status': 'fail'})

    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
