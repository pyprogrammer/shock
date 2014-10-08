__author__ = 'nzhang-dev'

import functools
import inspect
from collections import defaultdict

def _get_distance(klass, parentklass):
    return klass.__mro__.index(parentklass)

def _greatest_common_type(klasses):
    print(klasses)
    type_lists = [klass.__mro__[::-1] for klass in klasses]
    all_classes = set(type_lists[0])
    for type_list in type_lists[1:]:
        all_classes.intersection_update(type_list)
    commons = []
    for klass in all_classes:
        order = sum(type_list.index(klass) for type_list in type_lists)
        commons.append((order, klass))
    return max(commons)[1]



def shock(func):
    if not hasattr(shock, 'cache'):
        shock.cache = defaultdict(dict) #shock.cache is a dictionary of func_name:(mapping name,type) tuples to func objects.
        #I.E. 'hello':{{('x',int),('y',str)}:f}


    def lookup(name, type_dict):
        '''type_dict is dict of arg_name:arg_type pairs, with object being the default arg_type'''

        results = []
        for cache_key, func in shock.cache[name].items():
            try:
                distance = sum(_get_distance(type_dict[arg_name], arg_type) for arg_name, arg_type in cache_key)
                results.append((distance, func))
            except ValueError: #the types don't match up
                continue
        if not results:
            raise TypeError("Function {} with signature {} not found".format(name, type_dict))
        return min(results)[1]

    def make_key(f):
        spec = inspect.getfullargspec(f)
        key = []
        for arg in spec.args:
            key.append((arg, spec.annotations.get(arg, object)))
        if spec.varargs:
            key.append(('-varargs',spec.annotations.get(spec.varargs, object)))
        for kwonlyarg in spec.kwonlyargs:
            key.append((kwonlyarg, spec.annotations.get(kwonlyarg, object)))
        if spec.varkw:
            key.append(('-kwargs', spec.annotations.get(spec.varkw, object)))
        key = frozenset(key)
        return key

    shock.cache[func.__name__][make_key(func)] = func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        spec = inspect.getfullargspec(func)
        arguments = {}
        iter_args = iter(args)
        for arg_name in spec.args:
            arguments[arg_name] = next(iter_args)
        arguments['-varargs'] = tuple(iter_args)
        arguments['-kwargs'] = {}
        for arg_name, value in kwargs.items():
            if arg_name in spec.args:
                if arg_name in arguments:
                    raise TypeError("{} got multiple values for argument '{}'".format(func.__name__, arg_name))
                arguments[arg_name] = value
            else:
                arguments['-kwargs'][arg_name] = value
        arguments['-kwargs'] = frozenset((key,value) for key,value in arguments['-kwargs'].items())
        key = frozenset((key,value) for key,value in arguments.items())
        type_dict = {}
        print(arguments)
        for arg in arguments:
            if not arguments[arg]:
                type_dict[arg] = object
                continue
            if arg == '-kwargs':
                t = _greatest_common_type([type(e) for key, e in arguments['-kwargs']])
            elif arg == '-varargs':
                t = _greatest_common_type([type(e) for e in arguments['-varargs']])
            else:
                t = type(arguments[arg])
            type_dict[arg] = t
        return lookup(func.__name__, type_dict)(*args, **kwargs)

    return wrapper

if __name__ == '__main__':
    @shock
    def f(a:int, b, c:str):
        print(int, None, str)
        return a,b,c

    @shock
    def f(a:int, b, c:int):
        print(int, None, int)
        return a,b,c


    print(f(3,2,4))
    print(f(3,2,'hello'))
    print(f(3,'hello','world'))
