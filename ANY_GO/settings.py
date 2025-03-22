# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '192.168.110.13',  # 添加你的局域网IP
    '*',  # 允许所有主机（仅在开发环境中使用）
] 

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'  # 使用stdout而不是stderr
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
            'formatter': 'standard',
            'encoding': 'utf-8'  # 明确指定UTF-8编码
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        },
        'erp': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
} 