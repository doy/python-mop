# Phase 0: absolute basics that we must start with

Class     = None
Object    = None
Method    = None
Attribute = None

class BasicInstance(object):
    def __init__(self, metaclass, slots):
        self.metaclass = metaclass
        self.slots = slots

UNDERLYING_CLASSES = {}
def bootstrap_underlying_class_for(c):
    name = c.slots["name"]
    if name not in UNDERLYING_CLASSES.keys():
        UNDERLYING_CLASSES[name] = type(name, (object,), {})
    return UNDERLYING_CLASSES[name]

def bootstrap_create_class(name, superclass):
    return BasicInstance(
        globals().get("Class"),
        {
            "name": name,
            "superclass": superclass,
            "methods": {},
            "attributes": {},
        },
    )

def bootstrap_create_method(name, body):
    return BasicInstance(
        globals().get("Method"),
        {
            "name": name,
            "body": body,
        }
    )

def bootstrap_create_attribute(name):
    return BasicInstance(
        globals().get("Attribute"),
        {
            "name": name,
        }
    )

def bootstrap_class_add_method(self, method):
    name = method.slots["name"]
    self.slots["methods"][name] = method
    method.__class__ = bootstrap_underlying_class_for(Method)
    setattr(bootstrap_underlying_class_for(self), name, lambda self, *args, **kwargs: method.execute(self, args, kwargs))

def bootstrap_method_execute(method, invocant, args, kwargs):
    return method.slots["body"](invocant, *args, **kwargs)

def bootstrap():
    # Phase 1: construct the core classes

    global Class, Object, Method, Attribute

    Class     = bootstrap_create_class('Class', None)
    Object    = bootstrap_create_class('Object', None)
    Method    = bootstrap_create_class('Method', Object)
    Attribute = bootstrap_create_class('Attribute', Object)

    Class.slots["methods"]["add_method"] = bootstrap_create_method(
        "add_method", bootstrap_class_add_method
    )
    Method.slots["methods"]["execute"] = bootstrap_create_method(
        "execute", bootstrap_method_execute
    )

    # Phase 2: tie the knot

    Class.metaclass = Class
    Class.slots["superclass"] = Object

    # Phase 3: associate the core classes with their underlying method table

    Class.__class__     = bootstrap_underlying_class_for(Class)
    Object.__class__    = bootstrap_underlying_class_for(Class)
    Method.__class__    = bootstrap_underlying_class_for(Class)
    Attribute.__class__ = bootstrap_underlying_class_for(Class)

    m1 = Class.slots["methods"]["add_method"]
    m1.metaclass = Method
    m1.__class__ = bootstrap_underlying_class_for(Method)
    setattr(bootstrap_underlying_class_for(Class), "add_method", lambda self, *args, **kwargs: m1.execute(self, args, kwargs))

    # note: not using method.execute here, since this is the recursion base case
    m2 = Method.slots["methods"]["execute"]
    m2.metaclass = Method
    m2.__class__ = bootstrap_underlying_class_for(Method)
    setattr(bootstrap_underlying_class_for(Method), "execute", bootstrap_method_execute)

    # Phase 4: manually assemble enough scaffolding to allow object construction

    def gen_reader(name):
        return lambda self: self.slots[name]

    Class.add_method(bootstrap_create_method("get_superclass", gen_reader("superclass")))

    def get_mro(self):
        mro = [ self ]
        parent = self.get_superclass()
        if parent:
            mro.extend(parent.get_mro())
        return mro
    Class.add_method(bootstrap_create_method("get_mro", get_mro))

    Class.add_method(bootstrap_create_method("get_local_attributes", gen_reader("attributes")))

    def get_all_attributes(self):
        attributes = {}
        for c in reversed(self.get_mro()):
            attributes.update(c.get_local_attributes())
        return attributes
    Class.add_method(bootstrap_create_method("get_all_attributes", get_all_attributes))

    def create_instance(self, kwargs):
        slots = {}
        for attr_name in self.get_all_attributes():
            if attr_name in kwargs.keys():
                slots[attr_name] = kwargs[attr_name]
        instance = BasicInstance(self, slots)
        instance.__class__ = bootstrap_underlying_class_for(self)
        return instance
    Class.add_method(bootstrap_create_method("create_instance", create_instance))

    def new(self, **kwargs):
        return self.create_instance(kwargs)
    Class.add_method(bootstrap_create_method('new', new))

    # Phase 5: Object construction works, just need attributes to construct with

    Attribute.add_method(bootstrap_create_method("get_name", gen_reader("name")))

    def add_attribute(self, attr):
        self.get_local_attributes()[attr.get_name()] = attr
    Class.add_method(bootstrap_create_method("add_attribute", add_attribute))

    attr_name = bootstrap_create_attribute("name")
    attr_name.__class__ = bootstrap_underlying_class_for(Attribute)
    Attribute.add_attribute(attr_name)

    # and now object creation works!
    Method.add_attribute(Attribute.new(name="name"))
    Method.add_attribute(Attribute.new(name="body"))

    # Phase 6: now we can populate the rest of the mop

    Class.add_method(Method.new(name="attribute_class", body=lambda self: Attribute))
    Class.add_method(Method.new(name="method_class", body=lambda self: Method))
    Class.add_method(Method.new(name="base_object_class", body=lambda self: Object))

    Class.add_method(Method.new(name="get_name", body=gen_reader("name")))

    Class.add_method(Method.new(name="get_local_methods", body=gen_reader("methods")))

    def get_all_methods(self):
        methods = {}
        for c in reversed(self.get_mro()):
            methods.update(c.get_local_methods())
        return methods
    Class.add_method(Method.new(name="get_all_methods", body=get_all_methods))

    Method.add_method(Method.new(name="get_name", body=gen_reader("name")))
    Method.add_method(Method.new(name="get_body", body=gen_reader("body")))

    Class.add_attribute(Attribute.new(name="name"))
    Class.add_attribute(Attribute.new(name="superclass"))
    Class.add_attribute(Attribute.new(name="attributes"))
    Class.add_attribute(Attribute.new(name="methods"))

    def isa(self, other):
        mro = self.metaclass.get_mro()
        return other in mro
    Object.add_method(Method.new(name="isa", body=isa))

    def can(self, method_name):
        return self.metaclass.get_all_methods().get(method_name)
    Object.add_method(Method.new(name="can", body=can))

    # Phase 7: now we have to clean up after ourselves

    for c in [ Class, Object, Method, Attribute ]:
        for method in c.get_local_methods().values():
            method.__class__ = bootstrap_underlying_class_for(Method)
        for attribute in c.get_local_attributes().values():
            attribute.__class__ = bootstrap_underlying_class_for(Attribute)

    for method in Object.get_local_methods().values():
        setattr(bootstrap_underlying_class_for(Class), method.get_name(), lambda self, *args, **kwargs: method.execute(self, args, kwargs))
        setattr(bootstrap_underlying_class_for(Method), method.get_name(), lambda self, *args, **kwargs: method.execute(self, args, kwargs))
        setattr(bootstrap_underlying_class_for(Attribute), method.get_name(), lambda self, *args, **kwargs: method.execute(self, args, kwargs))

    def add_method(self, method):
        self.slots["methods"][method.get_name()] = method
    Class.add_method(Method.new(name="add_method", body=add_method))

bootstrap()
