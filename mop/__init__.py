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

def execute_method(body, invocant, args, kwargs):
    return body(invocant, *args, **kwargs)

# shim layer to interface with python - in a real system, this wouldn't be
# necessary, but this allows us to pass python-level method calls through to
# our mop infrastructure
UNDERLYING_CLASSES = {}
def python_class_for(c, name=None):
    key = c.__hash__()
    if key not in UNDERLYING_CLASSES.keys():
        if name is None:
            name = c.name()
        UNDERLYING_CLASSES[key] = type(name, (object,), {})
    return UNDERLYING_CLASSES[key]

def python_install_method(c, name, method):
    setattr(
        python_class_for(c),
        name,
        lambda self, *args, **kwargs: method.execute(self, args, kwargs)
    )

def bootstrap():
    # Phase 1: construct the core classes

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

    def bootstrap_create_attribute(name, default):
        return BasicInstance(
            globals().get("Attribute"),
            {
                "name": name,
                "default": default,
            }
        )

    global Class, Object, Method, Attribute

    Class     = bootstrap_create_class('Class', None)
    Object    = bootstrap_create_class('Object', None)
    Method    = bootstrap_create_class('Method', Object)
    Attribute = bootstrap_create_class('Attribute', Object)

    # need to make sure we call this explicitly with the class name during the
    # bootstrap, since we won't have name() yet
    python_class_for(Class,     'Class')
    python_class_for(Object,    'Object')
    python_class_for(Method,    'Method')
    python_class_for(Attribute, 'Attribute')

    Class.__class__     = python_class_for(Class)
    Object.__class__    = python_class_for(Class)
    Method.__class__    = python_class_for(Class)
    Attribute.__class__ = python_class_for(Class)

    # this add_method implementation is temporary, since it touches the slots
    # directly and fiddles with method.__class__ and such - once the full mop
    # is complete, we won't need to do those things (and they might even be the
    # wrong things to do), so we will replace it at the end
    def add_method(self, method):
        name = method.slots["name"]
        self.slots["methods"][name] = method
        method.__class__ = python_class_for(Method)
        python_install_method(self, name, method)
    method_add_method = bootstrap_create_method(
        "add_method", add_method
    )
    method_add_method.metaclass = Method
    method_add_method.__class__ = python_class_for(Method)
    Class.slots["methods"]["add_method"] = method_add_method
    python_install_method(Class, "add_method", method_add_method)

    # same here
    def execute(self, invocant, args, kwargs):
        return execute_method(self.slots["body"], invocant, args, kwargs)
    method_execute = bootstrap_create_method(
        "execute", execute
    )
    method_execute.metaclass = Method
    method_execute.__class__ = python_class_for(Method)
    Method.slots["methods"]["execute"] = method_execute
    # note: not using python_install_method here, since that installs a method
    # which calls method.execute, and this is where we have the recursion base
    # case
    setattr(python_class_for(Method), "execute", method_execute.slots["body"])

    # Phase 2: tie the knot

    Class.metaclass = Class
    Class.slots["superclass"] = Object

    # Phase 3: manually assemble enough scaffolding to allow object construction

    # temporary, we'll have a better version later
    def gen_reader(name):
        return lambda self: self.slots[name]

    # mro needs superclass
    Class.add_method(bootstrap_create_method(
        "superclass", gen_reader("superclass")
    ))

    # all_attributes requires mro
    def mro(self):
        mro = [ self ]
        parent = self.superclass()
        if parent:
            mro.extend(parent.mro())
        return mro
    Class.add_method(bootstrap_create_method(
        "mro", mro
    ))

    # all_attributes requires local_attributes
    Class.add_method(bootstrap_create_method(
        "local_attributes", gen_reader("attributes")
    ))

    # create_instance requires all_attributes
    def all_attributes(self):
        attributes = {}
        for c in reversed(self.mro()):
            attributes.update(c.local_attributes())
        return attributes
    Class.add_method(bootstrap_create_method(
        "all_attributes", all_attributes
    ))

    # default_for_instance requires default
    Attribute.add_method(bootstrap_create_method(
        "default", gen_reader("default")
    ))

    # create_instance requires default_for_instance
    def default_for_instance(self):
        default = self.default()
        if callable(default):
            default = default()
        return default
    Attribute.add_method(bootstrap_create_method(
        "default_for_instance", default_for_instance
    ))

    # set_value requires name
    Attribute.add_method(bootstrap_create_method(
        "name", gen_reader("name")
    ))

    # create_instance requires set_value
    def set_value(self, instance, new_value):
        instance.slots[self.name()] = new_value
    Attribute.add_method(bootstrap_create_method(
        name="set_value", body=set_value
    ))

    # new requires create_instance
    def create_instance(self, kwargs):
        instance = BasicInstance(self, {})
        instance.__class__ = python_class_for(self)
        attrs = self.all_attributes()
        for attr_name in attrs:
            attr = attrs[attr_name]
            if attr_name in kwargs.keys():
                attr.set_value(instance, kwargs[attr_name])
            else:
                attr.set_value(instance, attr.default_for_instance())
        return instance
    Class.add_method(bootstrap_create_method(
        "create_instance", create_instance
    ))

    def new(self, **kwargs):
        return self.create_instance(kwargs)
    Class.add_method(bootstrap_create_method(
        "new", new
    ))

    # Phase 4: Object construction works, just need attributes to construct with

    def add_attribute(self, attr):
        self.local_attributes()[attr.name()] = attr
    Class.add_method(bootstrap_create_method(
        "add_attribute", add_attribute
    ))

    attr_name = bootstrap_create_attribute("name", None)
    attr_name.__class__ = python_class_for(Attribute)
    Attribute.add_attribute(attr_name)

    attr_default = bootstrap_create_attribute("default", None)
    attr_default.__class__ = python_class_for(Attribute)
    Attribute.add_attribute(attr_default)

    # and now object creation works! add the method attributes now to allow
    # creating method objects
    Method.add_attribute(Attribute.new(name="name"))
    Method.add_attribute(Attribute.new(name="body"))

    # Phase 5: now we can populate the rest of the mop

    def value(self, instance):
        return instance.slots[self.name()]
    Attribute.add_method(Method.new(
        name="value", body=value
    ))

    # here's the better implementation
    # note that we can't replace the implementation of the methods implemented
    # by the previous gen_reader because that would end up recursive
    def gen_reader(name):
        return lambda self: self.metaclass.all_attributes()[name].value(self)

    Method.add_method(Method.new(
        name="name", body=gen_reader("name")
    ))
    Method.add_method(Method.new(
        name="body", body=gen_reader("body")
    ))

    Class.add_attribute(Attribute.new(name="name"))
    Class.add_attribute(Attribute.new(name="superclass"))
    Class.add_attribute(Attribute.new(name="attributes", default=lambda: {}))
    Class.add_attribute(Attribute.new(name="methods", default=lambda: {}))

    Class.add_method(Method.new(
        name="name", body=gen_reader("name")
    ))

    Class.add_method(Method.new(
        name="local_methods", body=gen_reader("methods")
    ))

    def all_methods(self):
        methods = {}
        for c in reversed(self.mro()):
            methods.update(c.local_methods())
        return methods
    Class.add_method(Method.new(
        name="all_methods", body=all_methods
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

    def finalize(self):
        for method in self.all_methods().values():
            python_install_method(self, method.name(), method)
    Class.add_method(Method.new(
        name="finalize", body=finalize
    ))

    def isa(self, other):
        mro = self.metaclass.mro()
        return other in mro
    Object.add_method(Method.new(
        name="isa", body=isa
    ))

    def can(self, method_name):
        return self.metaclass.all_methods().get(method_name)
    Object.add_method(Method.new(
        name="can", body=can
    ))

    # Phase 6: now we have to clean up after ourselves

    def add_method(self, method):
        self.local_methods()[method.name()] = method
    Class.add_method(Method.new(
        name="add_method", body=add_method
    ))

    Class.finalize()
    Object.finalize()
    Attribute.finalize()

    # we can't call Method.finalize(), since that would overwrite our base
    # implementation of Method.execute and lead to infinite recursion
    for method in Object.local_methods().values():
        python_install_method(Method, method.name(), method)

    # we add the better version of Method.execute to the internal method map,
    # but we don't actually install it. this way, all method subclasses will
    # use this implementation, but the base Method class will not (which is
    # safe because we know exactly how the base Method class is implemented)
    def execute(self, invocant, args, kwargs):
        body = self.metaclass.all_attributes()["body"].value(self)
        return execute_method(body, invocant, args, kwargs)
    Method.add_method(Method.new(
        name="execute", body=execute
    ))

    # do the same thing with accessor methods that we installed with our
    # temporary version of gen_reader
    Class.add_method(Method.new(
        name="superclass", body=gen_reader("superclass")
    ))
    Class.add_method(Method.new(
        name="local_attributes", body=gen_reader("attributes")
    ))
    Attribute.add_method(Method.new(
        name="default", body=gen_reader("default")
    ))
    Attribute.add_method(Method.new(
        name="name", body=gen_reader("name")
    ))

bootstrap()
