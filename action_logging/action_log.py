import logging
from logging.handlers import TimedRotatingFileHandler


def log():
    # 创建logger，如果参数为空则返回root logger
    logger = logging.getLogger("hawk")
    logger.setLevel(logging.DEBUG)  # 设置logger日志等级

    # 这里进行判断，如果logger.handlers列表为空，则添加，否则，直接去写日志
    if not logger.handlers:
        # 创建handler
        fh = TimedRotatingFileHandler(filename="./action_logging/log_text.log", when="D", interval=1,
                                 backupCount=7, encoding='utf-8')

    # 设置输出日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %X"
    )

    # 为handler指定输出格式
    fh.setFormatter(formatter)

    # 为logger添加的日志处理器
    logger.addHandler(fh)

    return logger  # 直接返回logger

logger = log()
