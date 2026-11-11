"""Small genuine technical PDFs, never large decompression bombs."""
import zlib
import pytest
from patches.semantica.bounded_pdf import validate_pdf_bytes,BoundedPDFParser


def pdf(text='Native bounded PDF',*,compress=False,filter_name=None,indirect=False,filter_key='Filter'):
    content=b'BT /F1 12 Tf 10 40 Td ('+text.encode()+b') Tj ET'
    encoded=zlib.compress(content) if compress else content
    filter_name=filter_name or ('FlateDecode' if compress else None)
    header=b'/'+filter_key.encode()+b' /'+filter_name.encode()+b' ' if filter_name else b''
    length=b'6 0 R' if indirect else str(len(encoded)).encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',b'<< '+header+b'/Length '+length+b' >>\nstream\n'+encoded+b'\nendstream',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    if indirect: objects.append(str(len(encoded)).encode())
    return assemble(objects)


def assemble(objects):
    data=b'%PDF-1.4\n'; positions=[0]
    for index,obj in enumerate(objects,1):
        positions.append(len(data)); data+=str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    xref=len(data)
    data+=b'xref\n0 '+str(len(positions)).encode()+b'\n0000000000 65535 f \n'
    data+=b''.join(f'{pos:010d} 00000 n \n'.encode() for pos in positions[1:])
    data+=b'trailer\n<< /Size '+str(len(positions)).encode()+b' /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'
    return data


@pytest.mark.parametrize('compress,indirect',[(False,False),(True,False),(True,True)])
def test_genuine_pdf_native_text_and_budgets(tmp_path,compress,indirect):
    data=pdf(compress=compress,indirect=indirect)
    evidence=validate_pdf_bytes(data)
    assert evidence['pages']==1 and evidence['decoded_bytes']>0
    path=tmp_path/'source.pdf'; path.write_bytes(data)
    result=BoundedPDFParser().parse(path)
    assert 'Native bounded PDF' in result['text']


def test_small_compressed_expansion_is_rejected():
    data=pdf('x'*300000,compress=True)
    assert len(data)<2000
    with pytest.raises(ValueError): validate_pdf_bytes(data)


@pytest.mark.parametrize('filter_name',['LZWDecode','DCTDecode','ASCII85Decode','Crypt'])
def test_unsupported_filters_fail_closed(filter_name):
    with pytest.raises(NotImplementedError): validate_pdf_bytes(pdf(filter_name=filter_name))


def test_abbreviated_filter_cannot_bypass_decoding_budget():
    with pytest.raises(ValueError): validate_pdf_bytes(pdf('x'*300000,compress=True,filter_key='F'))


def test_conflicting_filter_aliases_and_external_params_fail_closed():
    encoded=zlib.compress(b'x'*300000)
    for attrs in [b'/Filter [] /F /FlateDecode',b'/Filter /FlateDecode /FDecodeParms << /Predictor 12 >>']:
        data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [] /Count 0 >>',b'<< '+attrs+b' /Length '+str(len(encoded)).encode()+b' >>\nstream\n'+encoded+b'\nendstream'])
        with pytest.raises(NotImplementedError): validate_pdf_bytes(data)


def test_decoder_globals_unchanged():
    from pdfminer.pdftypes import PDFStream
    from pdfminer.pdfparser import PDFParser
    original=(PDFStream.decode,PDFParser.do_keyword)
    validate_pdf_bytes(pdf(compress=True))
    assert original==(PDFStream.decode,PDFParser.do_keyword)


def test_malformed_and_input_budget_rejected():
    with pytest.raises(ValueError): validate_pdf_bytes(b'not a pdf')
    with pytest.raises(ValueError): validate_pdf_bytes(b'%PDF-'+b'x'*1048576)


def test_page_tree_cycle_rejected():
    data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [2 0 R] /Count 1 >>'])
    with pytest.raises(ValueError): validate_pdf_bytes(data)


def test_indirect_length_cycle_rejected():
    data=pdf(indirect=True).replace(b'6 0 obj\n51',b'6 0 obj\n6 0 R')
    # Use a freshly correct xref fixture, not invalid offsets masking the cycle.
    data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [] /Count 0 >>',b'<< /Length 4 0 R >>\nstream\nx\nendstream',b'4 0 R'])
    with pytest.raises(ValueError): validate_pdf_bytes(data)


def test_encrypted_pdf_is_explicitly_unsupported():
    data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [] /Count 0 >>'])
    data=data.replace(b'/Root 1 0 R >>',b'/Root 1 0 R /Encrypt << /Filter /Standard /V 1 >> >>')
    with pytest.raises(NotImplementedError): validate_pdf_bytes(data)


def test_excess_pages_and_nested_syntax_rejected():
    page=b'<< /Type /Page /MediaBox [0 0 100 100] /Parent 2 0 R >>'
    kids=b' '.join(str(index).encode()+b' 0 R' for index in range(3,68))
    data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids ['+kids+b'] /Count 65 >>']+[page]*65)
    with pytest.raises(ValueError,match='page count'): validate_pdf_bytes(data)
    data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [] /Count 0 >>',b'['*40+b'0'+b']'*40])
    with pytest.raises(ValueError): validate_pdf_bytes(data)


def test_many_objects_rejected():
    data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [] /Count 0 >>']+[b'0']*512)
    with pytest.raises(ValueError): validate_pdf_bytes(data)


def test_total_decoded_budget_rejected():
    raw=b'q '+b'0 '*100000+b'Q'
    stream=b'<< /Length '+str(len(raw)).encode()+b' >>\nstream\n'+raw+b'\nendstream'
    # Aggregate below input1MiB needs compression under permitted ratio100.
    # Mildly compressed variable technical tokens keep ratio well below100.
    raw=b' '.join(str(index).encode() for index in range(40000))
    compressed=zlib.compress(raw)
    stream=b'<< /Filter /FlateDecode /Length '+str(len(compressed)).encode()+b' >>\nstream\n'+compressed+b'\nendstream'
    data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [] /Count 0 >>']+[stream]*6)
    assert len(data)<1048576
    with pytest.raises(ValueError,match='decoded total'): validate_pdf_bytes(data)


def object_stream_pdf(*,bomb=False):
    data=b'%PDF-1.5\n'; offsets={}
    def append(number,obj):
        nonlocal data
        offsets[number]=len(data); data+=str(number).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    append(1,b'<< /Type /Catalog /Pages 2 0 R >>')
    append(2,b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
    append(3,b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>')
    content=b'BT /F1 12 Tf 10 40 Td (Bounded object stream) Tj ET'
    append(4,b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream')
    raw=b'5 0 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'+(b' '*300000 if bomb else b'')
    compressed=zlib.compress(raw)
    append(6,b'<< /Type /ObjStm /N 1 /First 4 /Filter /FlateDecode /Length '+str(len(compressed)).encode()+b' >>\nstream\n'+compressed+b'\nendstream')
    offsets[7]=len(data)
    entries=b'\x00'+(0).to_bytes(4,'big')+(65535).to_bytes(2,'big')
    for index in range(1,8):
        kind,first,second=(2,6,0) if index==5 else (1,offsets[index],0)
        entries+=bytes([kind])+first.to_bytes(4,'big')+second.to_bytes(2,'big')
    encoded=zlib.compress(entries)
    append(7,b'<< /Type /XRef /W [1 4 2] /Size 8 /Root 1 0 R /Filter /FlateDecode /Length '+str(len(encoded)).encode()+b' >>\nstream\n'+encoded+b'\nendstream')
    data+=b'startxref\n'+str(offsets[7]).encode()+b'\n%%EOF\n'
    return data


def test_compressed_xref_and_object_stream_native_text(tmp_path):
    data=object_stream_pdf()
    assert validate_pdf_bytes(data)['pages']==1
    path=tmp_path/'source.pdf'; path.write_bytes(data)
    assert 'Bounded object stream' in BoundedPDFParser().parse(path)['text']


def test_object_stream_first_resolution_is_bounded():
    with pytest.raises(ValueError): validate_pdf_bytes(object_stream_pdf(bomb=True))


def test_facade_parses_only_validated_snapshot(tmp_path,monkeypatch):
    from semantica.parse import PDFParser
    path=tmp_path/'source.pdf'; path.write_bytes(pdf())
    original=PDFParser.parse
    def raced(self,actual_path,**options):
        path.write_bytes(pdf('CHANGED AFTER VALIDATION'))
        return original(self,actual_path,**options)
    monkeypatch.setattr(PDFParser,'parse',raced)
    assert 'Native bounded PDF' in BoundedPDFParser().parse(path)['text']


def test_filter_chain_and_predictor_rejected():
    for attrs in [b'/Filter [/FlateDecode /FlateDecode]',b'/Filter /FlateDecode /DecodeParms << /Predictor 12 >>']:
        raw=zlib.compress(b'x')
        data=assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [] /Count 0 >>',b'<< '+attrs+b' /Length '+str(len(raw)).encode()+b' >>\nstream\n'+raw+b'\nendstream'])
        with pytest.raises(NotImplementedError): validate_pdf_bytes(data)
