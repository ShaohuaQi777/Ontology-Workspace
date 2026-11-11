"""Exact built-in JSON value projection. Reject unknown native value types."""
import math
from ...semantic.errors import BackendError, ERROR_MESSAGES


def to_platform_value(value, *, run_id):
    count = 0
    active = set()
    def project(item, depth=0):
        nonlocal count
        count += 1
        if count > 10000 or depth > 32:
            raise ValueError('Oversized output')
        kind = type(item)
        if kind in (str,bool,int,type(None)):
            return item
        if kind is float and math.isfinite(item):
            return item
        if kind in (dict,list):
            if id(item) in active:
                raise ValueError('Cyclic native output')
            active.add(id(item))
            try:
                if kind is dict:
                    if not all(type(key) is str for key in item):
                        raise ValueError('Non-platform keys')
                    return {key:project(val,depth+1) for key,val in item.items()}
                return [project(val,depth+1) for val in item]
            finally:
                active.remove(id(item))
        raise ValueError('Unsupported native output type')
    failed = False
    try:
        result = project(value)
    except Exception:
        failed = True
    if failed:
        raise BackendError('BACKEND_FAILURE',ERROR_MESSAGES['BACKEND_FAILURE'],run_id,False) from None
    return result
