import React from 'react';
import {afterEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import OntologyWorkspace from './OntologyWorkspace';
import type {Job,Project,Revision,Source} from './types';

afterEach(cleanup);
const project:Project={project_id:'p1',name:'Workspace',namespace:'urn:test:',workspace_revision:'w2'};
const source:Source={source_id:'s1',project_id:'p1',format:'csv',revision:'srev1',sha256:'a'.repeat(64),size:12};
const revision:Revision={revision_id:'r1',project_id:'p1',layer:'tbox',content:{classes:[{id:'Asset'}]},dependencies:{},sha256:'b'.repeat(64),state:'DRAFT'};
const validation:Job={job_id:'j1',project_id:'p1',operation:'validate_shacl',state:'succeeded',attempt:1,run_id:'run-1',replay_of:null,error_code:null,result:{source_refs:['source:s1'],data:{conforms:true},artifact_refs:[]}};

describe('FDE ontology workspace',()=>{
  it('starts from real sources and states the missing discovery persistence boundary',()=>{
    render(<OntologyWorkspace project={project} sources={[source]} jobs={[]} revisions={[]} onSave={vi.fn()}/>);
    expect(screen.getByText('CSV 来源 · s1')).toBeTruthy();
    expect(screen.getByText(/访谈材料与业务事实的持久化接口尚未开放/)).toBeTruthy();
  });
  it('shows persisted model revisions and saves edited JSON as a real draft',async()=>{
    const save=vi.fn().mockResolvedValue(revision);
    render(<OntologyWorkspace project={project} sources={[]} jobs={[]} revisions={[revision]} onSave={save}/>);
    fireEvent.click(screen.getByRole('button',{name:/模型方案/}));
    expect(screen.getByText('Asset')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('本体层 JSON'),{target:{value:'{"classes":[{"id":"Equipment"}]}'}});
    fireEvent.click(screen.getByRole('button',{name:'保存 TBox 草稿'}));
    await waitFor(()=>expect(save).toHaveBeenCalledWith('tbox',{classes:[{id:'Equipment'}]},{}));
    expect(await screen.findByText('草稿已保存到后端修订记录。')).toBeTruthy();
  });
  it('uses actual validation jobs and keeps release actions unavailable',()=>{
    render(<OntologyWorkspace project={project} sources={[]} jobs={[validation]} revisions={[revision]} onSave={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:/场景验证/}));
    expect(screen.getByText('run-1')).toBeTruthy();
    expect(screen.getByText(/"conforms": true/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button',{name:/交付中心/}));
    expect((screen.getByRole('button',{name:'创建发布版本'}) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/发布与部署 API 尚未开放/)).toBeTruthy();
  });
});
