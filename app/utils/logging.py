import logging
from logging.handlers import RotatingFileHandler
import os

# LOG_DIR = "logs"
LOG_FILE = "app.log"

def setup_logging():
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, LOG_FILE)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] "
        "[%(filename)s:%(lineno)d] %(message)s"
    )

    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 文件 handler（自动切割）
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
