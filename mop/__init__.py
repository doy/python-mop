# Phase 0: absolute basics that we must start with

# things that must be provided by the underlying system: a place to store the
# mop itself, a data structure for instance data (with no associated behavior),
# and a way to run a chunk of code, given an invocant and argument list
Class     = None
Object    = None
Method    = None
Attribute = None

class BasicInstance(object):
    def __init__(self, metaclass, slots):
        self.metaclass = metaclass
        self.slots = slots

def execute_method(method, invocant, args, kwargs):
    return method.slots["body"](invocant, *args, **kwargs)

# shim layer to interface with python - in a real system, this wouldn't be
# necessary, but this allows us to pass python-level method calls through to
# our mop infrastructure
UNDERLYING_CLASSES = {}
def python_class_for(c, name=None):
    key = c.__hash__()
    if key not in UNDERLYING_CLASSES.keys():
        if name is None:
            name = c.get_name()
        UNDERLYING_CLASSES[key] = type(name, (object,), {})
    return UNDERLYING_CLASSES[key]

def python_install_method(c, name, method):
    setattr(
        python_class_for(c),
        name,
        lambda self, *args, **kwargs: method.execute(self, args, kwargs)
    )

# and finally, bootstrap helpers to create hardcoded structures during the
# bootstrap (which we will inflate into real structures at the end)
def bootstrap_create_class(name, superclass):
    c = BasicInstance(
        globals().get("Class"),
        {
            "name": name,
            "superclass": superclass,
            "methods": {},
            "attributes": {},
        },
    )
    # need to make sure we call this explicitly with the class name during the
    # bootstrap, since we won't have get_name() yet
    python_class_for(c, name)
    return c

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

def bootstrap():
    # Phase 1: construct the core classes

    global Class, Object, Method, Attribute

    Class     = bootstrap_create_class('Class', None)
    Object    = bootstrap_create_class('Object', None)
    Method    = bootstrap_create_class('Method', Object)
    Attribute = bootstrap_create_class('Attribute', Object)

    def add_method(self, method):
        name = method.slots["name"]
        self.slots["methods"][name] = method
        method.__class__ = python_class_for(Method)
        python_install_method(self, name, method)
    Class.slots["methods"]["add_method"] = bootstrap_create_method(
        "add_method", add_method
    )
    Method.slots["methods"]["execute"] = bootstrap_create_method(
        "execute", execute_method
    )

    # Phase 2: tie the knot

    Class.metaclass = Class
    Class.slots["superclass"] = Object

    # Phase 3: associate the core classes with their underlying method table

    Class.__class__     = python_class_for(Class)
    Object.__class__    = python_class_for(Class)
    Method.__class__    = python_class_for(Class)
    Attribute.__class__ = python_class_for(Class)

    m1 = Class.slots["methods"]["add_method"]
    m1.metaclass = Method
    m1.__class__ = python_class_for(Method)
    python_install_method(Class, "add_method", m1)

    # note: not using python_install_method here, since that installs a method
    # which calls method.execute, and this is where we have the recursion base
    # case
    m2 = Method.slots["methods"]["execute"]
    m2.metaclass = Method
    m2.__class__ = python_class_for(Method)
    setattr(python_class_for(Method), "execute", execute_method)

    # Phase 4: manually assemble enough scaffolding to allow object construction

    def gen_reader(name):
        return lambda self: self.slots[name]

    Class.add_method(bootstrap_create_method(
        "get_superclass", gen_reader("superclass")
    ))

    def get_mro(self):
        mro = [ self ]
        parent = self.get_superclass()
        if parent:
            mro.extend(parent.get_mro())
        return mro
    Class.add_method(bootstrap_create_method(
        "get_mro", get_mro
    ))

    Class.add_method(bootstrap_create_method(
        "get_local_attributes", gen_reader("attributes")
    ))

    def get_all_attributes(self):
        attributes = {}
        for c in reversed(self.get_mro()):
            attributes.update(c.get_local_attributes())
        return attributes
    Class.add_method(bootstrap_create_method(
        "get_all_attributes", get_all_attributes
    ))

    def create_instance(self, kwargs):
        slots = {}
        for attr_name in self.get_all_attributes():
            if attr_name in kwargs.keys():
                slots[attr_name] = kwargs[attr_name]
        instance = BasicInstance(self, slots)
        instance.__class__ = python_class_for(self)
        return instance
    Class.add_method(bootstrap_create_method(
        "create_instance", create_instance
    ))

    def new(self, **kwargs):
        return self.create_instance(kwargs)
    Class.add_method(bootstrap_create_method(
        "new", new
    ))

    # Phase 5: Object construction works, just need attributes to construct with

    Attribute.add_method(bootstrap_create_method(
        "get_name", gen_reader("name")
    ))

    def add_attribute(self, attr):
        self.get_local_attributes()[attr.get_name()] = attr
    Class.add_method(bootstrap_create_method(
        "add_attribute", add_attribute
    ))

    attr_name = bootstrap_create_attribute("name")
    attr_name.__class__ = python_class_for(Attribute)
    Attribute.add_attribute(attr_name)

    # and now object creation works! add the method attributes now to allow
    # creating method objects
    Method.add_attribute(Attribute.new(name="name"))
    Method.add_attribute(Attribute.new(name="body"))

    # Phase 6: now we can populate the rest of the mop

    Method.add_method(Method.new(
        name="get_name", body=gen_reader("name")
    ))
    Method.add_method(Method.new(
        name="get_body", body=gen_reader("body")
    ))

    Class.add_attribute(Attribute.new(name="name"))
    Class.add_attribute(Attribute.new(name="superclass"))
    Class.add_attribute(Attribute.new(name="attributes"))
    Class.add_attribute(Attribute.new(name="methods"))

    Class.add_method(Method.new(
        name="get_name", body=gen_reader("name")
    ))

    Class.add_method(Method.new(
        name="get_local_methods", body=gen_reader("methods")
    ))

    def get_all_methods(self):
        methods = {}
        for c in reversed(self.get_mro()):
            methods.update(c.get_local_methods())
        return methods
    Class.add_method(Method.new(
        name="get_all_methods", body=get_all_methods
    ))

    Class.add_method(Method.new(
        name="attribute_class", body=lambda self: Attribute
    ))
    Class.add_method(Method.new(
        name="method_class", body=lambda self: Method
    ))
    Class.add_method(Method.new(
        name="base_object_class", body=lambda self: Object
    ))

    def isa(self, other):
        mro = self.metaclass.get_mro()
        return other in mro
    Object.add_method(Method.new(
        name="isa", body=isa
    ))

    def can(self, method_name):
        return self.metaclass.get_all_methods().get(method_name)
    Object.add_method(Method.new(
        name="can", body=can
    ))

    # Phase 7: now we have to clean up after ourselves

    for c in [ Class, Object, Method, Attribute ]:
        for method in c.get_local_methods().values():
            method.__class__ = python_class_for(Method)
        for attribute in c.get_local_attributes().values():
            attribute.__class__ = python_class_for(Attribute)

    for method in Object.get_local_methods().values():
        python_install_method(Class, method.get_name(), method)
        python_install_method(Method, method.get_name(), method)
        python_install_method(Attribute, method.get_name(), method)

    def add_method(self, method):
        name = method.get_name()
        self.get_local_methods()[name] = method
        python_install_method(self, name, method)
    Class.add_method(Method.new(
        name="add_method", body=add_method
    ))

bootstrap()
