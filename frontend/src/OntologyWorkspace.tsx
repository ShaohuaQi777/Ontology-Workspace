import React,{useEffect,useMemo,useState} from 'react';
import type {Job,Project,Revision,Source} from './types';

const stages=[
  ['discovery','1','场景理解','来源与事实边界'],
  ['questions','2','业务问题','能力问题与验收口径'],
  ['model','3','模型方案','分层修订与编辑'],
  ['validation','4','场景验证','真实任务证据'],
  ['delivery','5','交付中心','就绪度与发布边界'],
] as const;
const layers:Revision['layer'][]=['tbox','abox','shacl','rules','vocabulary'];
const layerName:Record<Revision['layer'],string>={tbox:'TBox',abox:'ABox',shacl:'SHACL',rules:'规则',vocabulary:'词表'};

function Capability({children}:{children:React.ReactNode}){return <div className="capability-notice"><strong>当前能力边界</strong><p>{children}</p></div>}
function JsonView({value}:{value:unknown}){return <pre className="document-text mono">{JSON.stringify(value,null,2)}</pre>}
function latestByLayer(revisions:Revision[]){
  return Object.fromEntries(layers.map(layer=>[layer,revisions.find(item=>item.layer===layer)])) as Record<Revision['layer'],Revision|undefined>;
}
function contentLabels(value:Record<string,unknown>):string[]{
  const found:string[]=[];
  for(const item of Object.values(value)){
    if(Array.isArray(item)) for(const entry of item){
      if(typeof entry==='string')found.push(entry);
      else if(entry&&typeof entry==='object'){
        const record=entry as Record<string,unknown>;
        const label=record.label??record.name??record.id??record.iri;
        if(typeof label==='string')found.push(label);
      }
    }
  }
  return found.slice(0,8);
}

export default function OntologyWorkspace({project,sources,jobs,revisions,onSave,onGoData}:{
  project:Project;sources:Source[];jobs:Job[];revisions:Revision[];
  onSave:(layer:Revision['layer'],content:Record<string,unknown>,dependencies:Record<string,string>)=>Promise<Revision>;
  onGoData?:()=>void;
}){
  const [stage,setStage]=useState<(typeof stages)[number][0]>('discovery');
  const [layer,setLayer]=useState<Revision['layer']>('tbox');
  const latest=useMemo(()=>latestByLayer(revisions),[revisions]);
  const selected=latest[layer];
  const [draft,setDraft]=useState('{}'),[message,setMessage]=useState(''),[saving,setSaving]=useState(false);
  useEffect(()=>{setDraft(JSON.stringify(selected?.content??{},null,2));setMessage('')},[layer,selected?.revision_id]);
  const validations=jobs.filter(job=>job.operation==='validate_shacl');
  const semanticRuns=jobs.filter(job=>['extract','build_graph','ontology'].includes(job.operation));
  async function save(){
    setMessage('');let content:Record<string,unknown>;
    try{const parsed:unknown=JSON.parse(draft);if(!parsed||Array.isArray(parsed)||typeof parsed!=='object')throw new Error();content=parsed as Record<string,unknown>}
    catch{setMessage('JSON 必须是一个有效对象。');return}
    setSaving(true);
    try{await onSave(layer,content,{});setMessage('草稿已保存到后端修订记录。')}
    catch{setMessage('保存失败。请刷新项目修订后重试。')}
    finally{setSaving(false)}
  }
  return <section className="ontology-workspace">
    <div className="page-header"><div><div className="eyebrow">ONTOLOGY BUILD / FDE 本体构建</div><h1>从业务问题推进到可验证模型</h1><p>每一步使用当前项目的真实来源、修订和任务结果，保留数据与结论的证据链。</p></div><span className="status-pill">项目修订 {project.workspace_revision}</span></div>
    <nav className="stage-switcher" aria-label="本体构建阶段">{stages.map(([id,no,name,desc])=><button key={id} aria-current={stage===id?'step':undefined} onClick={()=>setStage(id)}><span>{no}</span><strong>{name}</strong><small>{desc}</small></button>)}</nav>

    {stage==='discovery'&&<div className="ontology-section">
      <div className="section-heading"><div><p className="eyebrow">STEP 1</p><h2>场景理解</h2><p>先确认来源覆盖、解析状态和已执行的语义任务，再决定哪些业务事实值得进入模型。</p></div>{onGoData&&<button className="button secondary" onClick={onGoData}>返回数据接入</button>}</div>
      <div className="metric-grid"><article><strong>{sources.length}</strong><span>真实来源快照</span></article><article><strong>{semanticRuns.length}</strong><span>语义任务记录</span></article><article><strong>{revisions.length}</strong><span>模型修订记录</span></article></div>
      <div className="card-grid">{sources.map(source=><article className="workspace-card" key={source.source_id}><span className="status-pill">{source.format.toUpperCase()}</span><h3>{source.format.toUpperCase()} 来源 · {source.source_id.slice(0,8)}</h3><p>{source.size.toLocaleString()} bytes</p><dl className="inspector-dl"><dt>来源修订</dt><dd className="mono">{source.revision}</dd><dt>内容哈希</dt><dd className="mono">{source.sha256}</dd></dl></article>)}</div>
      {!sources.length&&<div className="empty-state"><h2>还没有可建模来源</h2><p>先在数据接入中登记并解析真实文件。</p></div>}
      <Capability>访谈材料与业务事实的持久化接口尚未开放。当前页面仅展示后端已有来源和任务，访谈结论不会被写成已确认事实。</Capability>
    </div>}

    {stage==='questions'&&<div className="ontology-section"><div className="section-heading"><div><p className="eyebrow">STEP 2</p><h2>业务问题</h2><p>把“模型应该回答什么”沉淀成可评审、可回归的能力问题。</p></div></div>
      <Capability>后端目前没有能力问题、访谈结论和验收用例的保存接口。页面暂不生成虚构的问题清单，也不把 rules 层改称为业务问题。</Capability>
      <div className="empty-state"><h2>等待能力问题接口</h2><p>后续需要支持问题描述、业务负责人、证据来源、优先级和验收样例，并与具体模型修订绑定。</p></div>
    </div>}

    {stage==='model'&&<div className="ontology-section"><div className="section-heading"><div><p className="eyebrow">STEP 3</p><h2>模型方案</h2><p>查看项目中已经保存的五类修订，并以 JSON 对后端草稿做最小编辑。</p></div></div>
      <div className="model-layout"><aside className="layer-list">{layers.map(item=>{const rev=latest[item];return <button key={item} className={layer===item?'active':''} aria-pressed={layer===item} onClick={()=>setLayer(item)}><strong>{layerName[item]}</strong><small>{rev?`${rev.state} · ${rev.revision_id.slice(0,8)}`:'尚无修订'}</small></button>})}</aside>
      <div className="detail-panel"><div className="split"><div><h2>{layerName[layer]} 草稿</h2><p className="helper">保存会生成不可变修订，并推进项目 workspace_revision。</p></div>{selected&&<span className="status-pill" data-status={selected.state==='CERTIFIED'?'succeeded':undefined}>{selected.state}</span>}</div>
        {selected&&contentLabels(selected.content).length>0&&<div className="tag-list">{contentLabels(selected.content).map(label=><span key={label}>{label}</span>)}</div>}
        <label htmlFor="layer-json">本体层 JSON</label><textarea id="layer-json" className="json-editor mono" rows={16} value={draft} onChange={event=>setDraft(event.target.value)}/>
        <div className="dialog-actions"><button className="button primary" disabled={saving} onClick={save}>{saving?'保存中…':`保存 ${layerName[layer]} 草稿`}</button></div>{message&&<p className={message.startsWith('草稿')?'notice':'error'} role="status">{message}</p>}
        {selected&&<details><summary>查看当前修订证据</summary><JsonView value={{revision_id:selected.revision_id,sha256:selected.sha256,dependencies:selected.dependencies}}/></details>}
      </div></div>
      <Capability>当前编辑器严格对应已有 layer API。可视化类、关系、属性编辑以及候选批量评审仍需后端结构化命令与审核接口。</Capability>
    </div>}

    {stage==='validation'&&<div className="ontology-section"><div className="section-heading"><div><p className="eyebrow">STEP 4</p><h2>场景验证</h2><p>这里只展示后端已经执行的 SHACL 验证任务及其返回证据。</p></div></div>
      {validations.length?<div className="run-list">{validations.map(job=><article className="workspace-card" key={job.job_id}><div className="split"><h3>SHACL 验证</h3><span className="status-pill" data-status={job.state}>{job.state}</span></div><p className="mono">{job.run_id}</p>{job.error_code&&<p className="error">{job.error_code}</p>}{job.result&&<JsonView value={job.result.data}/>}</article>)}</div>:<div className="empty-state"><h2>还没有 SHACL 验证任务</h2><p>需要通过后端任务接口提交 validate_shacl 后，这里才会出现结果。</p></div>}
      <Capability>业务金标、竞争答案、人工结论与回归套件尚无持久化 API；当前验证结果只代表实际返回的 SHACL 任务证据。</Capability>
    </div>}

    {stage==='delivery'&&<div className="ontology-section"><div className="section-heading"><div><p className="eyebrow">STEP 5</p><h2>交付中心</h2><p>汇总当前项目修订与验证证据，识别进入正式交付前仍需补齐的门禁。</p></div><button className="button primary" disabled>创建发布版本</button></div>
      <div className="delivery-grid">{layers.map(item=>{const rev=latest[item];return <article className="workspace-card" key={item}><h3>{layerName[item]}</h3><strong>{rev?rev.state:'未就绪'}</strong><p className="mono">{rev?.revision_id??'尚无修订'}</p></article>})}<article className="workspace-card"><h3>SHACL 验证</h3><strong>{validations.some(job=>job.state==='succeeded')?'有成功记录':'未就绪'}</strong><p>{validations.length} 条真实任务</p></article></div>
      <Capability>发布与部署 API 尚未开放，认证能力也未暴露为 HTTP 接口。创建发布版本保持禁用，避免把草稿状态表达为已交付。</Capability>
    </div>}
  </section>
}
