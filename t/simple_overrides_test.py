import unittest

import mop

# in a real implementation, we'd add more functionality to the mop itself to
# allow for calling superclass methods, but that would be complicated enough to
# obscure the implementation and make it not as easy to follow (we would have
# to manage call stacks ourselves), and so we just do this instead for now
def call_method_at_class(c, method_name, invocant, *args, **kwargs):
    return c.get_all_methods()[method_name].slots["body"](
        invocant, *args, **kwargs
    )

class SimpleOverridesTest(unittest.TestCase):
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
