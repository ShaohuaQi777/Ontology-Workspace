import type {Connection, Job, Project, Source, User} from './types';

const JSON_LIMIT = 131072;
const FILE_LIMIT = 1048576;
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
const PARSE_FORMATS = new Set(['csv', 'json', 'pdf', 'docx']);
const UPLOAD_FORMATS = new Set(['csv', 'json', 'text', 'pdf', 'docx', 'turtle', 'nt']);

// Exact server boundary/service codes, plus fixed local failures. Never surface
// arbitrary response messages, submitted values or a native exception string.
const ERROR_CODES = [
  'UNSUPPORTED_SCHEMA', 'STORAGE_UNAVAILABLE', 'NOT_INITIALIZED',
  'SECRET_UNAVAILABLE', 'INVALID_ACCOUNT', 'ACCOUNT_EXISTS', 'BOOTSTRAP_DISABLED',
  'AUTHENTICATION_FAILED', 'UNAUTHENTICATED', 'LOGIN_RATE_LIMIT', 'FORBIDDEN',
  'INVALID_WORKSPACE', 'NAMESPACE_CONFLICT', 'STALE_REVISION', 'INVALID_DEPENDENCY',
  'INVALID_SOURCE', 'INVALID_JOB', 'INVALID_CONNECTION', 'CONNECTION_NOT_FOUND',
  'TARGET_CHANGED', 'IDEMPOTENCY_CONFLICT', 'UNSAFE_REPLAY', 'NOT_FOUND',
  'METHOD_NOT_ALLOWED', 'HTTP_ERROR', 'INVALID_REQUEST', 'INTERNAL_ERROR',
  'NOT_READY', 'BODY_TOO_LARGE', 'ORIGIN_FORBIDDEN', 'UNSUPPORTED_MEDIA_TYPE',
  'EMPTY_FILE', 'UNSUPPORTED_FORMAT', 'CLIENT_ERROR', 'NETWORK_ERROR', 'INVALID_RESPONSE',
] as const;
export type ApiErrorCode = typeof ERROR_CODES[number];
const SAFE_CODES: ReadonlySet<string> = new Set(ERROR_CODES);

export class ApiError extends Error {
  constructor(
    public readonly code: ApiErrorCode,
    public readonly runId: string | null,
    public readonly status: number,
  ) {
    super(code);
    this.name = 'ApiError';
  }
}

function fail(code: ApiErrorCode): never { throw new ApiError(code, null, 0); }
function identifier(value: string): string {
  if (typeof value !== 'string' || !IDENTIFIER.test(value) || value === '.' || value === '..') fail('INVALID_REQUEST');
  return encodeURIComponent(value);
}
function projectPath(projectId: string): string { return `/api/projects/${identifier(projectId)}`; }
function runPath(runId: string): string { return `/api/jobs/${identifier(runId)}`; }
function jsonBody(value: unknown): string {
  let text: string;
  try { text = JSON.stringify(value); } catch { return fail('INVALID_REQUEST'); }
  if (new TextEncoder().encode(text).byteLength > JSON_LIMIT) fail('BODY_TOO_LARGE');
  return text;
}
function idempotencyKey(): string {
  try {
    const value = globalThis.crypto.randomUUID();
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) return fail('CLIENT_ERROR');
    return value;
  } catch { return fail('CLIENT_ERROR'); }
}

async function request(path: string, init: RequestInit): Promise<Response> {
  let response: Response;
  try {
    // All callers construct fixed relative /api routes. No public generic fetch
    // or endpoint argument, no identity headers, no storage, and no retries.
    response = await fetch(path, {...init, credentials: 'include'});
  } catch (error) {
    if (error !== null && typeof error === 'object' && 'name' in error && error.name === 'AbortError') throw error;
    throw new ApiError('NETWORK_ERROR', null, 0);
  }
  if (!response.ok) {
    const fallback: ApiErrorCode = response.status === 401 ? 'UNAUTHENTICATED' : response.status === 403 ? 'FORBIDDEN' : 'HTTP_ERROR';
    let code: ApiErrorCode = fallback;
    let runId: string | null = null;
    try {
      const value: unknown = await response.json();
      if (value !== null && typeof value === 'object') {
        const body = value as Record<string, unknown>;
        if (typeof body.code === 'string' && SAFE_CODES.has(body.code)) code = body.code as ApiErrorCode;
        if (typeof body.run_id === 'string' && IDENTIFIER.test(body.run_id)) runId = body.run_id;
      }
    } catch { /* Discard the entire untrusted error body. */ }
    throw new ApiError(code, runId, response.status);
  }
  return response;
}

async function json<T>(path: string, init: RequestInit): Promise<T> {
  const response = await request(path, init);
  try { return await response.json() as T; }
  catch (error) {
    if (error !== null && typeof error === 'object' && 'name' in error && error.name === 'AbortError') throw error;
    throw new ApiError('INVALID_RESPONSE', null, response.status);
  }
}
function get<T>(path: string, signal?: AbortSignal): Promise<T> { return json<T>(path, {method: 'GET', signal}); }
async function post<T>(path: string, value: unknown): Promise<T> {
  return json<T>(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: jsonBody(value)});
}

export const api = {
  me(): Promise<User> { return get('/api/session/me'); },
  login(username: string, password: string): Promise<User> {
    return post('/api/session/login', {username, password});
  },
  async logout(): Promise<void> { await post('/api/session/logout', {}); },
  async projects(offset = 0, signal?: AbortSignal): Promise<Project[]> {
    if (!Number.isSafeInteger(offset) || offset < 0) fail('INVALID_REQUEST');
    // SQL LIMIT precedes grant filtering: even an empty page does NOT mean EOF.
    // Fetch a single explicit offset only; callers may request the next page.
    return (await get<{items: Project[]}>(`/api/projects?limit=50&offset=${offset}`, signal)).items;
  },
  createProject(name: string, namespace: string): Promise<Project> {
    return post('/api/projects', {name, namespace});
  },
  async sources(projectId: string, signal?: AbortSignal): Promise<Source[]> {
    return (await get<{items: Source[]}>(`${projectPath(projectId)}/sources`, signal)).items;
  },
  async jobs(projectId: string, signal?: AbortSignal): Promise<Job[]> {
    return (await get<{items: Job[]}>(`${projectPath(projectId)}/jobs`, signal)).items;
  },
  connections(projectId: string, signal?: AbortSignal): Promise<Connection[]> {
    return get(`${projectPath(projectId)}/connections`, signal);
  },
  async upload(projectId: string, file: File, format: string): Promise<Source> {
    if (!UPLOAD_FORMATS.has(format)) fail('UNSUPPORTED_FORMAT');
    if (file.size === 0) fail('EMPTY_FILE');
    if (file.size > FILE_LIMIT) fail('BODY_TOO_LARGE');
    return json<Source>(`${projectPath(projectId)}/sources?format=${format}`, {
      method: 'POST', headers: {'Content-Type': 'application/octet-stream'}, body: file,
    });
  },
  async parse(project: Project, source: Source): Promise<Job> {
    if (!PARSE_FORMATS.has(source.format)) fail('UNSUPPORTED_FORMAT');
    if (source.project_id !== project.project_id || !/^[0-9a-f]{64}$/.test(source.sha256)
      || !Number.isSafeInteger(source.size) || source.size <= 0 || source.size > FILE_LIMIT) fail('INVALID_SOURCE');
    identifier(source.source_id); identifier(source.revision); identifier(project.workspace_revision);
    return post(`${projectPath(project.project_id)}/jobs`, {
      operation: 'parse',
      expected_workspace_revision: project.workspace_revision,
      idempotency_key: idempotencyKey(),
      request: {
        run_id: 'server-assigned', workspace_revision: project.workspace_revision,
        source_refs: [`source:${source.source_id}`], scope_ref: `scope:${project.project_id}`,
        source: {path: source.source_id, sha256: source.sha256, size: source.size, kind: source.format, revision: source.revision},
        source_revision: source.revision, format: source.format,
      },
    });
  },
  getJob(runId: string, signal?: AbortSignal): Promise<Job> { return get(runPath(runId), signal); },
  async replay(runId: string): Promise<Job> {
    return post(`${runPath(runId)}/replay`, {idempotency_key: idempotencyKey()});
  },
  async sourceBytes(projectId: string, sourceId: string, signal?: AbortSignal): Promise<ArrayBuffer> {
    const response = await request(`${projectPath(projectId)}/sources/${identifier(sourceId)}`, {method: 'GET', signal});
    try { return await response.arrayBuffer(); }
    catch (error) {
      if (error !== null && typeof error === 'object' && 'name' in error && error.name === 'AbortError') throw error;
      throw new ApiError('INVALID_RESPONSE', null, response.status);
    }
  },
};
