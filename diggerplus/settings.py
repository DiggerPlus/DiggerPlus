# -*- coding: utf-8 -*-

_master = "mysql+pymysql://root@localhost:3306/diggerplus?charset=utf8"
_slave = "mysql+pymysql://root@localhost:3306/diggerplus?charset=utf8"

DEFAULT_DB_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = -1
DEFAULT_POOL_RECYCLE = 1200

DB_SETTINGS = {
    "diggerplus": {
        "urls": {
            "master": _master,
            "slave": _slave
        },
        "max_overflow": -1,
        "pool_size": 10,
        "pool_recycle": 1200
    }
}

cache_config = {
    'backend': 'dogpile.cache.redis',
    'expiration_time': 3600  # 1 hour
}
