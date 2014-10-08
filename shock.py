__author__ = 'nzhang-dev'

import functools
import inspect
from collections import defaultdict

def _get_distance(klass, parentklass):
    return klass.__mro__.index(parentklass)

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
            key.append('-varargs',spec.annotations.get(spec.varargs, object))
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
        for arg in arguments:
            type_dict[arg] = type(arguments[arg]) if arg not in ('-kwargs','-varargs') else object
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
