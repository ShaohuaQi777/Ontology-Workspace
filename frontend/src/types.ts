/** Public platform DTOs only; no SDK objects, credentials or client file paths. */
export interface User {
  user_id: string;
  username: string;
  global_role: string;
}

export interface Project {
  project_id: string;
  name: string;
  namespace: string;
  workspace_revision: string;
}

/** A registered, immutable source snapshot. Local display names are not persisted. */
export interface Source {
  source_id: string;
  project_id: string;
  format: string;
  revision: string;
  sha256: string;
  size: number;
}

export interface ArtifactRef {
  path: string;
  sha256: string;
  size: number;
  kind: string;
  revision: string;
}

export interface Job {
  job_id: string;
  project_id: string;
  operation: string;
  state: string;
  attempt: number;
  run_id: string;
  replay_of: string | null;
  error_code: string | null;
  result: null | {
    source_refs: string[];
    data: Record<string, unknown>;
    artifact_refs: ArtifactRef[];
  };
}

/** Public configuration metadata, not evidence that any data was ingested. */
export interface Connection {
  connection_id: string;
  project_id: string;
  name: string;
  target_alias: string;
  kind: string;
  revision: string;
  status: string;
}

/** Immutable ontology-layer revision returned by the workspace service. */
export interface Revision {
  revision_id: string;
  project_id: string;
  layer: 'tbox' | 'abox' | 'shacl' | 'rules' | 'vocabulary';
  content: Record<string, unknown>;
  dependencies: Record<string, string>;
  sha256: string;
  state: 'DRAFT' | 'CERTIFIED';
}
