"""Immutable platform values. No native SDK imports or objects."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

Identifier = Annotated[str, Field(min_length=1,max_length=128,pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]*$')]


class ValueModel(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True,frozen=True)


class ArtifactRef(ValueModel):
    path: Annotated[str,Field(min_length=1,max_length=1024)]
    sha256: Annotated[str,Field(pattern='^[0-9a-f]{64}$')]
    size: Annotated[int,Field(ge=0,le=1048576)]
    kind: Identifier
    revision: Identifier


class ObjectRef(ValueModel):
    kind: Identifier
    id: Identifier
    revision: Identifier


class Request(ValueModel):
    run_id: Identifier
    workspace_revision: Identifier
    source_refs: Annotated[tuple[str,...],Field(min_length=1,max_length=1000)]
    scope_ref: Annotated[str,Field(pattern=r'^scope:[^\s]+$',max_length=512)]
    parameters: dict[str,JsonValue] = Field(default_factory=dict)

    @field_validator('parameters')
    @classmethod
    def no_unsupported_parameters(cls,value):
        if value:
            raise ValueError('Generic semantic parameters are not supported; use explicit typed request fields')
        return value

    @field_validator('source_refs')
    @classmethod
    def source_references(cls,value):
        if any(not item.startswith('source:') or len(item)>512 or any(c.isspace() for c in item) for item in value):
            raise ValueError('Invalid source reference')
        return value


class IngestRequest(Request):
    source: ArtifactRef
    source_revision: Identifier
    format: Literal['csv','json','sqlite','pdf','docx','turtle','nt']


class ParseRequest(Request):
    source: ArtifactRef
    source_revision: Identifier
    format: Literal['csv','json','pdf','docx']


class ExtractRequest(Request):
    source: ArtifactRef
    source_revision: Identifier


class GraphBuildRequest(Request):
    source: ArtifactRef
    graph_revision: Identifier


class OntologyRequest(Request):
    source: ArtifactRef
    schema_revision: Identifier
    action: Literal['import','edit','generate','export']
    format: Literal['turtle','nt'] = 'turtle'
    subject_uri: str | None = None
    label: Annotated[str,Field(max_length=4096)] | None = None
    language: str | None = None
    name: Identifier = 'WorkspaceOntology'
    base_uri: Annotated[str,Field(pattern=r'^(https?://|urn:)[^\s]+$')] = 'urn:ontology-workspace:'


class SHACLRequest(Request):
    source: ArtifactRef
    shapes: ArtifactRef
    graph_revision: Identifier
    shapes_revision: Identifier
    suite_revision: Identifier


class ReasoningRequest(Request):
    source: ArtifactRef
    rules: ArtifactRef
    graph_revision: Identifier
    ruleset_revision: Identifier


class Result(ValueModel):
    run_id: Identifier
    workspace_revision: Identifier
    backend_version: str
    adapter_version: str
    source_refs: tuple[str,...]
    artifact_refs: tuple[ArtifactRef,...]
    object_refs: tuple[ObjectRef,...] = ()
    data: dict[str,JsonValue]


class IngestResult(Result): pass
class ParseResult(Result): pass
class ExtractionResult(Result): pass
class GraphResult(Result): pass
class OntologyResult(Result): pass
class ValidationResult(Result): pass
class ReasoningResult(Result): pass


class Capability(ValueModel):
    operation: str
    supported: bool
    backend_version: str
    limitations: tuple[str,...] = ()
