
import inspect
import re

import config

iter_types = [
    dict,
    list,
    tuple
]

string_types = [
    str
]

numeric_types = [
    int,
    float
]

value_types = [
    bool,
    None
]

supported_types = iter_types+string_types+numeric_types+value_types
invalid_module_chars = r'[^a-zA-Z0-9\_\.]'


class TranslationError(Exception):
    pass


def dump(obj, serialize_method=None, ignore_attribute=None, ignore=[]):
    if not serialize_method:
        serialize_method = config.serialize_method
    if not ignore_attribute:
        ignore_attribute = config.ignore_attribute
    obj_type = type(obj)
    if obj_type in numeric_types+string_types+value_types:
        return obj
    if obj_type in iter_types:
        if obj_type in (list, tuple):
            new_obj = []
            for item in obj:
                new_obj.append(
                    dump(item, serialize_method, ignore_attribute, ignore))
            if isinstance(obj_type, tuple):
                new_obj = tuple(new_obj)
            return new_obj
        else:
            new_obj = {}
            for key, value in obj.items():
                new_obj[key] = dump(
                    value, serialize_method, ignore_attribute, ignore)
            return new_obj
    module_name = inspect.getmodule(obj).__name__
    class_name = obj.__class__.__name__
    json_class = class_name
    if module_name not in ['', '__main__']:
        json_class = '%s.%s' % (module_name, json_class)
    return_obj = {"__jsonclass__": [json_class]}
    # If a serialization method is defined..
    if serialize_method in dir(obj):
        serialize = getattr(obj, serialize_method)
        params, attrs = serialize()
        return_obj['__jsonclass__'].append(params)
        return_obj.update(attrs)
        return return_obj
    return_obj['__jsonclass__'].append([])
    attrs = {}
    ignore_list = getattr(obj, ignore_attribute, [])+ignore
    for attr_name, attr_value in obj.__dict__.items():
        if type(attr_value) in supported_types and \
                attr_name not in ignore_list and \
                attr_value not in ignore_list:
            attrs[attr_name] = dump(
                attr_value, serialize_method, ignore_attribute, ignore)
    return_obj.update(attrs)
    return return_obj


def load(obj):
    if type(obj) in string_types + numeric_types + value_types:
        return obj

    if isinstance(obj, list):
        return_list = []
        for entry in obj:
            return_list.append(load(entry))
        return return_list
    if '__jsonclass__' not in obj:
        return_dict = {}
        for key, value in obj.iteritems():
            new_value = load(value)
            return_dict[key] = new_value
        return return_dict
    orig_module_name = obj['__jsonclass__'][0]
    params = obj['__jsonclass__'][1]
    if orig_module_name == '':
        raise TranslationError('Module name empty.')
    json_module_clean = re.sub(invalid_module_chars, '', orig_module_name)
    if json_module_clean != orig_module_name:
        raise TranslationError('Module name %s has invalid characters.' %
                               orig_module_name)
    json_module_parts = json_module_clean.split('.')
    json_class = None
    if len(json_module_parts) == 1:
        # Local class name -- probably means it won't work
        if json_module_parts[0] not in config.classes.keys():
            raise TranslationError('Unknown class or module %s.' %
                                   json_module_parts[0])
        json_class = config.classes[json_module_parts[0]]
    else:
        json_class_name = json_module_parts.pop()
        json_module_tree = '.'.join(json_module_parts)
        try:
            temp_module = __import__(json_module_tree)
        except ImportError:
            raise TranslationError('Could not import %s from module %s.' %
                                   (json_class_name, json_module_tree))
        for i in json_module_parts[1:]:
            temp_module = getattr(temp_module, i)

        json_class = getattr(temp_module, json_class_name)
    new_obj = None
    if isinstance(params, list):
        new_obj = json_class(*params)
    elif isinstance(params, dict):
        new_obj = json_class(**params)
    else:
        raise TranslationError('Constructor args must be a dict or list.')
    for key, value in obj.iteritems():
        if key == '__jsonclass__':
            continue
        setattr(new_obj, key, value)
    return new_obj