"""Quiet, bounded pre-staging native PDF validation; no caller logger mutation."""
import os
from pathlib import Path
import subprocess
import sys


def check_pdf_bytes(data:bytes)->None:
    source_root=Path(__file__).resolve().parents[3]
    env={'PATH':os.defpath,'PYTHONPATH':str(source_root),'HOME':'/nonexistent','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    result=subprocess.run([sys.executable,'-P','-m','ontology_platform.infrastructure.semantica_adapter.pdf_preflight'],input=data,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=source_root,env=env,timeout=20)
    if result.returncode or result.stdout not in (b'ok',b'invalid',b'unsupported'): raise ValueError('Native PDF preflight failed')
    if result.stdout==b'unsupported': raise NotImplementedError('Native PDF feature unsupported')
    if result.stdout==b'invalid': raise ValueError('Invalid or unbounded PDF')


def main():
    import contextlib,logging,resource
    resource.setrlimit(resource.RLIMIT_CPU,(15,15))
    resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))
    logging.disable(logging.CRITICAL)  # private single-use process, not caller/global app
    data=sys.stdin.buffer.read(1048577)
    status='invalid'
    with open(os.devnull,'w') as sink,contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
        try:
            from semantica.parse.bounded_pdf import validate_pdf_bytes
            validate_pdf_bytes(data)
            status='ok'
        except NotImplementedError: status='unsupported'
        except Exception: status='invalid'
    sys.stdout.write(status)
    return 0


if __name__=='__main__': raise SystemExit(main())
