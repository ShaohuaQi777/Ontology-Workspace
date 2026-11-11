"""Stable non-sensitive application service failures, not native exceptions."""
MESSAGES={
    'UNSUPPORTED_SCHEMA':'Service metadata schema is unsupported',
    'STORAGE_UNAVAILABLE':'Service metadata storage is unavailable',
    'NOT_INITIALIZED':'Service metadata is not initialized',
}


class ServiceError(Exception):
    def __init__(self,code:str):
        if code not in MESSAGES: raise ValueError('Unknown service error')
        self.code=code
        super().__init__(MESSAGES[code])
