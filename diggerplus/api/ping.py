# -*- coding: utf-8 -*-

import logging

from diggerplus import __version__
from .base import status_OK, MethodView, Blueprint_v1


logger = logging.getLogger(__name__)

bp = Blueprint_v1('ping', __name__)


class Ping(MethodView):
    blueprint = bp
    url_rules = ['/ping']
    logger = logger

    def get(self):
        return status_OK({'version': __version__})
