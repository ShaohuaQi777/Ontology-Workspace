"""Stable non-sensitive application service failures, not native exceptions."""
MESSAGES={
    'UNSUPPORTED_SCHEMA':'Service metadata schema is unsupported',
    'STORAGE_UNAVAILABLE':'Service metadata storage is unavailable',
    'NOT_INITIALIZED':'Service metadata is not initialized',
    'SECRET_UNAVAILABLE':'Required secret provider reference is unavailable',
    'INVALID_ACCOUNT':'Account input is invalid',
    'ACCOUNT_EXISTS':'Account already exists',
    'BOOTSTRAP_DISABLED':'Account bootstrap is unavailable',
    'AUTHENTICATION_FAILED':'Account authentication failed',
    'UNAUTHENTICATED':'A valid service session is required',
    'LOGIN_RATE_LIMIT':'Authentication temporarily rate limited',
    'FORBIDDEN':'Operation is not permitted',
}


class ServiceError(Exception):
    def __init__(self,code:str):
        if code not in MESSAGES: raise ValueError('Unknown service error')
        self.code=code
        super().__init__(MESSAGES[code])
