# -*- coding: utf-8 -*-

import math
import datetime
import hashlib

from dogpile.cache.region import make_region
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import (
    Column,
    BigInteger,
    DateTime,
)

from diggerplus.db import mode_base, db_manager
from diggerplus.settings import cache_config
from .cache.caching_query import CachingQuery, FromCache


ModelBase = mode_base()
DBSession = db_manager.get_session('diggerplus')


def md5_key_mangler(key):
    if key.startswith('SELECT '):
        key = hashlib.md5(key.encode('ascii')).hexdigest()
    return key


regions = dict(
    default=make_region(key_mangler=md5_key_mangler).configure(**cache_config)
)


class Pagination(object):
    """Internal helper class returned by :meth:`BaseQuery.paginate`.  You
    can also construct it from any other SQLAlchemy query object if you are
    working with other libraries.  Additionally it is possible to pass `None`
    as query object in which case the :meth:`prev` and :meth:`next` will
    no longer work.
    """

    def __init__(self, query, page, per_page, total, items):
        #: the unlimited query object that was used to create this
        #: pagination object.
        self.query = query
        #: the current page number (1 indexed)
        self.page = page
        #: the number of items to be displayed on a page.
        self.per_page = per_page
        #: the total number of items matching the query
        self.total = total
        #: the items for the current page
        self.items = items

    @property
    def pages(self):
        """The total number of pages"""
        if self.per_page == 0:
            pages = 0
        else:
            pages = int(math.ceil(self.total / float(self.per_page)))
        return pages

    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.query is not None, 'a query object is required ' \
                                       'for this method to work'
        return self.query.paginate(self.page - 1, self.per_page, error_out)

    @property
    def prev_num(self):
        """Number of the previous page."""
        if not self.has_prev:
            return None
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.query is not None, 'a query object is required ' \
                                       'for this method to work'
        return self.query.paginate(self.page + 1, self.per_page, error_out)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        if not self.has_next:
            return None
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        This is how you could render such a pagination in the templates:
        .. sourcecode:: html+jinja
            {% macro render_pagination(pagination, endpoint) %}
              <div class=pagination>
              {%- for page in pagination.iter_pages() %}
                {% if page %}
                  {% if page != pagination.page %}
                    <a href="{{ url_for(endpoint, page=page) }}">{{ page }}</a>
                  {% else %}
                    <strong>{{ page }}</strong>
                  {% endif %}
                {% else %}
                  <span class=ellipsis>…</span>
                {% endif %}
              {%- endfor %}
              </div>
            {% endmacro %}
        """
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


class Query(CachingQuery):
    """SQLAlchemy :class:`~sqlalchemy.orm.query.Query` subclass with
    convenience methods for querying in a web application. This is the
    default :attr:`~Model.query` object used for models, and exposed as
    :attr:`~SQLAlchemy.Query`. Override the query class for an individual
    model by subclassing this and setting :attr:`~Model.query_class`.
    """

    def paginate(self, page, per_page):
        items = self.limit(per_page).offset((page - 1) * per_page).all()
        if page == 1 and len(items) < per_page:
            total = len(items)
        else:
            total = self.order_by(None).count()

        return Pagination(self, page, per_page, total, items)


def query_callable(regions, query_cls=Query):
    def query(*args, **kwargs):
        return query_cls(regions, *args, **kwargs)
    return query


class Model(ModelBase):

    __abstract__ = True
    query = DBSession.query_property(query_cls=query_callable(regions))

    @classmethod
    def from_cache(cls):
        """query from cache, set cache if missing."""
        return cls.query.options(FromCache())

    @declared_attr
    def id(cls):
        return Column('id', BigInteger, primary_key=True, autoincrement=True,
                      nullable=False)

    @declared_attr
    def created_at(cls):
        # `sqlalchemy.sql.func.now()` `sqlalchemy.sql.func.utc_timestamp()`
        return Column('created_at', DateTime, nullable=False, index=True,
                      default=datetime.datetime.now())

    @declared_attr
    def updated_at(cls):
        return Column('updated_at', DateTime, nullable=False, index=True,
                      default=datetime.datetime.now(),
                      onupdate=datetime.datetime.now())

    @classmethod
    def count(cls):
        return cls.query.count()

    @classmethod
    def get_all(cls):
        """return iteritor"""
        return cls.query

    @classmethod
    def get(cls, _id):
        return cls.query.filter(cls.id==_id).first()

    @classmethod
    def get_multi(cls, *ids):
        return [cls.get(_id) for _id in ids]

    @classmethod
    def add(cls, **kwargs):
        ins = cls(**kwargs)
        with DBSession() as session:
            session.add(ins)
        return ins

    def update(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        with DBSession() as session :
            session.add(self)

    def delete(self):
        with DBSession() as session:
            session.delete(self)

    def to_dict(self, shields=None):
        if shields is None:
            shields = []
        return {
            c.name: getattr(self, c.name, None)
            for c in self.__table__.columns if c.name not in shields
        }
