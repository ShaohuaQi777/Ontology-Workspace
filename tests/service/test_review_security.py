"""Independent Wave1 findings reproduced with synthetic markers, never real secrets."""
import pytest
from sqlalchemy import text
from test_workspaces import workspace


@pytest.mark.parametrize('content',[
    {'description':'https://safe.invalid https://synthetic-user:SYNTHETIC-PRIVATE-MARKER@example.invalid'},
    {'description':'https://safe.invalid,https://synthetic-user:SYNTHETIC-PRIVATE-MARKER@example.invalid'},
    {'url':'https://example.invalid/path?access_token=SYNTHETIC-PRIVATE-MARKER'},
    {'url':'https://example.invalid/path?ACCESS%5Ftoken=SYNTHETIC-PRIVATE-MARKER'},
])
def test_review_all_uri_authorities_and_credential_queries_reject_before_revision_persistence(tmp_path,content):
    work,accounts,store,actor,root=workspace(tmp_path)
    project=work.create_project(actor,'Technical','urn:review:')
    with pytest.raises(Exception) as failure: work.save_layer(actor,project.project_id,'tbox','w0',content,{})
    assert failure.value.code=='INVALID_WORKSPACE' and 'SYNTHETIC-PRIVATE-MARKER' not in str(failure.value)
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM revisions')).scalar_one()==0
    store.close()


@pytest.mark.parametrize('format,data',[
    ('csv',b'id,password\nn1,SYNTHETIC-PRIVATE-MARKER\n'),
    ('csv',b'id,Access Token\nn1,SYNTHETIC-PRIVATE-MARKER\n'),
    ('json',b'{"url":"https://example.invalid/?access_token=SYNTHETIC-PRIVATE-MARKER"}'),
    ('text',b'https://safe.invalid https://synthetic-user:SYNTHETIC-PRIVATE-MARKER@example.invalid'),
])
def test_review_credential_sources_reject_before_files_and_rows_are_registered(tmp_path,format,data):
    work,accounts,store,actor,root=workspace(tmp_path)
    project=work.create_project(actor,'Technical','urn:review:')
    with pytest.raises(Exception) as failure: work.register_source(actor,project.project_id,format,data)
    assert failure.value.code=='INVALID_SOURCE' and 'SYNTHETIC-PRIVATE-MARKER' not in str(failure.value)
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM sources')).scalar_one()==0
    store.close()


def test_review_source_preflight_never_blocks_http_event_loop(tmp_path,monkeypatch):
    import asyncio,time
    from test_api import api,client,login
    app,store,root=api(tmp_path)
    original=app.state.workspaces.register_source
    def bounded_preflight(*args,**kwargs):
        time.sleep(.3)  # Peripheral scheduling probe; actual registration follows.
        return original(*args,**kwargs)
    monkeypatch.setattr(app.state.workspaces,'register_source',bounded_preflight)
    async def run():
        async with await client(app) as c:
            await login(c)
            pid=(await c.post('/api/projects',json={'name':'Technical','namespace':'urn:scheduling:'})).json()['project_id']
            start=time.monotonic()
            upload=asyncio.create_task(c.post(f'/api/projects/{pid}/sources?format=text',content=b'Technical bounded source',headers={'Content-Type':'application/octet-stream'}))
            try:
                await asyncio.sleep(.03)
                assert (await c.get('/healthz')).status_code==200
                assert time.monotonic()-start<.2
            finally: assert (await upload).status_code==201
    asyncio.run(run()); store.close()
