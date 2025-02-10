import typing

def f(global_vars: dict[str, typing.Any], local_vars: dict[str, typing.Any]):
    globals().update(global_vars)
    globals().update(local_vars)
