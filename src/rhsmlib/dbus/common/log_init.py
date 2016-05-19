import logging

logger_initialized = False


def init_root_logger():
    global logger_initialized
    if logger_initialized:
        return
    # Set up root logger for debug purposes
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)

    logger_initialized = True
