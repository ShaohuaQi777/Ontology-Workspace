"""Product backend selection; test doubles are never registered here."""
from pathlib import Path
from ontology_platform.semantic.backend import SemanticBackend


def create_backend(kind:str,artifact_root:Path)->SemanticBackend:
    if kind!='semantica':
        raise ValueError('Only the native semantica backend is supported')
    from ontology_platform.infrastructure.semantica_adapter.backend import SemanticaBackend
    return SemanticaBackend(artifact_root)
