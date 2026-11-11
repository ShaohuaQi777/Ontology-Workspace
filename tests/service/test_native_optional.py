"""Pinned SDK capability probes. Missing engines/fallbacks are not product support."""
import hashlib,json,os,sqlite3,subprocess,sys
from pathlib import Path


def native(code,tmp_path):
    result=tmp_path/'probe.json'
    subprocess.run([sys.executable,'-c',code,str(result),str(tmp_path.resolve())],env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=30)
    return json.loads(result.read_text())


def test_actual_native_database_select_is_readonly_and_preserves_source_hash(tmp_path):
    path=tmp_path/'source.db'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE technical(id TEXT, value INTEGER)')
        connection.execute('INSERT INTO technical VALUES(?,?)',('n1',7))
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    result=native('''import sys,json
from pathlib import Path
from semantica.ingest.db_ingestor import DBIngestor
root=Path(sys.argv[2]); uri='sqlite:///file:'+str(root/'source.db')+'?mode=ro&immutable=1&uri=true'
engine=DBIngestor(); rows=engine.execute_query(uri,'SELECT id,value FROM technical LIMIT :count',count=10)
rejected=False
try: engine.execute_query(uri,'UPDATE technical SET value=9')
except Exception: rejected=True
Path(sys.argv[1]).write_text(json.dumps({'rows':rows,'write_rejected':rejected}))
''',tmp_path)
    assert result=={'rows':[{'id':'n1','value':7}],'write_rejected':True}
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


def test_actual_native_ocr_reports_missing_engine_not_metadata_success(tmp_path):
    result=native('''import sys,json,shutil
from pathlib import Path
from PIL import Image
from semantica.parse.image_parser import ImageParser,TESSERACT_AVAILABLE
image=Path(sys.argv[2])/'technical.png'; Image.new('RGB',(32,32),'white').save(image)
assert not TESSERACT_AVAILABLE and shutil.which('tesseract') is None
unavailable=False
try: ImageParser().extract_text(image)
except Exception: unavailable=True
Path(sys.argv[1]).write_text(json.dumps({'native_ocr_attempted':True,'engine_available':False,'unavailable':unavailable}))
''',tmp_path)
    assert result=={'native_ocr_attempted':True,'engine_available':False,'unavailable':True}


def test_native_embedding_fallback_is_not_neural_rag_or_clip_support(tmp_path):
    result=native('''import sys,json,importlib.util
from pathlib import Path
from semantica.embeddings.text_embedder import TextEmbedder
embedder=TextEmbedder(); vector=embedder.embed_text('Technical retrieval input')
info=embedder.get_model_info()
Path(sys.argv[1]).write_text(json.dumps({'method':info['method'],'dimension':len(vector),'neural_available':importlib.util.find_spec('sentence_transformers') is not None,'clip_dependencies':all(importlib.util.find_spec(name) is not None for name in ('torch','transformers'))}))
''',tmp_path)
    assert result['method']=='fallback' and result['dimension']>0
    assert result['neural_available'] is False and result['clip_dependencies'] is False
