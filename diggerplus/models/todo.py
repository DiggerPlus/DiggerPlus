# -*- coding: utf-8 -*-

from sqlalchemy import (
    Column,
    String,
    SmallInteger
)

from .base import Model


class TODOModel(Model):

    __tablename__ = 'todo'

    title = Column(String, default="")
    is_done = Column(SmallInteger, default=0)

    @classmethod
    def get_by_title(cls, title):
        return cls.from_cache().filter(cls.title==title).first()
