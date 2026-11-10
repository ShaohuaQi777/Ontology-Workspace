"""Strict, platform-owned evidence values, never native objects or errors."""
from __future__ import annotations
import importlib.metadata
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

FORMATS = {'csv', 'json', 'sqlite', 'pdf', 'docx', 'turtle', 'n-triples', 'xml', 'json-ld'}


def safe_parameters(parameters: dict) -> dict[str, str | bool]:
    safe = {}
    for key, value in parameters.items():
        if key == 'format' and type(value) is str and value in FORMATS:
            safe[key] = value
        elif key == 'language' and value in ('en', 'zh'):
            safe[key] = value
        elif key in {'extract_text', 'extract_tables', 'extract_images', 'inference_enabled'} and type(value) is bool:
            safe[key] = value
    return safe


def installed_backend_version() -> str | None:
    try:
        return importlib.metadata.version('semantica')
    except importlib.metadata.PackageNotFoundError:
        return None


class ProbeEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    case_id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,79}$')
    status: Literal['passed', 'failed', 'unavailable']
    backend_version: str | None
    api_symbol: str = ''
    run_id: str = Field(min_length=1, max_length=128)
    source_refs: list[str] = Field(default_factory=list)
    parameters: dict[str, str | bool] = Field(default_factory=dict)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    checks: dict[str, bool] = Field(default_factory=dict)
    error_code: str | None = None

    @model_validator(mode='after')
    def validate_evidence(self):
        if self.parameters != safe_parameters(self.parameters):
            raise ValueError('Evidence parameters must be allowlisted')
        if self.status == 'passed':
            if (not self.backend_version or not self.api_symbol.startswith('semantica.')
                    or not self.source_refs or not self.checks
                    or not all(self.checks.values()) or self.error_code is not None):
                raise ValueError('Successful evidence requires version, native API, source and passing checks')
        elif not self.error_code:
            raise ValueError('Non-successful evidence requires a stable error code')
        return self
