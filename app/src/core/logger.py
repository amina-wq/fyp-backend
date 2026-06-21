from logging import config as logging_config

from src.core.config import settings

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

LOG_DEFAULT_HANDLERS = [
    'console',
]


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': LOG_FORMAT,
        },
        'default': {
            '()': 'uvicorn.logging.DefaultFormatter',
            'fmt': '%(levelprefix)s %(message)s',
            'use_colors': None,
        },
        'access': {
            '()': 'uvicorn.logging.AccessFormatter',
            'fmt': "%(levelprefix)s %(client_addr)s - '%(request_line)s' %(status_code)s",
        },
    },
    'handlers': {
        'console': {
            'level': settings.LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'default': {
            'formatter': 'default',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
        'access': {
            'formatter': 'access',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        '': {
            'handlers': LOG_DEFAULT_HANDLERS,
            'level': settings.LOGGING_LEVEL,
        },
        'uvicorn.error': {
            'level': settings.LOGGING_LEVEL,
        },
        'uvicorn.access': {
            'handlers': ['access'],
            'level': settings.LOGGING_LEVEL,
            'propagate': False,
        },
    },
    'root': {
        'level': settings.LOGGING_LEVEL,
        'handlers': LOG_DEFAULT_HANDLERS,
    },
}


def setup_logging() -> None:
    logging_config.dictConfig(LOGGING)
