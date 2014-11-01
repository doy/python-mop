import unittest

import collections

from . import InMemoryDatabase

class DictProxy(collections.MutableMapping):
    def __init__(self):
        self.store = {}
    def __len__(self):
        return len(self.store)
    def __iter__(self):
        return iter(self.store)
    def __getitem__(self, key):
        return self.store[key]
    def __setitem__(self, key, new_value):
        self.store[key] = new_value
    def __delitem__(self, key):
        del self.store[key]

class PythonTest(unittest.TestCase):
    def test_accessor_generation(self):
        class AccessorsDict(DictProxy):
            def __setitem__(self, key, new_value):
                if not callable(new_value):
                    self.store["get_" + key] = lambda self: getattr(self, key)
                super().__setitem__(key, new_value)

        class AccessorsMetaclass(type):
            @classmethod
            def __prepare__(metacls, name, bases, **kwds):
                return AccessorsDict()
            def __new__(cls, name, bases, namespace, **kwds):
                return super().__new__(cls, name, bases, namespace.store)

        class Point(object, metaclass=AccessorsMetaclass):
            x = 0
            y = 0
            def distance(self):
                import math
                return math.sqrt(pow(self.get_x(), 2) + pow(self.get_y(), 2))

        point = Point()
        point.x = 3
        point.y = 4
        assert point.get_x() == 3
        assert point.get_y() == 4
        assert point.distance() == 5

    def test_trace_method_calls(self):
        methods_called = []

        class TraceDict(DictProxy):
            def __setitem__(self, key, new_value):
                if callable(new_value):
                    def trace_wrapper(self, *args, **kwargs):
                        methods_called.append(new_value.__name__)
                        return new_value(self, *args, **kwargs)
                    to_set = trace_wrapper
                else:
                    to_set = new_value
                super().__setitem__(key, to_set)

        class TraceClass(type):
            @classmethod
            def __prepare__(metacls, name, bases, **kwds):
                return TraceDict()
            def __new__(cls, name, bases, namespace, **kwds):
                return super().__new__(cls, name, bases, namespace.store)

        class Point(object, metaclass=TraceClass):
            def get_x(self):
                return self.x
            def get_y(self):
                return self.y

        point = Point()
        point.x = 2
        point.y = 3
        assert methods_called == []
        assert point.get_x() == 2
        assert methods_called == ['get_x']
        assert point.get_y() == 3
        assert methods_called == ['get_x', 'get_y']

    def test_db_backed_object(self):
        class DatabaseDict(DictProxy):
            def __init__(self, db):
                super().__init__()
                self.store["db"] = db
                def __getattr__(self, name):
                    db_key = str(hash(self)) + ":" + name
                    return self.db.lookup(db_key)
                self.store["__getattr__"] = __getattr__
                def __setattr__(self, name, new_value):
                    db_key = str(hash(self)) + ":" + name
                    self.db.insert(db_key, new_value)
                self.store["__setattr__"] = __setattr__

        class DatabaseBackedClass(type):
            @classmethod
            def __prepare__(metacls, name, bases, **kwds):
                return DatabaseDict(kwds["db"])
            def __new__(cls, name, bases, namespace, **kwds):
                return super().__new__(cls, name, bases, namespace.store)
            def __init__(cls, name, bases, namespace, **kwds):
                super().__init__(name, bases, namespace)

        class Point(object, metaclass=DatabaseBackedClass, db=InMemoryDatabase()):
            def get_x(self):
                return self.x
            def get_y(self):
                return self.y
            def set_x(self, new_value):
                self.x = new_value

        point = Point()
        point.x = 3
        point.y = 7
        assert point.get_x() == 3
        assert point.get_y() == 7
        assert point.__dict__ == {}
        point.set_x(12)
        assert point.get_x() == 12
        assert point.get_y() == 7
        assert point.__dict__ == {}
        assert len(Point.db.store) == 2

        point2 = Point()
        point2.x = 123
        point2.y = -5
        assert point.get_x() == 12
        assert point.get_y() == 7
        assert point.__dict__ == {}
        assert point2.get_x() == 123
        assert point2.get_y() == -5
        assert point2.__dict__ == {}
        assert len(Point.db.store) == 4
