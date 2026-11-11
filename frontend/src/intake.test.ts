import {describe,it,expect} from 'vitest';
import {makePreview,sourceJob} from './intake';
describe('native result projection, never substitute native parsing',()=>{
 it('renders native CSV columns and actual missing values',()=>{
  const p=makePreview({headers:['id','value'],rows:[['r1',''],['r2','a']],row_count:2});
  expect(p.columns.map(c=>c.name)).toEqual(['id','value']);expect(p.rows[0].value).toBe('');expect(p.columns[1].emptyCount).toBe(1);expect(p.sampleOnly).toBe(false);
 });
 it('supports native record-shaped CSV without losing values',()=>{const p=makePreview({headers:['id'],rows:[{id:'r1'}],row_count:1});expect(p.rows[0]).toEqual({id:'r1'})});
 it('uses JSON content rather than pretending every document is a table',()=>{expect(makePreview({type:'array',content:[{key:1},{key:null}]}).columns[0].emptyCount).toBe(1);expect(makePreview({text:'A paragraph',paragraphs:['A paragraph']}).text).toBe('A paragraph');expect(makePreview({text:'A paragraph'}).columns).toEqual([])});
 it('bounds actual preview and labels quality as sample-only',()=>{const p=makePreview({headers:['id'],rows:Array.from({length:230},(_,i)=>[i]),row_count:230});expect(p.rows).toHaveLength(200);expect(p.sampleOnly).toBe(true)});
 it('never associates a failed or different source job by project alone',()=>{const a={job_id:'j',project_id:'p',operation:'parse',state:'succeeded',attempt:1,run_id:'run-a',replay_of:null,error_code:null,result:{source_refs:['source:other'],data:{},artifact_refs:[]}};expect(sourceJob('mine',[a])).toBeUndefined();expect(sourceJob('other',[a])?.run_id).toBe('run-a')});
 it.each([false,null,7,'root'])('preserves a native JSON scalar root %s rather than displaying empty rows',value=>{const p=makePreview({content:value});expect(p.text).toBe(JSON.stringify(value));expect(p.rows).toEqual([])});
 it('unknown data is not fabricated into preview rows',()=>{expect(makePreview({unsupported:true}).rows).toEqual([]);expect(makePreview({unsupported:true}).text).toBeUndefined()});
});
