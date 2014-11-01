import unittest

import mop

from . import InMemoryDatabase

class DatabaseTest(unittest.TestCase):
    def test_database(self):
        db = InMemoryDatabase()

        db.insert("foo", {"a": 1, "b": 2})
        assert db.lookup("foo") == {"a": 1, "b": 2}
        assert db.store == {"foo": '{"data":{"a":1,"b":2},"type":"plain"}'}

        db.insert("foo", {"a": 3, "c": 5})
        assert db.lookup("foo") == {"a": 3, "c": 5}
        assert db.store == {"foo": '{"data":{"a":3,"c":5},"type":"plain"}'}

        db.insert("bar", [1, 2, "b"])
        assert db.lookup("foo") == {"a": 3, "c": 5}
        assert db.lookup("bar") == [1, 2, "b"]
        assert db.store == {
            "foo": '{"data":{"a":3,"c":5},"type":"plain"}',
            "bar": '{"data":[1,2,"b"],"type":"plain"}',
        }

        Point = mop.Class(
            name="Point",
            superclass=mop.Class.base_object_class(),
        )
        Point.add_attribute(Point.attribute_class()(name="x"))
        Point.add_attribute(Point.attribute_class()(name="y"))
        Point.add_method(Point.method_class()(
            name="x",
            body=lambda self: self.metaclass.all_attributes()["x"].value(self)
        ))
        Point.add_method(Point.method_class()(
            name="y",
            body=lambda self: self.metaclass.all_attributes()["y"].value(self)
        ))
        Point.finalize()

        point = Point(x=10, y=23)
        assert point.x() == 10
        assert point.y() == 23

        db.insert("p", point)
        point2 = db.lookup("p")
        assert point2.x() == 10
        assert point2.y() == 23
        assert point is not point2
        assert db.store == {
            "foo": '{"data":{"a":3,"c":5},"type":"plain"}',
            "bar": '{"data":[1,2,"b"],"type":"plain"}',
            "p": '{"class":"Point","data":{"x":10,"y":23},"type":"object"}',
        }
