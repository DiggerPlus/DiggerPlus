# -*- coding: utf-8 -*-

import functools

from sqlalchemy.exc import SQLAlchemyError

from werkzeug.local import Local
from werkzeug.exceptions import HTTPException
from flask import current_app, request, json, Blueprint
from flask.views import View

from ..exc import EmptyFieldsException


req = Local()


def status(code):
    def response(*args, **kwargs):
        if args and kwargs:
            raise TypeError("Cannot pass both args and kwargs.")
        elif len(args) == 1:
            data = args[0]
        else:
            data = args or kwargs

        if data:
            data = (json.dumps(data), '\n')
        else:
            data = None

        return current_app.response_class(
            response=data,
            status=code,
            mimetype=current_app.config['JSONIFY_MIMETYPE']
        )
    return response

status_OK = status(200)
status_Created = status(201)
status_NoContent = status(204)
status_ResetContent = status(205)


def mv_register(app_or_bp, cls):
    # support multi routing in one view!
    endpoint = getattr(cls, 'endpoint', cls.__name__)
    view_func = cls.as_view(endpoint)
    for url_rule in cls.url_rules:
        app_or_bp.add_url_rule(
            rule=url_rule,
            view_func=view_func,
            methods=cls.methods
        )
    return cls


def with_error_response(logger):
    def _deco(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException as exc:
                logger.exception("Tolerated error: %s", exc)
                raise
            except SQLAlchemyError as exc:
                logger.exception("SQLAlchemy error: %s", exc)
                raise
            except Exception as exc:
                logger.exception("Unknown error: %s", exc)
                raise
        return _wrapper
    return _deco


class ViewMeta(type):
    SUPPORT_METHODS = frozenset([
        'get', 'post', 'patch', 'put', 'head', 'delete', 'options'
    ])

    def __new__(cls, cls_name, bases, attrs):

        def _deco(method):
            @functools.wraps(method)
            def _wrapper(self, *args, **kwargs):
                logger = getattr(self, 'logger', None)
                meth = method
                if logger is not None:
                    meth = with_error_response(logger)(meth)
                return meth(self, *args, **kwargs)
            return _wrapper

        rv = type.__new__(cls, cls_name, bases, attrs)
        rv.request = req

        # wrapper HTTP methods
        methods = getattr(rv, 'methods', None) or []
        for name in cls.SUPPORT_METHODS:
            method = getattr(rv, name, None)
            if method is None:
                continue

            if name not in methods:
                methods.append(name.upper())
                setattr(rv, name, _deco(method))
        rv.methods = sorted(methods)

        bp = getattr(rv, 'blueprint', None)
        if bp is not None:
            mv_register(bp, rv)
        return rv


class ParserMixin(object):
    """Parser mixin for parser parameters via `request`, also support
    validation fields.
    """

    @staticmethod
    def get_key(key, required=False):
        data = request.get_json(force=True, silent=True)
        if not data:
            data = request.values.to_dict()
        if not data:
            raise EmptyFieldsException("Empty fields!")
        try:
            return data[key]
        except KeyError:
            if required:
                raise EmptyFieldsException(
                    "Field {!r} cannot be empty".format(key))
            return None


class MethodView(ParserMixin, View):
    __metaclass__ = ViewMeta

    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)
        assert meth is not None, "Unimplemented method %r" % meth
        return meth(*args, **kwargs)


class Blueprint_v1(Blueprint):
    """Api version v1.

    api: http://host:port/api/v1/your_api
    """

    def __init__(self, *args, **kwargs):
        super(Blueprint_v1, self).__init__(
            *args, url_prefix='/api/v1', **kwargs
        )
