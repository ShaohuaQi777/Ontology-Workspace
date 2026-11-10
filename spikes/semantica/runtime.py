"""Serial probe guard: discard raw Python SDK logs/stdio and keep caches local.

This is NOT a network sandbox or cancellation mechanism. Native capabilities
remain real calls. Later product Worker isolation must enforce those boundaries.
"""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
import logging
import os
from pathlib import Path


class DiscardText(io.TextIOBase):
    def write(self, text):
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return False


@contextmanager
def quiet_native_runtime(work: Path):
    settings = {'SEMANTICA_CACHE_BACKEND': 'memory', 'HF_HUB_OFFLINE': '1',
                'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
                'HF_HOME': str(work / 'model-cache'), 'XDG_CACHE_HOME': str(work / 'cache')}
    previous_env = {key: os.environ.get(key) for key in settings}
    root = logging.getLogger('semantica')
    loggers = [root] + [logger for name, logger in logging.Logger.manager.loggerDict.items()
                       if name.startswith('semantica.') and isinstance(logger, logging.Logger)]
    previous_logs = [(logger, logger.handlers[:], logger.propagate) for logger in loggers]
    for logger in loggers:
        logger.handlers = []
        logger.propagate = logger is not root
    root.addHandler(logging.NullHandler())  # Prevent SDK auto-initializing semantica.log.
    os.environ.update(settings)
    try:
        with redirect_stdout(DiscardText()), redirect_stderr(DiscardText()):
            yield
    finally:
        for logger, handlers, propagate in previous_logs:
            logger.handlers = handlers
            logger.propagate = propagate
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
