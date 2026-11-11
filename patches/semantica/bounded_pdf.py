"""MIT-licensed local bounded PDF facade for Semantica's native pdfminer backend.

No library globals are mutated. Only conservative raw/Flate text PDFs are supported.
PDF structure/semantics are parsed by pdfminer and Semantica, not lexical heuristics.
"""
from dataclasses import dataclass
import io
from pathlib import Path
import zlib
import tempfile

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser as NativeParser
from pdfminer.pdftypes import PDFObjRef,PDFStream,resolve1
from pdfminer.psparser import literal_name

INPUT_LIMIT=1048576
STREAM_LIMIT=262144


@dataclass
class Budget:
    decoded_bytes:int=0
    tokens:int=0
    nodes:int=0

    def consume(self,size):
        self.decoded_bytes+=size
        if self.decoded_bytes>INPUT_LIMIT: raise ValueError('PDF decoded total exceeds budget')


class BoundedStream(PDFStream):
    def __init__(self,original,budget):
        super().__init__(original.attrs,original.rawdata,original.decipher)
        self.budget=budget

    def decode(self):
        if self.data is not None: return
        if self.decipher is not None: raise NotImplementedError('Encrypted PDFs unsupported')
        raw=self.rawdata
        if type(raw) is not bytes or len(raw)>INPUT_LIMIT: raise ValueError('Invalid PDF stream input')
        if sum(key in self.attrs for key in ('F','Filter'))>1 or sum(key in self.attrs for key in ('DP','DecodeParms','FDecodeParms'))>1 or 'FDecodeParms' in self.attrs:
            raise NotImplementedError('Ambiguous/external PDF decoder parameters unsupported')
        filters=resolve1(self.attrs.get('F',self.attrs.get('Filter',[])))
        if not isinstance(filters,list): filters=[filters]
        params=resolve1(self.attrs.get('DP',self.attrs.get('DecodeParms',{})))
        if isinstance(params,list):
            if len(params)>1: raise NotImplementedError('PDF filter chains unsupported')
            params=resolve1(params[0]) if params else {}
        if params and (not isinstance(params,dict) or resolve1(params.get('Predictor',1))!=1):
            raise NotImplementedError('PDF predictors unsupported')
        if len(filters)>1: raise NotImplementedError('PDF filter chains unsupported')
        if filters:
            if literal_name(resolve1(filters[0])) not in ('FlateDecode','Fl'):
                raise NotImplementedError('PDF filter unsupported')
            decoder=zlib.decompressobj()
            decoded=decoder.decompress(raw,STREAM_LIMIT+1)
            if len(decoded)>STREAM_LIMIT or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
                raise ValueError('PDF decoded stream exceeds budget or is malformed')
            if len(decoded)>max(len(raw),1)*100:
                raise ValueError('PDF compression ratio exceeds budget')
        else: decoded=raw
        if len(decoded)>STREAM_LIMIT: raise ValueError('PDF raw stream exceeds budget')
        self.budget.consume(len(decoded))
        self.data=decoded
        self.rawdata=None


class LocalParser(NativeParser):
    def __init__(self,stream,budget):
        self.budget=budget
        super().__init__(stream)

    def nexttoken(self):
        self.budget.tokens+=1
        if self.budget.tokens>10000 or len(getattr(self,'context',[]))>32:
            raise ValueError('PDF syntax exceeds budget')
        return super().nexttoken()

    def do_keyword(self,pos,token):
        super().do_keyword(pos,token)
        if token is self.KEYWORD_STREAM:
            position,stream=self.pop(1)[0]
            if not isinstance(stream,PDFStream): raise ValueError('Invalid native PDF stream')
            self.push((position,BoundedStream(stream,self.budget)))


class LocalDocument(PDFDocument):
    def __init__(self,parser):
        self.active=set(); self.xref_active=set(); self.xref_count=0
        super().__init__(parser,caching=True,fallback=False)

    def _initialize_password(self,password=''):
        raise NotImplementedError('Encrypted PDFs unsupported')

    def read_xref_from(self,parser,pos,xrefs):
        if pos in self.xref_active or self.xref_count>=512: raise ValueError('Cyclic/excess PDF xrefs')
        self.xref_count+=1; self.xref_active.add(pos)
        try: return super().read_xref_from(parser,pos,xrefs)
        finally: self.xref_active.remove(pos)

    def getobj(self,objid):
        if objid in self.active or len(self.active)>=32: raise ValueError('Cyclic/deep PDF object references')
        self.active.add(objid)
        try:
            value=super().getobj(objid)
            if isinstance(value,PDFObjRef): value=self.getobj(value.objid)
            return value
        finally: self.active.remove(objid)


def validate_pdf_bytes(data:bytes)->dict[str,int]:
    if type(data) is not bytes or not data.startswith(b'%PDF-') or len(data)>INPUT_LIMIT:
        raise ValueError('Invalid bounded PDF input')
    budget=Budget()
    try:
        document=LocalDocument(LocalParser(io.BytesIO(data),budget))
        ids=set()
        for xref in document.xrefs:
            for objid in xref.get_objids():
                ids.add(objid)
                if len(ids)>512: raise ValueError('PDF object count exceeds budget')
        seen=set()
        def walk(value,depth=0):
            budget.nodes+=1
            if budget.nodes>10000 or depth>32: raise ValueError('PDF object traversal exceeds budget')
            if isinstance(value,PDFObjRef):
                if value.objid in seen: return
                seen.add(value.objid); return walk(document.getobj(value.objid),depth+1)
            if isinstance(value,PDFStream):
                if not isinstance(value,BoundedStream): raise ValueError('Unbounded native PDF stream rejected')
                value.get_data(); return walk(value.attrs,depth+1)
            if isinstance(value,dict):
                for item in value.values(): walk(item,depth+1)
            elif isinstance(value,list):
                for item in value: walk(item,depth+1)
        for objid in ids:
            if objid not in seen:
                seen.add(objid); walk(document.getobj(objid))
        pages=0; page_seen=set()
        def page_tree(value,depth=0):
            nonlocal pages
            if depth>32: raise ValueError('PDF page tree exceeds depth')
            if isinstance(value,PDFObjRef):
                if value.objid in page_seen: raise ValueError('Cyclic PDF page tree')
                page_seen.add(value.objid)
            value=resolve1(value)
            if not isinstance(value,dict): raise ValueError('Invalid PDF page tree')
            kind=literal_name(value.get('Type'))
            if kind=='Page':
                pages+=1
                if pages>64: raise ValueError('PDF page count exceeds budget')
            elif kind=='Pages':
                kids=resolve1(value.get('Kids'))
                if not isinstance(kids,list) or len(kids)>512: raise ValueError('Invalid PDF page children')
                before=pages
                for child in kids: page_tree(child,depth+1)
                count=resolve1(value.get('Count'))
                if type(count) is not int or count!=pages-before: raise ValueError('Inconsistent PDF page count')
            else: raise ValueError('Unsupported PDF page structure')
        page_tree(document.catalog.get('Pages'))
        # Native PDFPage repair scans orphan xref Page objects when the tree is
        # empty. Those objects must not become a second accepted page model.
        for objid in ids:
            value=document.getobj(objid)
            if isinstance(value,dict) and literal_name(value.get('Type'))=='Page' and objid not in page_seen:
                raise ValueError('Orphan PDF page/fallback unsupported')
        return {'pages':pages,'objects':len(ids),'decoded_bytes':budget.decoded_bytes}
    except NotImplementedError: raise
    except ValueError: raise
    except Exception:
        raise ValueError('Malformed or unsupported PDF structure') from None


class BoundedPDFParser:
    def parse(self,path:Path)->dict:
        path=Path(path)
        with path.open('rb') as stream: data=stream.read(INPUT_LIMIT+1)
        validated=validate_pdf_bytes(data)
        # Semantica owns text parsing; never reopen the mutable caller path.
        from semantica.parse import PDFParser
        with tempfile.TemporaryDirectory(prefix='semantica-bounded-pdf-') as temporary:
            snapshot=Path(temporary)/'validated.pdf'
            with snapshot.open('xb') as output: output.write(data)
            result=PDFParser().parse(snapshot,extract_tables=False,extract_images=False)
        if result['total_pages']!=validated['pages'] or result['total_pages']>64:
            raise ValueError('Native PDF interpretation differs from validated page model')
        if len(result['full_text'].encode('utf-8'))>INPUT_LIMIT:
            raise ValueError('PDF text output exceeds budget')
        return {'text':result['full_text'],'pages':result['total_pages'],'metadata':result['metadata']}
