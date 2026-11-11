import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {api, ApiError} from './api';
import type {Connection, Job, Project, Source, User} from './types';

// Domain-neutral fixtures only. Fetch is the external boundary; the API code is real.
const user: User = {user_id:'user-1',username:'tester',global_role:'engineer'};
const project: Project = {project_id:'project-1',name:'Workspace',namespace:'urn:workspace:',workspace_revision:'workspace-3'};
const source: Source = {source_id:'source-1',project_id:'project-1',format:'csv',revision:'source-2',sha256:'a'.repeat(64),size:12};
const job: Job = {job_id:'job-1',project_id:'project-1',operation:'parse',state:'pending',attempt:1,run_id:'run-1',replay_of:null,error_code:null,result:null};
const connection: Connection = {connection_id:'connection-1',project_id:'project-1',name:'Configured',target_alias:'local',kind:'sqlite',revision:'connection-2',status:'CONFIGURED'};
let transport: ReturnType<typeof vi.fn<typeof fetch>>;
function reply(value: unknown, status=200) { return new Response(JSON.stringify(value), {status,headers:{'content-type':'application/json'}}); }
function lastRequest() { const [url,init] = transport.mock.calls.at(-1)!; return {url,init:init!}; }
function body() { return JSON.parse(lastRequest().init.body as string); }

beforeEach(() => { transport=vi.fn<typeof fetch>(); vi.stubGlobal('fetch',transport); });
afterEach(() => { vi.unstubAllGlobals(); });

describe('same-origin authenticated API contracts', () => {
  it('reads the current user through the relative cookie endpoint', async () => {
    transport.mockResolvedValue(reply(user));
    expect(await api.me()).toEqual({user_id:'user-1',username:'tester',global_role:'engineer'});
    expect(lastRequest()).toMatchObject({url:'/api/session/me',init:{credentials:'include',method:'GET'}});
  });
  it('posts login JSON without identity headers or local persistence', async () => {
    const storage=vi.spyOn(Storage.prototype,'setItem');
    const log=vi.spyOn(console,'log'); const error=vi.spyOn(console,'error');
    transport.mockResolvedValue(reply(user));
    expect(await api.login('tester','test-only-secret')).toEqual(user);
    expect(lastRequest()).toMatchObject({url:'/api/session/login',init:{credentials:'include',method:'POST',body:'{"username":"tester","password":"test-only-secret"}'}});
    expect(new Headers(lastRequest().init.headers).get('content-type')).toBe('application/json');
    expect(new Headers(lastRequest().init.headers).has('authorization')).toBe(false);
    expect(storage).not.toHaveBeenCalled(); expect(log).not.toHaveBeenCalled(); expect(error).not.toHaveBeenCalled();
  });
  it('logs out with a JSON body accepted by the server boundary', async () => {
    transport.mockResolvedValue(reply({status:'logged_out'})); await api.logout();
    expect(lastRequest()).toMatchObject({url:'/api/session/logout',init:{method:'POST',credentials:'include',body:'{}'}});
  });
  it('returns exactly one project page and never treats grant-filtered empty items as EOF', async () => {
    const signal=new AbortController().signal;
    transport.mockResolvedValueOnce(reply({items:[]})).mockResolvedValueOnce(reply({items:[project]}));
    expect(await api.projects(0,signal)).toEqual([]);
    expect(lastRequest()).toMatchObject({url:'/api/projects?limit=50&offset=0',init:{signal,credentials:'include'}});
    expect(transport).toHaveBeenCalledTimes(1);
    expect(await api.projects(50,signal)).toEqual([project]);
    expect(lastRequest().url).toBe('/api/projects?limit=50&offset=50');
  });
  it('creates projects only through the fixed public DTO', async () => {
    transport.mockResolvedValue(reply(project,201)); expect(await api.createProject('Workspace','urn:workspace:')).toEqual(project);
    expect(lastRequest()).toMatchObject({url:'/api/projects',init:{method:'POST',credentials:'include'}});
    expect(body()).toEqual({name:'Workspace',namespace:'urn:workspace:'});
  });
  it('unwraps source and job items while retaining cancellation', async () => {
    const signal=new AbortController().signal;
    transport.mockResolvedValueOnce(reply({items:[source]})).mockResolvedValueOnce(reply({items:[job]}));
    expect(await api.sources('project-1',signal)).toEqual([source]);
    expect(lastRequest()).toMatchObject({url:'/api/projects/project-1/sources',init:{signal,credentials:'include'}});
    expect(await api.jobs('project-1',signal)).toEqual([job]);
    expect(lastRequest()).toMatchObject({url:'/api/projects/project-1/jobs',init:{signal,credentials:'include'}});
  });
  it('reads connections as the server array, not an invented items envelope', async () => {
    const signal=new AbortController().signal; transport.mockResolvedValue(reply([connection]));
    expect(await api.connections('project-1',signal)).toEqual([connection]);
    expect(lastRequest()).toMatchObject({url:'/api/projects/project-1/connections',init:{signal,credentials:'include'}});
  });
  it('reads actual source bytes through the permission-checked API only', async () => {
    const bytes=new Uint8Array([0,1,255]); const signal=new AbortController().signal;
    transport.mockResolvedValue(new Response(bytes));
    expect(new Uint8Array(await api.sourceBytes('project-1','source-1',signal))).toEqual(bytes);
    expect(lastRequest()).toMatchObject({url:'/api/projects/project-1/sources/source-1',init:{method:'GET',credentials:'include',signal}});
  });
  it('reads a job by server run ID and preserves result evidence', async () => {
    const completed: Job={...job,state:'succeeded',result:{source_refs:['source:source-1'],data:{values:[1,2]},artifact_refs:[{path:'artifact-1',sha256:'b'.repeat(64),size:2,kind:'json',revision:'result-1'}]}};
    const signal=new AbortController().signal; transport.mockResolvedValue(reply(completed));
    expect(await api.getJob('run-1',signal)).toEqual(completed);
    expect(lastRequest()).toMatchObject({url:'/api/jobs/run-1',init:{signal,credentials:'include'}});
  });
});

describe('file boundaries', () => {
  it('posts the File itself as raw bytes without multipart, filename or parse configuration', async () => {
    const file=new File(['a,b\n1,2\n'],'local-only.csv'); transport.mockResolvedValue(reply(source,201));
    expect(await api.upload('project-1',file,'csv')).toEqual(source);
    expect(lastRequest()).toMatchObject({url:'/api/projects/project-1/sources?format=csv',init:{method:'POST',credentials:'include',body:file}});
    expect(new Headers(lastRequest().init.headers).get('content-type')).toBe('application/octet-stream');
  });
  it.each([['csv',1048576],['json',1048576],['pdf',1048576],['docx',1048576]])('accepts the exact %s file budget', async (format,size) => {
    transport.mockResolvedValue(reply({...source,format,size},201));
    await api.upload('project-1',new File([new Uint8Array(size)],'local'),format);
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it.each([['csv',0,'EMPTY_FILE'],['csv',1048577,'BODY_TOO_LARGE'],['json',1048577,'BODY_TOO_LARGE']])('rejects %s at size %i before sending', async (format,size,code) => {
    await expect(api.upload('project-1',new File([new Uint8Array(size)],'local'),format)).rejects.toMatchObject({code,status:0,runId:null});
    expect(transport).not.toHaveBeenCalled();
  });
  it('accepts a text snapshot upload without claiming text parse support', async () => {
    transport.mockResolvedValue(reply({...source,format:'text'},201));
    await api.upload('project-1',new File(['plain text'],'local'),'text');
    expect(lastRequest().url).toBe('/api/projects/project-1/sources?format=text');
    await expect(api.parse(project,{...source,format:'text'})).rejects.toMatchObject({code:'UNSUPPORTED_FORMAT'});
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('rejects sqlite upload because public source registration does not accept databases', async () => {
    transport.mockResolvedValue(reply({...source,format:'sqlite'},201));
    await expect(api.upload('project-1',new File(['bytes'],'local'),'sqlite')).rejects.toMatchObject({code:'UNSUPPORTED_FORMAT'});
    expect(transport).not.toHaveBeenCalled();
  });
  it('rejects unsupported upload formats instead of inventing an ingestion path', async () => {
    await expect(api.upload('project-1',new File(['x'],'local'),'xml')).rejects.toMatchObject({code:'UNSUPPORTED_FORMAT'});
    expect(transport).not.toHaveBeenCalled();
  });
  it('bounds outbound JSON by UTF-8 bytes, not characters', async () => {
    await expect(api.createProject('界'.repeat(45000),'urn:workspace:')).rejects.toMatchObject({code:'BODY_TOO_LARGE',status:0});
    expect(transport).not.toHaveBeenCalled();
  });
});

describe('immutable parse binding and explicit replay', () => {
  it.each(['csv','json','pdf','docx'])('binds %s to its exact immutable snapshot and workspace', async format => {
    transport.mockResolvedValue(reply(job,202));
    expect(await api.parse(project,{...source,format})).toEqual(job);
    expect(lastRequest()).toMatchObject({url:'/api/projects/project-1/jobs',init:{method:'POST',credentials:'include'}});
    const submitted=body();
    expect(submitted).toEqual({operation:'parse',expected_workspace_revision:'workspace-3',idempotency_key:expect.stringMatching(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i),request:{run_id:'server-assigned',workspace_revision:'workspace-3',source_refs:['source:source-1'],scope_ref:'scope:project-1',source:{path:'source-1',sha256:'a'.repeat(64),size:12,kind:format,revision:'source-2'},source_revision:'source-2',format}});
  });
  it('binds a JSON snapshot at the raw file budget without applying the API JSON body budget', async () => {
    transport.mockResolvedValue(reply(job,202));
    await api.parse(project,{...source,format:'json',size:1048576});
    expect(body().request.source.size).toBe(1048576);
    expect(body().request.format).toBe('json');
  });
  it('uses fresh cryptographic UUID keys per explicit submission and replay', async () => {
    transport.mockImplementation(async () => reply(job,202));
    await api.parse(project,source); const first=body().idempotency_key;
    await api.parse(project,source); const second=body().idempotency_key;
    await api.replay('run-1'); const third=body().idempotency_key;
    expect(new Set([first,second,third]).size).toBe(3);
    expect(lastRequest().url).toBe('/api/jobs/run-1/replay');
    expect(body()).toEqual({idempotency_key:expect.stringMatching(/^[0-9a-f-]{36}$/i)});
  });
  it('uses crypto.randomUUID rather than a pseudo-random idempotency fallback', async () => {
    const randomUUID=vi.fn().mockReturnValue('12345678-1234-4234-9234-123456789abc');
    vi.stubGlobal('crypto',{randomUUID}); transport.mockResolvedValue(reply(job,202));
    await api.parse(project,source); expect(body().idempotency_key).toBe('12345678-1234-4234-9234-123456789abc');
  });
  it('fails closed when secure UUID generation is unavailable', async () => {
    vi.stubGlobal('crypto',{});
    await expect(api.parse(project,source)).rejects.toMatchObject({code:'CLIENT_ERROR'});
    expect(transport).not.toHaveBeenCalled();
  });
  it.each(['sqlite','turtle','nt','xml'])('does not parse unsupported format %s', async format => {
    await expect(api.parse(project,{...source,format})).rejects.toMatchObject({code:'UNSUPPORTED_FORMAT'});
    expect(transport).not.toHaveBeenCalled();
  });
  it('rejects cross-project source binding before any job request', async () => {
    await expect(api.parse(project,{...source,project_id:'project-2'})).rejects.toMatchObject({code:'INVALID_SOURCE'});
    expect(transport).not.toHaveBeenCalled();
  });
  it.each([{sha256:'broken'},{size:-1},{size:1048577},{revision:'../private'},{source_id:'../private'}])('rejects malformed immutable binding %j', async changed => {
    await expect(api.parse(project,{...source,...changed})).rejects.toBeInstanceOf(ApiError);
    expect(transport).not.toHaveBeenCalled();
  });
  it('never automatically resubmits when network outcome is unknown', async () => {
    transport.mockRejectedValue(new TypeError('private diagnostic'));
    await expect(api.parse(project,source)).rejects.toMatchObject({code:'NETWORK_ERROR',status:0,runId:null});
    expect(transport).toHaveBeenCalledTimes(1);
  });
});

describe('safe failures and fixed routes', () => {
  it.each([[401,'UNAUTHENTICATED'],[403,'FORBIDDEN'],[409,'STALE_REVISION'],[413,'BODY_TOO_LARGE']])('preserves status %i and fixed %s code', async (status,code) => {
    transport.mockResolvedValue(reply({code,run_id:'request-abc',detail:'private input'},status));
    try { await api.me(); throw new Error('expected failure'); } catch (error) {
      expect(error).toBeInstanceOf(ApiError); expect(error).toMatchObject({code,runId:'request-abc',status});
      expect(String(error)).not.toContain('private input'); expect(JSON.stringify(error)).not.toContain('private input');
    }
  });
  it('does not echo malicious code/run_id or extra backend error body', async () => {
    transport.mockResolvedValue(reply({code:'private input',run_id:'https://user:private@example.invalid',password:'private input'},500));
    await expect(api.me()).rejects.toMatchObject({code:'HTTP_ERROR',runId:null,status:500});
  });
  it('maps malformed error bodies to fixed status-aware errors', async () => {
    transport.mockResolvedValue(new Response('<html>private input</html>',{status:403}));
    await expect(api.me()).rejects.toMatchObject({code:'FORBIDDEN',runId:null,status:403});
  });
  it('maps invalid successful JSON to a fixed error without response body', async () => {
    transport.mockResolvedValue(new Response('private input',{status:200}));
    await expect(api.me()).rejects.toMatchObject({code:'INVALID_RESPONSE',status:200,runId:null});
  });
  it('preserves abort semantics for stale request cancellation', async () => {
    const aborted=new DOMException('Abort','AbortError'); transport.mockRejectedValue(aborted);
    await expect(api.sources('project-1',new AbortController().signal)).rejects.toBe(aborted);
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it.each(['../private','https://example.invalid','id?extra=1','id/bytes','id#fragment',''])('rejects non-identifiers %s before route construction', async id => {
    await expect(api.sourceBytes('project-1',id)).rejects.toMatchObject({code:'INVALID_REQUEST'});
    expect(transport).not.toHaveBeenCalled();
  });
  it.each([-1,0.5,Number.NaN])('rejects invalid pagination offset %s without a request', async offset => {
    await expect(api.projects(offset)).rejects.toMatchObject({code:'INVALID_REQUEST'});
    expect(transport).not.toHaveBeenCalled();
  });
  it('percent-encodes otherwise valid identifiers without arbitrary endpoints', async () => {
    transport.mockResolvedValue(reply({items:[]})); await api.sources('project:1');
    expect(lastRequest().url).toBe('/api/projects/project%3A1/sources');
  });
});
