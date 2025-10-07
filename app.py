import ctypes
import json
import os
import re
import subprocess
import threading
import time

from flask import Flask, render_template, request, jsonify

from utils.fn import fn_api, set_global_info
from utils.log import logger
from utils.potplayer import stop_sec_pot

flash_app = Flask(__name__)
flash_app.config['UPLOAD_FOLDER'] = 'uploads'
flash_app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB
os.makedirs(flash_app.config['UPLOAD_FOLDER'], exist_ok=True)

pipe_index = 0
pipe_cache = {}
pipe_process_cache = {}

pot_path = "C:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe"


def set_pot_path(path):
    global pot_path
    pot_path = path


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


def check_key(res, key):
    # 是否有这个key
    if key in res:
        # 是否为空数组，空字典
        if not res[key]:
            return False
        else:
            return True
    else:
        return False


def convert_file_path(file_path, hostname):
    # 处理 /vol02 远程挂载
    vol_number = 0
    first_dir = ''
    other_path = ''
    if file_path.startswith('/vol02/'):
        # 获取远程网盘的路径
        success, res = fn_api('/v/api/v1/server/getAppAuthorizedDir', None)
        if not success or not check_key(res, 'authDirList'):
            logger.error(f'获取远程挂载网盘信息失败 - 错误信息={res}')
            return jsonify({'status': 'fail'})

        for authDir in res['authDirList']:
            auth_path = authDir['path']
            if file_path.startswith(auth_path):
                cloud_type = authDir['cloudStorageType']
                replace_path = ''
                if cloud_type == 4:
                    # 夸克
                    cloud_username = authDir['username']
                    replace_path = f'远程挂载-webdav_{cloud_username}_127.0.0.1_dav'
                elif cloud_type == 1:
                    # 百度
                    cloud_comment = authDir['comment']
                    replace_path = f'远程挂载-百度网盘_{cloud_comment}'
                pattern = r'/vol02/.*?/'
                file_path = re.sub(pattern, f'{replace_path}/', file_path)
                break
    else:
        # 移除 '/vol1/1000'
        pattern = r'/vol(\d)/\d{4}/(.*?)/(.*)'
        match = re.search(pattern, file_path)
        if match:
            vol_number = match.group(1)
            first_dir = match.group(2)
            other_path = match.group(3)
            file_path = f'{first_dir}/{other_path}'

    # 将所有 '/' 替换为 '\\'
    windows_path = file_path.replace('/', '\\')
    smb_path = f'\\\\{hostname}\\{windows_path}'

    smb_exists = check_smb_file(smb_path)
    if smb_exists:
        return smb_path
    else:
        file_path = f'{first_dir} (存储空间{vol_number})/{other_path}'
        windows_path = file_path.replace('/', '\\')
        smb_path = f'\\\\{hostname}\\{windows_path}'
        return smb_path


def check_smb_file(smb_url):
    """
    使用Windows API检查SMB文件是否存在
    """

    # 转换为宽字符字符串
    unc_path_wide = smb_url.encode('utf-16le') + b'\x00\x00'

    # 调用Windows API
    try:
        # 尝试获取文件属性
        attr = ctypes.windll.kernel32.GetFileAttributesW(unc_path_wide)
        if attr == -1 or attr == 0xFFFFFFFF:  # INVALID_FILE_ATTRIBUTES
            error = ctypes.windll.kernel32.GetLastError()
            # 文件不存在错误代码
            if error == 2:  # ERROR_FILE_NOT_FOUND
                return False
            elif error == 3:  # ERROR_PATH_NOT_FOUND
                return False
            else:
                return False
        else:
            return True

    except Exception as e:
        return False


@flash_app.route('/')
def index():
    return render_template('index.html')


@flash_app.route('/movie', methods=['POST'])
def movie():
    # 获取表单数据
    # 获取 item guid 和 media guid （可选，用于指定特定文件）
    item_guid = request.form.get('item_guid')
    base_url = request.form.get('base_url')
    hostname = request.form.get('hostname')
    token = request.form.get('token')
    file_choose = request.form.get('file_choose')

    set_global_info(base_url, token)

    # 根据 item guid 获取影视信息，包括播放开始时间，标题
    success, res = fn_api('/v/api/v1/play/info', {'item_guid': item_guid})
    if not success or not check_key(res, 'item'):
        logger.error(f'获取影视信息失败 - item_guid = {item_guid} 错误信息={res}')
        return jsonify({'status': 'fail'})

    # print('play info ', json.dumps(res))

    media_guid = res['media_guid'] or ''
    video_guid = res['video_guid'] or ''
    subtitle_guid = res['subtitle_guid'] or ''
    audio_guid = res['audio_guid'] or ''
    ts = res['ts']
    title = res['item'].get('title') or ''
    duration = res['item']['duration']

    # 根据 item guid 获取文件流信息，拼接smb文件参数
    success, res = fn_api('/v/api/v1/stream/list/' + item_guid, None)
    if not success or not check_key(res, 'files') or not check_key(res, 'video_streams'):
        logger.error(f'获取影视流信息失败 - item_guid = {item_guid} 错误信息={res}')
        return jsonify({'status': 'fail'})

    # print('stream info ', json.dumps(res))

    if media_guid == '':
        media_guid = res['files'][0]['guid']

    file_path = res['files'][0]['path']
    # 根据 media guid 获取 files 对象
    for file in res['files']:
        file_guid = file['guid']
        if file_guid == media_guid:
            file_path = file['path']
            break

    choose_str = ''
    if file_choose:
        file_choose = int(file_choose)
        if file_choose < len(res['files']):
            choose_file = res['files'][file_choose]
            file_path = choose_file['path']
            media_guid = choose_file['guid']
    # 从 video_streams 获取准确的 duration
    for video in res['video_streams']:
        video_stream_guid = video['guid']
        video_media_guid = video['media_guid']
        if media_guid == video_media_guid:
            duration = video['duration']
            video_guid = video_stream_guid
            choose_str = str.upper(video['resolution_type'] or '') + '-' + (video['color_range_type'] or '')
            break

    if ts > duration:
        ts = 0

    old_path = file_path
    smb_url = convert_file_path(file_path, hostname)
    logger.info(f'获取到相关文件信息：{old_path}，SMB地址：{smb_url}')

    time_cmd = '/seek=' + seconds_to_hms(ts)
    title = '/title=' + title + '　' + str(choose_str) + '　' + str(file_choose)

    cmd = [pot_path, smb_url, time_cmd, title, '/config=fntv']

    logger.info(f'执行cmd，参数：{cmd}')
    player = subprocess.Popen(cmd)
    activate_window_by_pid(player.pid, sleep=1)

    stop_sec = stop_sec_pot(player.pid)
    if stop_sec is None:
        return jsonify({'status': 'fail'})

    logger.info(f'检测到PotPlayer已关闭，关闭时进度为：{seconds_to_hms(stop_sec)} / {seconds_to_hms(duration)}')

    # 小于15s，视作已观看
    if (duration - stop_sec) < 15:
        # 电影标记已观看
        logger.info(f'更新已观看：item_guid = {item_guid}')
        success, res = fn_api(f'/v/api/v1/item/watched', {'item_guid': item_guid})
        if not success:
            logger.error(f'更新已观看失败 - item_guid = {item_guid} 错误信息={res}')
            return jsonify({'status': 'fail'})
    else:
        # 修改时间
        logger.info(f'修改观看进度：item_guid = {item_guid} stop_sec = {seconds_to_hms(stop_sec)}')
        success, res = fn_api('/v/api/v1/play/record',
                              {'item_guid': item_guid, 'media_guid': media_guid, 'video_guid': video_guid,
                               'audio_guid': audio_guid, 'subtitle_guid': subtitle_guid,
                               'ts': stop_sec})
        if not success:
            logger.error(f'修改进度失败 - item_guid = {item_guid} stop_sec = {stop_sec} 错误信息={res}')
            return jsonify({'status': 'fail'})

    return jsonify({'status': 'ok'})


@flash_app.route('/tv', methods=['POST'])
def tv():
    # 获取表单数据
    # 获取 season guid 和 media guid （可选，用于指定特定文件）
    season_guid = request.form.get('season_guid')
    base_url = request.form.get('base_url')
    hostname = request.form.get('hostname')
    token = request.form.get('token')

    set_global_info(base_url, token)

    # 根据 season_guid 获取当前播放集的guid
    success, res = fn_api('/v/api/v1/play/info', {'item_guid': season_guid})
    if not success:
        logger.error(f'获取season影视信息失败 - season_guid = {season_guid} 错误信息={res}')
        return jsonify({'status': 'fail'})
    item_guid = res['guid']
    season_guid = res['parent_guid']

    # 获取所有集信息，判断当前集索引
    success, res = fn_api(f'/v/api/v1/episode/list/{season_guid}', None)
    if not success or not res:
        logger.error(f'获取所有集信息失败 - season_guid = {season_guid} 错误信息={res}')
        return jsonify({'status': 'fail'})

    episode_list = res
    current_index = 0
    total_index = len(episode_list)
    for episode_index, episode in enumerate(episode_list):
        episode_guid = episode['guid']
        if episode_guid == item_guid:
            current_index = episode_index
            break

    last_stop_sec = 0
    last_episode_guid = ''
    last_media_guid = ''
    last_video_guid = ''
    last_audio_guid = ''
    last_subtitle_guid = ''
    all_finished = False
    while True:
        if current_index > total_index - 1:
            logger.info(f"检测到已播完全部 {current_index}/{total_index}")
            all_finished = True
            break
        current_episode = episode_list[current_index]
        episode_guid = current_episode['guid']
        # 根据 episode_guid 获取影视信息，包括播放开始时间，标题
        success, res = fn_api('/v/api/v1/play/info', {'item_guid': episode_guid})
        if not success or not check_key(res, 'item'):
            logger.error(f'获取episode影视信息失败 - episode_guid = {episode_guid} 错误信息={res}')
            return jsonify({'status': 'fail'})

        media_guid = res['media_guid'] or ''
        video_guid = res['video_guid'] or ''
        subtitle_guid = res['subtitle_guid'] or ''
        audio_guid = res['audio_guid'] or ''
        ts = res['ts']
        tv_title = res['item'].get('tv_title') or '某电视剧'
        season_number = res['item'].get('season_number') or '1'
        episode_number = res['item'].get('episode_number') or '1'
        title = res['item'].get('title') or ''
        title = f'{tv_title}-第{season_number}季-第{episode_number}集　{title}'
        duration = res['item']['duration']

        # 根据 item guid 获取文件流信息，拼接smb文件参数
        success, res = fn_api(f'/v/api/v1/stream/list/{episode_guid}', None)
        if not success or not check_key(res, 'files') or not check_key(res, 'video_streams'):
            logger.error(f'获取影视流信息失败 - item_guid = {item_guid} 错误信息={res}')
            return jsonify({'status': 'fail'})

        if media_guid == '':
            media_guid = res['files'][0]['guid']

        file_path = res['files'][0]['path']
        # 根据 media guid 获取 files 对象
        for file in res['files']:
            file_guid = file['guid']
            if file_guid == media_guid:
                file_path = file['path']
                break
        # 从 video_streams 获取准确的 duration
        for video in res['video_streams']:
            video_stream_guid = video['guid']
            if video_stream_guid == video_guid:
                duration = video['duration']

        old_path = file_path
        smb_url = convert_file_path(file_path, hostname)
        logger.info(f'获取到相关文件信息：{old_path}，SMB地址：{smb_url}')

        time_cmd = '/seek=' + seconds_to_hms(ts)
        title = '/title=' + title

        cmd = [pot_path, smb_url, time_cmd, title, '/config=fntv']
        logger.info(f'执行cmd，参数：{cmd}')
        try:
            player = subprocess.Popen(cmd)
        except Exception as e:
            logger.error(f'执行CMD报错：{e}')
            return jsonify({'status': 'fail'})

        activate_window_by_pid(player.pid, sleep=1)
        stop_sec = stop_sec_pot(player.pid)
        play_per = stop_sec / duration * 100

        # 时间异常
        if stop_sec == 1397424 or stop_sec > duration + 100:
            logger.error(f'时间异常 - stop_sec = {stop_sec} duration={duration}')
            return jsonify({'status': 'fail'})

        # 小于15s 或播放进度大于95%，视作下一集
        if (duration - stop_sec) < 15 or play_per > 93:
            current_index = current_index + 1
            logger.info(f'检测到已看完一集 stop_sec={stop_sec} duration={duration} curr_index={current_index}')
            # 播放下一集，将这集标记已观看
            success, res = fn_api(f'/v/api/v1/item/watched', {'item_guid': episode_guid})
            if not success:
                logger.error(f'更新已观看失败 - item_guid = {episode_guid} 错误信息={res}')
                return jsonify({'status': 'fail'})
        else:
            last_stop_sec = stop_sec
            last_episode_guid = episode_guid
            last_media_guid = media_guid
            last_video_guid = video_guid
            last_audio_guid = audio_guid
            last_subtitle_guid = subtitle_guid
            break

    if all_finished:
        return jsonify({'status': 'ok'})

    if last_stop_sec is None:
        return jsonify({'status': 'fail'})

    logger.info(f'检测到PotPlayer已关闭，关闭时进度为：{seconds_to_hms(last_stop_sec)}')

    # 修改时间
    success, res = fn_api('/v/api/v1/play/record',
                          {'item_guid': last_episode_guid, 'media_guid': last_media_guid, 'video_guid': last_video_guid,
                           'subtitle_guid': last_subtitle_guid, 'audio_guid': last_audio_guid,
                           'ts': last_stop_sec})
    if not success:
        logger.error(f'修改进度失败 - item_guid = {item_guid} stop_sec = {last_stop_sec} 错误信息={res}')
        return jsonify({'status': 'fail'})

    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    mode = os.environ.get("fnToPotPlayer-mode", "pro")
    if mode == 'dev':
        flash_app.run(host='0.0.0.0', port=5050, debug=True)
    else:
        flash_app.run(host='0.0.0.0', port=5050)
