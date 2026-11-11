"""Platform preflight only; semantic computation remains in the native SDK."""
import io
import json
import re
import zipfile
from .translation import to_platform_value

GRAPH_FIELDS={'entities':{'id','type','text'},'relationships':{'source','target','type'}}
CREDENTIAL_KEYS={'password','passwd','secret','token','apikey','accesstoken','refreshtoken','authorization','privatekey','clientsecret','clientpassword','bearertoken','signingkey','recoverycode'}


def json_input(data,*,run_id):
    value=json.loads(data)
    value=to_platform_value(value,run_id=run_id)
    def check(item):
        if type(item) is dict:
            for key,val in item.items():
                canonical=re.sub(r'[^a-z0-9]','',key.casefold())
                if canonical in CREDENTIAL_KEYS:
                    raise ValueError('Credential fields require a separately authorized credential reference')
                check(val)
        elif type(item) is list:
            for val in item: check(val)
    check(value)
    return value


def graph_input(data,*,run_id):
    graph=json_input(data,run_id=run_id)
    if type(graph) is not dict or set(graph)!=set(GRAPH_FIELDS):
        raise ValueError('Invalid graph input')
    for key,allowed in GRAPH_FIELDS.items():
        if type(graph[key]) is not list or len(graph[key])>1000:
            raise ValueError('Invalid graph records')
        for item in graph[key]:
            required={'id','type'} if key=='entities' else allowed
            if type(item) is not dict or not required<=set(item)<=allowed or not all(type(val) is str and 0<len(val)<=4096 for val in item.values()):
                raise ValueError('Unsupported graph fields')
    ids=[item['id'] for item in graph['entities']]
    if len(set(ids))!=len(ids) or any(item[edge] not in ids for item in graph['relationships'] for edge in ('source','target')):
        raise ValueError('Invalid graph references')
    return graph


def archive_input(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries=archive.infolist()
        if not entries or len(entries)>128 or sum(item.file_size for item in entries)>1048576:
            raise ValueError('Archive expansion exceeds budget')
        for item in entries:
            if item.flag_bits&1 or item.file_size>1048576 or item.file_size>max(item.compress_size,1)*100:
                raise ValueError('Archive compression exceeds budget')
            if item.filename.startswith('/') or '\\' in item.filename or '..' in item.filename.split('/'):
                raise ValueError('Unsafe archive member')
        # Verify actual decompression/CRC is finite too; never extract paths.
        total=0
        for item in entries:
            with archive.open(item) as member:
                content=member.read(1048577)
                total+=len(content)
                if len(content)!=item.file_size or total>1048576:
                    raise ValueError('Invalid archive content')


def preflight(operation,request,inputs):
    for key,data in inputs.items():
        ref=getattr(request,key)
        if ref.path.lower().endswith('.json') or (key=='source' and getattr(request,'format',None)=='json') or (operation in ('build_graph','reason') and key in ('source','rules')):
            json_input(data,run_id=request.run_id)
        if ref.path.lower().endswith('.docx') or (key=='source' and getattr(request,'format',None)=='docx'):
            archive_input(data)
        if operation=='parse' and key=='source' and request.format=='pdf':
            from .pdf_preflight import check_pdf_bytes
            check_pdf_bytes(data)
    if operation=='build_graph' or (operation=='ontology' and request.action=='generate'):
        graph_input(inputs['source'],run_id=request.run_id)
    if operation=='reason':
        from .worker import checked_rules
        checked_rules(json_input(inputs['source'],run_id=request.run_id),json_input(inputs['rules'],run_id=request.run_id))
