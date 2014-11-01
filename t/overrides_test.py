import unittest

import mop

from . import InMemoryDatabase

# in a real implementation, we'd add more functionality to the mop itself to
# allow for calling superclass methods, but that would be complicated enough to
# obscure the implementation and make it not as easy to follow (we would have
# to manage call stacks ourselves), and so we just do this instead for now
def call_method_at_class(c, method_name, invocant, *args, **kwargs):
    return c.get_all_methods()[method_name].slots["body"](
        invocant, *args, **kwargs
    )

class OverridesTest(unittest.TestCase):
    def test_accessor_generation(self):
        AccessorsMetaclass = mop.Class.new(
            name="AccessorsMetaclass",
            superclass=mop.Class,
        )
        def add_attribute(self, attr):
            name = attr.get_name()
            call_method_at_class(mop.Class, "add_attribute", self, attr)
            self.add_method(self.method_class().new(
                name=name,
                body=lambda self: self.metaclass.get_all_attributes()[name].get_value(self),
            ))
        AccessorsMetaclass.add_method(AccessorsMetaclass.metaclass.method_class().new(
            name="add_attribute",
            body=add_attribute,
        ))
        AccessorsMetaclass.finalize()

        Point = AccessorsMetaclass.new(
            name="Point",
            superclass=AccessorsMetaclass.base_object_class(),
        )
        Point.add_attribute(Point.attribute_class().new(name="x", default=0))
        Point.add_attribute(Point.attribute_class().new(name="y", default=0))
        Point.finalize()

        point = Point.new(x=1, y=2)
        assert point.x() == 1
        assert point.y() == 2

    def test_trace_method_calls(self):
        methods_called = []

        TraceMethod = mop.Class.new(
            name="TraceMethod",
            superclass=mop.Method,
        )

        def execute(self, invocant, args, kwargs):
            methods_called.append(self.get_name())
            return call_method_at_class(mop.Method, "execute", self, invocant, args, kwargs)
        TraceMethod.add_method(TraceMethod.metaclass.method_class().new(
            name="execute",
            body=execute,
        ))
        TraceMethod.finalize()

        TraceClass = mop.Class.new(
            name="TraceClass",
            superclass=mop.Class,
        )
        TraceClass.add_method(TraceClass.metaclass.method_class().new(
            name="method_class",
            body=lambda self: TraceMethod,
        ))
        TraceClass.finalize()

        Point = TraceClass.new(
            name="Point",
            superclass=TraceClass.base_object_class(),
        )
        Point.add_attribute(Point.attribute_class().new(name="x", default=0))
        Point.add_attribute(Point.attribute_class().new(name="y", default=0))
        Point.add_method(Point.method_class().new(
            name="x",
            body=lambda self: self.metaclass.get_all_attributes()["x"].get_value(self)
        ))
        Point.add_method(Point.method_class().new(
            name="y",
            body=lambda self: self.metaclass.get_all_attributes()["y"].get_value(self)
        ))
        Point.finalize()

        point = Point.new(x=1, y=2)
        assert methods_called == []
        assert point.x() == 1
        assert methods_called == ['x']
        assert point.y() == 2
        assert methods_called == ['x', 'y']

    def test_db_backed_object(self):
        DatabaseAttribute = mop.Class.new(
            name="DatabaseAttribute",
            superclass=mop.Attribute,
        )
        DatabaseAttribute.add_attribute(DatabaseAttribute.attribute_class().new(
            name="db",
        ))
        DatabaseAttribute.add_method(DatabaseAttribute.method_class().new(
            name="db",
            body=lambda self: self.metaclass.get_all_attributes()["db"].get_value(self)
        ))
        def get_value(self, instance):
            key = str(instance.__hash__()) + ":" + self.get_name()
            return self.db().lookup(key)
        DatabaseAttribute.add_method(DatabaseAttribute.method_class().new(
            name="get_value",
            body=get_value,
        ))
        def set_value(self, instance, new_value):
            key = str(instance.__hash__()) + ":" + self.get_name()
            self.db().insert(key, new_value)
        DatabaseAttribute.add_method(DatabaseAttribute.method_class().new(
            name="set_value",
            body=set_value,
        ))
        DatabaseAttribute.finalize()

        DatabaseBackedClass = mop.Class.new(
            name="DatabaseBackedClass",
            superclass=mop.Class,
        )
        DatabaseBackedClass.add_attribute(DatabaseBackedClass.attribute_class().new(
            name="db",
        ))
        DatabaseBackedClass.add_method(DatabaseBackedClass.method_class().new(
            name="db",
            body=lambda self: self.metaclass.get_all_attributes()["db"].get_value(self)
        ))
        def add_attribute(self, attr):
            attr.metaclass.get_all_attributes()["db"].set_value(attr, self.db())
            call_method_at_class(mop.Class, "add_attribute", self, attr)
        DatabaseBackedClass.add_method(DatabaseBackedClass.method_class().new(
            name="add_attribute",
            body=add_attribute,
        ))
        DatabaseBackedClass.add_method(DatabaseBackedClass.method_class().new(
            name="attribute_class",
            body=lambda self: DatabaseAttribute,
        ))
        DatabaseBackedClass.finalize()

        Point = DatabaseBackedClass.new(
            name="Point",
            superclass=DatabaseBackedClass.base_object_class(),
            db=InMemoryDatabase(),
        )
        Point.add_attribute(Point.attribute_class().new(name="x", default=0))
        Point.add_attribute(Point.attribute_class().new(name="y", default=0))
        Point.add_method(Point.method_class().new(
            name="x",
            body=lambda self: self.metaclass.get_all_attributes()["x"].get_value(self)
        ))
        Point.add_method(Point.method_class().new(
            name="y",
            body=lambda self: self.metaclass.get_all_attributes()["y"].get_value(self)
        ))
        Point.add_method(Point.method_class().new(
            name="set_x",
            body=lambda self, new_value: self.metaclass.get_all_attributes()["x"].set_value(self, new_value)
        ))
        Point.finalize()

        point = Point.new(x=3, y=7)
        assert point.x() == 3
        assert point.y() == 7
        assert point.slots == {}
        point.set_x(12)
        assert point.x() == 12
        assert point.y() == 7
        assert point.slots == {}
        assert len(Point.db().store) == 2

        point2 = Point.new(x=123, y=-5)
        assert point.x() == 12
        assert point.y() == 7
        assert point.slots == {}
        assert point2.x() == 123
        assert point2.y() == -5
        assert point2.slots == {}
        assert len(Point.db().store) == 4