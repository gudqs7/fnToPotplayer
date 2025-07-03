import os
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
    status_code, res = fn_api('/v/api/v1/play/info', {'item_guid': item_guid})
    print('info', status_code, res)
    media_guid = res['media_guid'] or ''
    ts = res['ts']
    title = res['item']['title']

    # 根据 item guid 获取文件流信息，拼接smb文件参数
    status_code, res = fn_api('/v/api/v1/stream/list/' + item_guid, None)
    print('stream', status_code, res)

    if media_guid == '':
        media_guid = res['files'][0]['guid']
    file_path = res['files'][0]['path']

    # 移除 '/vol1/1000'
    path_without_prefix = file_path.replace('/vol1/1000/', '', 1)
    # 将所有 '/' 替换为 '\\'
    windows_path = path_without_prefix.replace('/', '\\')

    print(windows_path)

    smb_url = f'\\\\{hostname}\\{windows_path}'

    time_cmd = '/seek=' + seconds_to_hms(ts)

    title = '/title=' + title

    cmd = [pot_path, smb_url, time_cmd, title]
    player = subprocess.Popen(cmd)
    activate_window_by_pid(player.pid, sleep=1)

    stop_sec = stop_sec_pot(player.pid)
    print('stop_sec ' + str(stop_sec))
    if stop_sec is None:
        return jsonify({'status': 'fail'})

    # 修改时间
    status_code, res = fn_api('/v/api/v1/play/record',
                              {'item_guid': item_guid, 'media_guid': media_guid, 'ts': stop_sec})
    print('修改时间', status_code, res, stop_sec)

    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
