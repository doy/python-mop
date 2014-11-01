import unittest

import mop

class MopTest(unittest.TestCase):
    def test_bootstrap(self):
        assert mop.Class is not None
        assert mop.Object is not None
        assert mop.Method is not None
        assert mop.Attribute is not None

        assert mop.Class.metaclass is mop.Class
        assert mop.Object.metaclass is mop.Class
        assert mop.Method.metaclass is mop.Class
        assert mop.Attribute.metaclass is mop.Class

        assert mop.Class.isa(mop.Object)
        assert mop.Class.isa(mop.Class)
        assert mop.Object.isa(mop.Object)
        assert mop.Object.isa(mop.Class)

        assert mop.Class.get_all_methods()["add_method"].isa(mop.Object)
        assert mop.Class.get_all_methods()["add_method"].isa(mop.Method)
        assert not mop.Class.get_all_methods()["add_method"].isa(mop.Class)

        assert mop.Class.get_all_attributes()["superclass"].isa(mop.Object)
        assert mop.Class.get_all_attributes()["superclass"].isa(mop.Attribute)
        assert not mop.Class.get_all_attributes()["superclass"].isa(mop.Class)

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

        assert Point.metaclass is mop.Class
        assert Point.isa(mop.Object)
        assert Point.get_superclass() is mop.Object
        assert Point.get_mro() == [ Point, mop.Object ]

        point = Point.new(x=1, y=2)
        assert point.isa(Point)
        assert point.metaclass is Point
        assert point.x() == 1
        assert point.y() == 2
        point.set_x(10)
        assert point.x() == 10

        point2 = Point.new(x=3, y=4)
        assert point is not point2
        assert point.x() == 10
        assert point.y() == 2
        assert point2.x() == 3
        assert point2.y() == 4

        Point3D = Point.metaclass.new(
            name="Point3D",
            superclass=Point,
        )
        Point3D.add_attribute(Point3D.attribute_class().new(name="z", default=0))
        Point3D.add_method(Point3D.method_class().new(
            name="z",
            body=lambda self: self.metaclass.get_all_attributes()["z"].get_value(self)
        ))
        Point3D.finalize()

        assert Point3D.metaclass is mop.Class
        assert Point3D.isa(mop.Object)
        assert Point3D.get_superclass() is Point
        assert Point3D.get_mro() == [ Point3D, Point, mop.Object ]

        point3d = Point3D.new(x=3, y=4, z=5)
        assert point3d.isa(Point3D)
        assert point3d.isa(Point)
        assert point3d.isa(mop.Object)
        assert point3d.x() == 3
        assert point3d.y() == 4
        assert point3d.z() == 5

        assert not point.can("z")
        assert point3d.can("z")

        assert point.isa(Point)
        assert point3d.isa(Point)
        assert not point.isa(Point3D)
        assert point3d.isa(Point3D)

        point_default = Point.new()
        assert point_default.x() == 0
        assert point_default.y() == 0
        point3d_default = Point3D.new()
        assert point3d_default.x() == 0
        assert point3d_default.y() == 0
