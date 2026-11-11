export type Cell = string|number|boolean|null;
export type Column={name:string,type:string,emptyCount:number,examples:string[]};
export type Preview={columns:Column[],rows:Record<string,Cell>[],text?:string,issues:{field:string,message:string,count:number}[],sampleOnly:boolean,total?:number};
const cell=(value:unknown):Cell=>value===undefined||value===null?null:typeof value==='string'||typeof value==='number'||typeof value==='boolean'?value:JSON.stringify(value);
const blank=(value:Cell)=>value===null||typeof value==='string'&&!value.trim();
export function makePreview(data:Record<string,unknown>):Preview{
 const preview:Preview={columns:[],rows:[],issues:[],sampleOnly:false};
 if(typeof data.text==='string'){preview.text=data.text.slice(0,50000);preview.sampleOnly=data.text.length>50000;return preview}
 if(Object.hasOwn(data,'content')&&data.content!==undefined&&(data.content===null||typeof data.content!=='object')){preview.text=JSON.stringify(data.content).slice(0,50000);preview.sampleOnly=JSON.stringify(data.content).length>50000;return preview}
 let raw:unknown[]=[];let names:string[]=[];
 if(Array.isArray(data.headers)&&Array.isArray(data.rows)){names=data.headers.filter((s):s is string=>typeof s==='string');raw=data.rows}
 else if(Array.isArray(data.content))raw=data.content;
 else if(data.content&&typeof data.content==='object')raw=[data.content];
 if(!names.length){names=[...new Set(raw.slice(0,200).flatMap(v=>v&&typeof v==='object'&&!Array.isArray(v)?Object.keys(v):['值']))]}
 preview.rows=raw.slice(0,200).map(row=>Object.fromEntries(names.map((name,i)=>[name,cell(Array.isArray(row)?row[i]:row&&typeof row==='object'?(row as Record<string,unknown>)[name]:row)])));
 preview.total=typeof data.row_count==='number'?data.row_count:raw.length;
 preview.sampleOnly=preview.total>preview.rows.length;
 preview.columns=names.map(name=>{const values=preview.rows.map(row=>row[name]);const nonempty=values.filter(v=>!blank(v));const types=[...new Set(nonempty.map(v=>typeof v))];return{name,type:types.length===1?types[0]:types.length>1?'混合类型':'未知',emptyCount:values.filter(blank).length,examples:[...new Set(nonempty.map(String))].slice(0,4)}});
 for(const field of preview.columns){if(field.emptyCount)preview.issues.push({field:field.name,message:'样本中存在空值',count:field.emptyCount});if(field.type==='混合类型')preview.issues.push({field:field.name,message:'样本中存在不同类型',count:preview.rows.length})}
 return preview;
}
export function sourceJob<T extends{operation:string,state:string,result:{source_refs:string[]}|null}>(id:string,jobs:T[]):T|undefined{return jobs.find(job=>job.operation==='parse'&&job.state==='succeeded'&&job.result?.source_refs.includes('source:'+id))}
