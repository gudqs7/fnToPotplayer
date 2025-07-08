import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('fnToPotPlayer')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 按文件大小轮换 (最大1MB，保留3个备份)
rotating_handler = RotatingFileHandler(
    'fnToPotPlayer.log', maxBytes=10 * 1024 * 1024, backupCount=5, encoding='UTF-8'
)
console_handler = logging.StreamHandler()

rotating_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(rotating_handler)
logger.addHandler(console_handler)
