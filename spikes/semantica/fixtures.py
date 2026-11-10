"""Domain-neutral technical fixtures only; no manufacturing/business gold data."""
from pathlib import Path

GRAPH = {'entities': [{'id': 'n1', 'type': 'Node'}, {'id': 'n2', 'type': 'Node'}],
         'relationships': [{'source': 'n1', 'target': 'n2', 'type': 'linksTo'}]}

COMPLEX_TTL = '''@prefix ex: <https://example.invalid/probe/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
ex: a owl:Ontology; owl:imports <https://example.invalid/not-authorized> .
ex:Node a owl:Class; rdfs:label "Technical node";
 rdfs:subClassOf [a owl:Restriction; owl:onProperty ex:p; owl:someValuesFrom ex:Node] .
ex:p a owl:ObjectProperty .
'''

SHAPES = '''@prefix ex: <https://example.invalid/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
ex:S a sh:NodeShape; sh:targetNode ex:n1;
 sh:property [sh:path ex:p; sh:minCount 1] .
'''


def make_pdf(path: Path) -> Path:
    stream = b'BT /F1 12 Tf 72 720 Td (Probe text) Tj ET\n'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'endstream']
    data = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f'{number} 0 obj\n'.encode() + body + b'\nendobj\n')
    start = len(data)
    data.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for offset in offsets[1:]:
        data.extend(f'{offset:010d} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    path.write_bytes(data)
    return path


def make_docx(path: Path) -> Path:
    from docx import Document
    document = Document()
    document.add_paragraph('Probe text')
    document.save(path)
    return path
