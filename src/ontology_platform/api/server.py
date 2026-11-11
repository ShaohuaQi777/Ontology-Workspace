"""Explicit local HTTP entrypoint. No implicit public deployment or credential file."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit
from ontology_platform.infrastructure.metadata import MetadataStore
from ontology_platform.infrastructure.secrets import EnvironmentSecretProvider
from .app import create_app


def parse_args(argv=None):
    parser=argparse.ArgumentParser(description='Authenticated local ontology HTTP service')
    parser.add_argument('--database',required=True)
    parser.add_argument('--artifact-root',required=True,type=Path)
    parser.add_argument('--origin',required=True,action='append')
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',default=8765,type=int)
    parser.add_argument('--secret-ref',default=[],action='append')
    parser.add_argument('--insecure-dev',action='store_true')
    settings=parser.parse_args(argv)
    if settings.host not in ('127.0.0.1','::1','localhost') or not 1<=settings.port<=65535: raise ValueError('Only explicit local service binding is supported')
    settings.secure_cookies=not settings.insecure_dev
    if settings.insecure_dev and any(urlsplit(origin).hostname not in ('127.0.0.1','::1','localhost') for origin in settings.origin): raise ValueError('Insecure cookies are restricted to local development')
    return settings


def server_options(settings):
    return {'host':settings.host,'port':settings.port,'access_log':False,'proxy_headers':False,'log_config':None,'log_level':'critical','http':'h11','loop':'asyncio','ws':'none','limit_concurrency':32,'timeout_keep_alive':5}


def main(argv=None):
    import uvicorn
    try:
        settings=parse_args(argv)
        store=MetadataStore(settings.database); store.initialize()
        provider=EnvironmentSecretProvider(set(settings.secret_ref))
        app=create_app(store,settings.artifact_root,provider,settings.origin,secure_cookies=settings.secure_cookies)
        from ontology_platform.application.runtime import LocalWorkerRuntime
        runtime=LocalWorkerRuntime(app.state.jobs)
        app.state.runtime=runtime
        try:
            runtime.start()
            uvicorn.run(app,**server_options(settings))
        finally:
            runtime.stop(); store.close()
    except Exception: raise SystemExit('SERVICE_START_FAILED') from None


if __name__=='__main__': main()
