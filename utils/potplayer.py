import time

from utils.logger import logger

prefetch_data = dict(on=True, running=False, stop_sec_dict={}, done_list=[])


def stop_sec_pot(pid, stop_sec_only=True, check_only=False, **_):
    if not pid:
        logger.error('pot pid not found skip stop_sec_pot')
        return None if stop_sec_only else {}
    import ctypes
    from utils.windows_tool import user32, EnumWindowsProc, process_is_running_by_pid

    def potplayer_time_title_updater(_pid):
        def send_message(hwnd):
            nonlocal stop_sec, name_stop_sec_dict, name_total_sec_dict
            target_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(target_pid))
            if _pid == target_pid.value:
                msg_cur_time = user32.SendMessageW(hwnd, 0x400, 0x5004, 1)
                if msg_cur_time:
                    if check_only:
                        stop_sec = 'check_only'
                        return
                    stop_sec = msg_cur_time // 1000

                    length = user32.GetWindowTextLengthW(hwnd)
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.replace(' - PotPlayer', '')
                    name_stop_sec_dict[title] = stop_sec
                    prefetch_data['stop_sec_dict'][title] = stop_sec

                    if not name_total_sec_dict.get(title):
                        msg_total_time = user32.SendMessageW(hwnd, 0x400, 0x5002, 1)
                        total_sec = msg_total_time // 1000
                        if total_sec != stop_sec:
                            name_total_sec_dict[title] = total_sec
                            if '.strm' in title:
                                logger.info(f'pot: get strm file {total_sec=}')

        def for_each_window(hwnd, _):
            send_message(hwnd)
            return True

        proc = EnumWindowsProc(for_each_window)
        user32.EnumWindows(proc, 0)

    stop_sec = None
    name_stop_sec_dict = {}
    name_total_sec_dict = {}
    while True:
        if not process_is_running_by_pid(pid):
            logger.debug('pot not running')
            break
        if check_only and stop_sec == 'check_only':
            return True
        potplayer_time_title_updater(pid)
        logger.debug(f'pot stop, {stop_sec=}')
        time.sleep(0.3)
    if check_only:
        return False
    logger.debug(f'pot stop, {stop_sec=}')
    return stop_sec if stop_sec_only else (name_stop_sec_dict, name_total_sec_dict)
