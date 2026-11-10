"""Instance-local RDFLib parser adapters preserving RDF literal lexical terms.

SPDX-License-Identifier: MIT
No mutation of rdflib global normalization flags or parser registries.
"""
from io import StringIO
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from rdflib.plugins.parsers import notation3, ntriples


def strict_literal(text, *, datatype=None, lang=None):
    # RDFLib always collapses token/normalizedString whitespace even with
    # normalize=False. Preserve lexical str while retaining its value metadata.
    prepared = Literal(text, datatype=datatype, lang=lang, normalize=False)
    result = str.__new__(Literal, text)
    for field in Literal.__slots__:
        setattr(result, field, getattr(prepared, field))
    return result


class LexicalSink(notation3.RDFSink):
    def newLiteral(self, s, dt, lang):
        return strict_literal(s, datatype=dt, lang=lang)


class LexicalTurtleParser(notation3.SinkParser):
    def nodeOrLiteral(self, argstr, i, res):
        result = self.node(argstr, i, res)
        if result >= 0:
            return result
        offset = self.skipSpace(argstr, i)
        if offset >= 0:
            for pattern, datatype in [(notation3.exponent_syntax, XSD.double),
                                      (notation3.decimal_syntax, XSD.decimal),
                                      (notation3.integer_syntax, XSD.integer)]:
                match = pattern.match(argstr, offset)
                if match:
                    res.append(strict_literal(argstr[offset:match.end()], datatype=datatype))
                    return match.end()
        return super().nodeOrLiteral(argstr, i, res)


class LexicalNTParser(ntriples.W3CNTriplesParser):
    def literal(self):
        if not self.peek('"'):
            return False
        text, language, datatype = self.eat(ntriples.r_literal).groups()
        datatype = URIRef(ntriples.uriquote(ntriples.unquote(datatype))) if datatype else None
        if language and datatype:
            raise ntriples.ParseError('Language and datatype cannot both be specified')
        return strict_literal(ntriples.unquote(text), lang=language or None, datatype=datatype)


def parse_lexical(graph, data, format, base_uri):
    if format == 'nt':
        LexicalNTParser(ntriples.NTGraphSink(graph)).parse(StringIO(data))
    else:
        parser = LexicalTurtleParser(LexicalSink(graph), baseURI=base_uri or graph.absolutize(''), turtle=True)
        parser.loadBuf(data)
        for prefix, namespace in parser._bindings.items():
            graph.bind(prefix, namespace)
