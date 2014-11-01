import json
import mop

class InMemoryDatabase(object):
    def __init__(self):
        self.store = {}
        self.class_registry = {}

    def register_class(self, c):
        self.class_registry[c.name()] = c

    def insert(self, name, obj):
        data = self._repr(obj)
        self.store[name] = json.dumps(
            data,
            separators=(',', ':'),
            sort_keys=True
        )

    def lookup(self, name):
        if name in self.store:
            data = json.loads(self.store[name])
            if data["type"] == "plain":
                return data["data"]
            elif data["type"] == "object":
                metaclass = self.class_registry[data["class"]]
                return metaclass.create_instance(data["data"])
            else:
                raise Exception("unknown object type")
        else:
            raise Exception("object not in database")

    def _repr(self, obj):
        if type(obj) == type([]):
            return { "type": "plain", "data": obj }
        if type(obj) == type({}):
            return { "type": "plain", "data": obj }
        if type(obj) == type(""):
            return { "type": "plain", "data": obj }
        if type(obj) == type(0):
            return { "type": "plain", "data": obj }
        if type(obj) == type(True):
            return { "type": "plain", "data": obj }
        if type(obj) == type(None):
            return { "type": "plain", "data": obj }
        if hasattr(obj, 'isa') and obj.isa(mop.Object):
            self.register_class(obj.metaclass)
            return {
                "type": "object",
                "class": obj.metaclass.name(),
                "data": obj.slots,
            }
        raise Exception("unknown object type")
