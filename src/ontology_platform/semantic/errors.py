"""Platform-owned error boundary. Never retain native exception objects."""
from __future__ import annotations

import re
from typing import Callable, TypeVar

T = TypeVar('T')
ERROR_MESSAGES = {
    'DEPENDENCY_UNAVAILABLE': 'Required semantic backend dependency is unavailable',
    'INVALID_INPUT': 'Semantic operation input is invalid',
    'UNSUPPORTED_CAPABILITY': 'Semantic backend capability is unsupported',
    'TIMEOUT': 'Semantic backend operation timed out',
    'BACKEND_FAILURE': 'Semantic backend operation failed',
}
RUN_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')


class BackendError(Exception):
    """Only platform scalar values cross this error boundary.

    ``message`` is an application-owned safe message, never ``str(native_error)``.
    Use ``invoke_guarded`` to translate native failures safely.
    """
    def __init__(self, code: str, message: str, run_id: str, retryable: bool):
        if type(code) is not str or code not in ERROR_MESSAGES:
            raise ValueError('Unknown backend error code')
        if type(message) is not str or not message or len(message) > 512:
            raise ValueError('Invalid platform error message')
        if type(run_id) is not str or not RUN_ID.fullmatch(run_id):
            raise ValueError('Invalid run identifier')
        if type(retryable) is not bool:
            raise ValueError('Invalid retry policy')
        self.code = code
        self.message = message
        self.run_id = run_id
        self.retryable = retryable
        super().__init__(message)

    def to_dict(self) -> dict[str, str | bool]:
        return {'code': self.code, 'message': self.message,
                'run_id': self.run_id, 'retryable': self.retryable}

    @classmethod
    def from_native(cls, error: Exception, run_id: str) -> 'BackendError':
        if isinstance(error, ImportError):
            code = 'DEPENDENCY_UNAVAILABLE'
        elif isinstance(error, TimeoutError):
            code = 'TIMEOUT'
        elif isinstance(error, ValueError):
            code = 'INVALID_INPUT'
        else:
            code = 'BACKEND_FAILURE'
        return cls(code, ERROR_MESSAGES[code], run_id, code == 'TIMEOUT')


def invoke_guarded(operation: Callable[[], T], *, run_id: str) -> T:
    """Guard synchronous SDK calls; result DTO conversion is the Adapter's job.

    Raise outside the native exception handler so ``__context__`` does not
    retain the native object. Merely using ``raise ... from None`` *inside*
    the handler hides the traceback but still retains that exception.
    """
    if type(run_id) is not str or not RUN_ID.fullmatch(run_id):
        raise ValueError('Invalid run identifier')
    translated: BackendError
    try:
        return operation()
    except BackendError as error:
        translated = BackendError(error.code, error.message, error.run_id, error.retryable)
    except Exception as error:
        translated = BackendError.from_native(error, run_id)
    raise translated from None
