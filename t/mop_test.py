import unittest

import mop

class MopTest(unittest.TestCase):
    def test_bootstrap(self):
        assert mop.Class is not None
        assert mop.Object is not None
        assert mop.Method is not None
        assert mop.Attribute is not None

        assert mop.Object.metaclass is mop.Class
        assert mop.Class.metaclass is mop.Class

        assert mop.Object in mop.Class.get_mro()
        assert mop.Class in mop.Class.get_mro()
        assert mop.Object in mop.Object.get_mro()
        assert mop.Class not in mop.Object.get_mro()

        # XXX no idea what's going on here
        # assert mop.Class.isa(mop.Object)
        # assert mop.Class.isa(mop.Class)
        # assert mop.Object.isa(mop.Object)
        # assert not mop.Object.isa(mop.Class)

        assert mop.Method.metaclass is mop.Class
        assert mop.Attribute.metaclass is mop.Class

        assert mop.Object in mop.Method.get_mro()
        assert mop.Object in mop.Attribute.get_mro()

        assert mop.Class.get_name() == "Class"
        assert mop.Object.get_name() == "Object"
        assert mop.Method.get_name() == "Method"
        assert mop.Attribute.get_name() == "Attribute"

        assert mop.Class.get_superclass() is mop.Object
        assert mop.Object.get_superclass() is None
        assert mop.Method.get_superclass() is mop.Object
        assert mop.Attribute.get_superclass() is mop.Object

        assert mop.Class.get_mro() == [ mop.Class, mop.Object ]
        assert mop.Object.get_mro() == [ mop.Object ]
        assert mop.Method.get_mro() == [ mop.Method, mop.Object ]
        assert mop.Attribute.get_mro() == [ mop.Attribute, mop.Object ]

    def test_class_creation(self):
        Point = mop.Class.new(
            name="Point",
            superclass=mop.Class.base_object_class()
        )

        Point.add_attribute(Point.attribute_class().new(name="x"))
        Point.add_attribute(Point.attribute_class().new(name="y"))

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
        assert point.x() == 1
        assert point.y() == 2

        Point3D = Point.metaclass.new(
            name="Point3D",
            superclass=Point,
        )
        Point3D.add_attribute(Point3D.attribute_class().new(name="z"))
        Point3D.add_method(Point3D.method_class().new(
            name="z",
            body=lambda self: self.metaclass.get_all_attributes()["z"].get_value(self)
        ))
        Point3D.finalize()

        point3d = Point3D.new(x=3, y=4, z=5)
        assert point3d.x() == 3
        assert point3d.y() == 4
        assert point3d.z() == 5

        assert not point.can("z")
        assert point3d.can("z")
