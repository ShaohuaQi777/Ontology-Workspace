"""CLI boundary configuration; real loopback process smoke is B1-06."""
import importlib
import pytest


def test_server_default_is_loopback_secure_no_access_body_or_proxy_logging(tmp_path):
    module=importlib.import_module('ontology_platform.api.server')
    settings=module.parse_args(['--database','sqlite:///'+str(tmp_path/'metadata.db'),'--artifact-root',str(tmp_path/'artifacts'),'--origin','https://localhost'])
    assert settings.host=='127.0.0.1' and settings.port==8765 and settings.secure_cookies is True
    kwargs=module.server_options(settings)
    assert kwargs['host']=='127.0.0.1' and kwargs['access_log'] is False and kwargs['proxy_headers'] is False
    assert kwargs['http']=='h11' and kwargs['loop']=='asyncio' and kwargs['log_config'] is None
    assert kwargs['limit_concurrency']==32


@pytest.mark.parametrize('extra',[['--host','0.0.0.0'],['--host','remote.invalid'],['--insecure-dev','--origin','https://remote.invalid']])
def test_server_refuses_implicit_remote_exposure_or_insecure_remote_cookies(tmp_path,extra):
    module=importlib.import_module('ontology_platform.api.server')
    args=['--database','sqlite:///'+str(tmp_path/'metadata.db'),'--artifact-root',str(tmp_path/'artifacts'),'--origin','http://127.0.0.1:8765',*extra]
    with pytest.raises(ValueError): module.parse_args(args)
