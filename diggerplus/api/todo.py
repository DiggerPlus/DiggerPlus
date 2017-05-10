# -*- coding: utf-8 -*-

import logging

from flask import Blueprint

from .base import (
    status_OK,
    status_Created,
    status_ResetContent,
    MethodView,
)
from ..models.todo import TODOModel
from ..exc import NotFoundException, ExistedException
from ..consts import ALREADY_EXISTS_MESSSAGE

logger = logging.getLogger(__name__)


bp = Blueprint('todos', __name__, url_prefix='/api')


class TODOS(MethodView):
    blueprint = bp
    url_rules = ['/todos/<title>', '/todos']
    logger = logger

    shields = ['created_at', 'updated_at']

    def get(self, title=None):
        if title is None:
            todos = TODOModel.get_all()
            return status_OK([todo.to_dict(self.shields) for todo in todos])
        todo = TODOModel.get_by_title(title)
        if todo:
            return status_OK(todo.to_dict(self.shields))
        raise NotFoundException("TODO: {!r} not found!".format(title))

    def post(self, title=None):
        title = title or self.get_key('title', required=True)
        todo = TODOModel.get_by_title(title)
        if todo:
            raise ExistedException(
                ALREADY_EXISTS_MESSSAGE.format(self.__class__.__name__, title))
        TODOModel.add(title=title)
        return status_Created()

    def put(self, title=None):
        title = title or self.get_key('title', required=True)
        is_done = self.get_key('is_done', required=True)
        todo = TODOModel.get_by_title(title)
        if todo:
            todo.update(title=title, is_done=is_done)
            return status_ResetContent()
        raise NotFoundException("TODO: {!r} not found!".format(title))
