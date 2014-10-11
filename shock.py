__author__ = 'nzhang-dev'

import functools
import inspect
from collections import defaultdict, namedtuple


class Shock:
    cache = defaultdict(dict)
    ParameterKey = namedtuple('ParameterKey', ['name', 'kind', 'type', 'default'])

    @staticmethod
    def get_distance(cls, parent_cls):
        if not issubclass(cls, parent_cls):
            raise TypeError('{} is not a subclass of {}'.format(cls, parent_cls))
        return cls.__mro__.index(parent_cls)

    @staticmethod
    def greatest_common_type(cls_list):
        type_lists = [cls.__mro__[::-1] for cls in cls_list]
        all_classes = set(type_lists[0])
        for type_list in type_lists[1:]:
            all_classes.intersection_update(type_list)
        commons = []
        for cls in all_classes:
            order = sum(type_list.index(cls) for type_list in type_lists)
            commons.append((order, cls))
        return max(commons)[1]

    @classmethod
    def param_to_key(cls, param):
        """returns a hashable key for param"""
        param_type = object
        if isinstance(param.annotation, type) and not issubclass(param.annotation, inspect.Signature.empty):
            param_type = param.annotation
        return cls.ParameterKey(param.name, param.kind, param_type, param.default)

    @classmethod
    def lookup(cls, name, type_dict):
        """returns the cached version of function of name <name> that can process the args and kwargs"""
        func_cache = cls.cache[name]  # the cache that has the versions of function <name>
        distances = []
        for signature, func in func_cache.items():
            try:
                distance = 0
                for arg, arg_type in signature:
                    distance += cls.get_distance(type_dict[arg], arg_type)
                distances.append((distance, func))
            except (ValueError, KeyError):
                continue
        return min(distances)[1]

    @classmethod
    def make_key(cls, f):
        signature = inspect.signature(f)
        key = tuple(cls.param_to_key(parameter) for parameter in signature.parameters.values())
        return key

    def __new__(cls, func):
        key = cls.make_key(func)
        cache_entry = cls.cache[func.__name__]
        if cache_entry and key in cache_entry:
            return cache_entry[key]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            min_dist, function = float('inf'), lambda *args, **kwargs: NotImplementedError('Function not defined')
            for parameter_keys in cache_entry:
                parameter_list = [inspect.Parameter(param_key.name, param_key.kind, default=param_key.default,
                                                    annotation=param_key.type) for param_key in parameter_keys]
                signature = inspect.Signature(parameters=parameter_list)
                try:
                    bound = signature.bind(*args, **kwargs)
                except TypeError:
                    continue
                for param in parameter_list:
                    if param.name not in bound.arguments and param.default != inspect.Signature.empty:
                        bound.arguments[param.name] = param.default
                distance = 0
                best_key = None
                try:
                    for param_name, value in bound.arguments.items():

                        param_type = signature.parameters[param_name].annotation
                        if signature.parameters[param_name].kind == inspect.Parameter.VAR_POSITIONAL:
                            val_type = cls.greatest_common_type(type(arg) for arg in value)
                        elif signature.parameters[param_name].kind == inspect.Parameter.VAR_KEYWORD:
                            val_type = cls.greatest_common_type(type(arg) for arg in value.values())
                        else:
                            val_type = type(value)
                        distance += cls.get_distance(val_type, param_type)
                except TypeError:
                    #TypeError means not all args were filled or args were not the right type
                    continue
                if distance < min_dist:
                    min_dist, function = distance, cache_entry[parameter_keys]
            return function(*args, **kwargs)
        cache_entry[key] = func
        return wrapper

if __name__ == '__main__':
    @Shock
    def f(a: int, b, c: str):
        print(int, None, str)
        return a, b, c

    @Shock
    def f(a: int, b, c: int):
        print(int, None, int)
        return a, b, c


    @Shock
    def f(*a: int):
        print('*args, int')
        return a

    @Shock
    def f(*a: str):
        print('*args, str')
        return a

if __name__ == '__main__':
    print(f(3, 2, 4))
    print(f(3, 2, 'hello'))
    print(f(3, 'hello', 'world'))
    print(f(3, 3, 3, 2, 3, 2))
    print(f('hello', 'hello'))

    print(Shock.cache)
