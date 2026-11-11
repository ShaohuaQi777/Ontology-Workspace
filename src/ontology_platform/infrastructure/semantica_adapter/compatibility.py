"""Scalar upgrade comparison through the native lexical-preserving document API."""
from rdflib import BNode
from rdflib.compare import isomorphic


def native_nt_isomorphic(left:str,right:str)->bool:
    from semantica.ontology.document import OntologyDocument
    graphs=[]
    for data in (left,right):
        if not isinstance(data,str) or len(data.encode())>1048576: return False
        document=OntologyDocument.from_rdf(data,format='nt',base_uri='urn:ontology-workspace:upgrade:')
        graph=document._graph  # native-owned graph stays inside Adapter boundary
        if len(graph)>128 or len({term for triple in graph for term in triple if isinstance(term,BNode)})>32: return False
        graphs.append(graph)
    return bool(isomorphic(*graphs))
