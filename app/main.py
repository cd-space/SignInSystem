import logging
from .logs.logging import setup_logging
from .db.init_db import create_student_table




def main():
    setup_logging()
    logger = logging.getLogger()

    logger.info("程序启动")
    create_student_table()



if __name__ == '__main__':
    main()