
import logging
from logging.handlers import RotatingFileHandler


logger = logging.getLogger('rotating_logger')
logger.setLevel(logging.INFO)

# 按文件大小轮换 (最大1MB，保留3个备份)
rotating_handler = RotatingFileHandler(
    'ffmpeg.log', maxBytes=10 * 1024 * 1024, backupCount=5
)

formatter = logging.Formatter('%(message)s')
rotating_handler.setFormatter(formatter)
logger.addHandler(rotating_handler)