import sys

PYTHON_VERSION = ('Python 2', 'Python 3')

class LocalClasses(dict):
    def add(self, cls):
        self[cls.__name__] = cls


class Config(object):
    use_jsonclass = True

    serialize_method = '_serialize'
    ignore_attribute = '_ignore'
    classes = LocalClasses()
    version = 2.0
    user_agent = '(Python %s)' % \
        '.'.join([str(ver) for ver in sys.version_info[0:3]])
    _instance = None

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance
