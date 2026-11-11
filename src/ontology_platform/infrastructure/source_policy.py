"""Bounded platform input policy; native parsing stays inside the Adapter."""
import csv,io,json,zipfile
from ontology_platform.semantic.dto import reject_credential_authority
from ontology_platform.infrastructure.semantica_adapter.input_policy import json_input,archive_input
from ontology_platform.infrastructure.semantica_adapter.pdf_preflight import check_pdf_bytes

FORMATS={'csv':'csv','json':'json','text':'txt','pdf':'pdf','docx':'docx','turtle':'ttl','nt':'nt'}


def checked_json(value):
    data=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
    if len(data)>1048576: raise ValueError('Content exceeds budget')
    clean=json_input(data,run_id='source-preflight')
    def scan(item):
        if isinstance(item,str): reject_credential_authority(item)
        elif isinstance(item,dict):
            for key,val in item.items(): reject_credential_authority(key); scan(val)
        elif isinstance(item,list):
            for val in item: scan(val)
    scan(clean)
    return clean


def check_source(format,data):
    if format not in FORMATS or type(data) is not bytes or not 0<len(data)<=1048576:
        raise ValueError('Invalid bounded source')
    if format=='csv':
        decoded=data.decode('utf-8')
        headers=next(csv.reader(io.StringIO(decoded)),[])
        checked_json({key:None for key in headers})
        reject_credential_authority(decoded)
    elif format=='json': checked_json(json_input(data,run_id='source-preflight'))
    elif format=='docx':
        archive_input(data)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                reject_credential_authority(archive.read(member).decode('utf-8',errors='ignore'))
    elif format=='pdf':
        check_pdf_bytes(data)
        reject_credential_authority(data.decode('utf-8',errors='ignore'))
    else: reject_credential_authority(data.decode('utf-8'))
