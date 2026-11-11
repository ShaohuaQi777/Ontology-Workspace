"""Race/resource preflight tests; genuine child invocation where permitted."""
import io
import json
import os
from pathlib import Path
import zipfile
import pytest
from ontology_platform.semantic.dto import IngestRequest, ParseRequest, GraphBuildRequest
from ontology_platform.semantic.errors import BackendError
from ontology_platform.infrastructure.semantica_adapter.backend import SemanticaBackend
from test_semantic_boundary import artifact,common


def test_concurrent_runs_symlink_never_redirects_writes(tmp_path,monkeypatch):
    root=tmp_path/'root'; root.mkdir(); outside=tmp_path/'outside'; outside.mkdir()
    source=artifact(root,'source.csv','id\nx\n')
    original=os.mkdir; fired=[]
    def racing(path,*args,**kwargs):
        if not fired and 'runs' in str(path):
            fired.append(True)
            (root/'runs').symlink_to(outside,target_is_directory=True)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(os,'mkdir',racing)
    with pytest.raises(BackendError):
        SemanticaBackend(root).ingest(IngestRequest(**common(),source=source,source_revision='v1',format='csv'))
    assert fired and list(outside.iterdir())==[]


def test_input_symlink_is_not_followed_even_within_authorized_root(tmp_path):
    original=artifact(tmp_path,'real.csv','id\nx\n')
    (tmp_path/'source.csv').symlink_to(tmp_path/'real.csv')
    ref=original.model_copy(update={'path':'source.csv'})
    with pytest.raises(BackendError):
        SemanticaBackend(tmp_path).ingest(IngestRequest(**common(),source=ref,source_revision='v1',format='csv'))


def test_graph_credentials_never_enter_new_snapshots(tmp_path):
    source=artifact(tmp_path,'graph.json',json.dumps({'entities':[{'id':'n','type':'Node','metadata':{'password':'technical-test-secret'}}],'relationships':[]}))
    with pytest.raises(BackendError):
        SemanticaBackend(tmp_path).build_graph(GraphBuildRequest(**common(),source=source,graph_revision='g1'))
    assert not (tmp_path/'runs').exists()


def test_archive_ratio_rejected_before_native_or_snapshot(tmp_path):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('word/document.xml','<doc>'+('x'*600000)+'</doc>')
    source=artifact(tmp_path,'source.docx',stream.getvalue())
    with pytest.raises(BackendError) as caught:
        SemanticaBackend(tmp_path).parse(ParseRequest(**common(),source=source,source_revision='v1',format='docx'))
    assert caught.value.code=='INVALID_INPUT'
    assert not (tmp_path/'runs').exists()


@pytest.mark.parametrize('key',['accessToken','privateKey','refresh-token','clientSecret','access_token','api-key'])
def test_conventional_credential_key_forms_rejected(tmp_path,key):
    source=artifact(tmp_path,'source.json',json.dumps({key:'technical-test-secret'}))
    with pytest.raises(BackendError):
        SemanticaBackend(tmp_path).parse(ParseRequest(**common(),source=source,source_revision='v1',format='json'))
    assert not (tmp_path/'runs').exists()


def test_serialized_output_is_bounded_before_persistence(tmp_path):
    from ontology_platform.infrastructure.semantica_adapter.worker import persist_response
    with pytest.raises(ValueError):
        persist_response(tmp_path,{'data':{'text':'x'*1048576}})
    assert not (tmp_path/'response.json').exists()


def test_rule_cartesian_fanout_is_rejected_without_inference():
    from ontology_platform.infrastructure.semantica_adapter.worker import checked_rules
    facts=['Token(x'+str(index)+')' for index in range(20)]
    rules=[{'id':'r','conditions':['Token(?a)','Token(?b)','Token(?c)','Token(?d)','Token(?e)'],'conclusion':'Out(?a)'}]
    with pytest.raises(ValueError):
        checked_rules(facts,rules)


def test_untrusted_artifact_package_never_bootstraps_python(tmp_path):
    package=tmp_path/'ontology_platform'; package.mkdir()
    marker=tmp_path/'executed'
    (package/'__init__.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("UNTRUSTED_CODE_EXECUTED")\n')
    source=artifact(tmp_path,'source.csv','id\nx\n')
    result=None
    try:
        result=SemanticaBackend(tmp_path).ingest(IngestRequest(**common(),source=source,source_revision='v1',format='csv'))
    except BackendError: pass
    assert not marker.exists()
    assert result is not None and result.data['file_type']=='csv'


def test_declared_json_credentials_rejected_with_non_json_suffix(tmp_path):
    source=artifact(tmp_path,'source.txt','{"password":"technical-test-secret"}')
    with pytest.raises(BackendError):
        SemanticaBackend(tmp_path).parse(ParseRequest(**common(),source=source,source_revision='v1',format='json'))
    assert not (tmp_path/'runs').exists()
