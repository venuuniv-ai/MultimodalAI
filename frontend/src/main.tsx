import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUp, BookOpen, Check, ChevronRight, Database, FileText, FlaskConical, Layers, LoaderCircle, Plus, ShieldCheck, Trash2, Upload } from 'lucide-react';
import './style.css';
import { EvaluationDashboard } from './EvaluationDashboard';

type Doc = {id:string;name:string;kind:string;chunks:number};
type Source = {evidence_text?:string;id:string;name:string;page:number;text:string;score:number};
type Result = {answer:string;sources:Source[];trace:{step:string;detail:string}[];mode:string;latency_ms:number;warning?:string;citation_check?:{valid:boolean;note:string}|null};
type Health = {status:string;documents:number;ocr_available:boolean;models:string[]};
async function api<T>(url:string, init?:RequestInit):Promise<T>{
  const response = await fetch('/api'+url,init);
  const body = await response.json();
  if(!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
  return body;
}
function App(){
  const [docs,setDocs]=useState<Doc[]>([]),[health,setHealth]=useState<Health|null>(null),[error,setError]=useState('');
  const [question,setQuestion]=useState(''),[busy,setBusy]=useState(false),[mode,setMode]=useState('extractive'),[model,setModel]=useState('');
  const [docId,setDocId]=useState(''),[operation,setOperation]=useState(''),[column,setColumn]=useState('revenue');
  const [result,setResult]=useState<Result|null>(null),[asked,setAsked]=useState(''),[tab,setTab]=useState('sources');
  const [view,setView]=useState('research'),[numericColumns,setNumericColumns]=useState<string[]>([]);
  const input=useRef<HTMLInputElement>(null);
  async function refresh(){const [d,h]=await Promise.all([api<Doc[]>('/documents'),api<Health>('/health')]);setDocs(d);setHealth(h);setModel(m=>m||h.models[0]||'');}
  useEffect(()=>{refresh().catch(e=>setError(e.message));},[]);
  useEffect(()=>{let live=true;setNumericColumns([]);if(docs.find(d=>d.id===docId)?.kind==='csv')api<{numeric_columns:string[]}>('/documents/'+docId+'/columns').then(data=>{if(live){setNumericColumns(data.numeric_columns);setColumn(data.numeric_columns[0]||'');}}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[docId,docs]);
  async function action(work:()=>Promise<unknown>){setBusy(true);setError('');try{await work();}catch(e){setError((e as Error).message);}finally{await refresh().catch(e=>setError(e.message));setBusy(false);}}
  async function upload(files:FileList|null){if(!files)return;await action(async()=>{for(const file of Array.from(files)){const data=new FormData();data.append('file',file);await api('/documents',{method:'POST',body:data});}});if(input.current)input.current.value='';}
  async function ask(e:React.FormEvent){e.preventDefault();if(!question.trim())return;setBusy(true);setError('');setResult(null);setAsked(question);try{setResult(await api<Result>('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,mode,model,document_id:docId||null,operation:operation||null,column:operation==='summary'?column:null})}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  function exportAnswer(){if(!result)return;const body='# '+asked+'\n\n'+result.answer+'\n\n'+result.sources.map((s,i)=>`## S${i+1}: ${s.name} (page/row ${s.page})\n\n${s.evidence_text||s.text}`).join('\n\n')+'\n\nReference validation checks IDs, not semantic faithfulness.\n';const url=URL.createObjectURL(new Blob([body],{type:'text/markdown'}));const a=document.createElement('a');a.href=url;a.download='research-answer.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  const examples=['How does the retrieval engine work?','When is the weekly research review?','How are citations validated?'];
  return <div className="shell">
    <aside className="sidebar"><a className="brand" href="/"><span className="brand-icon"><Layers size={21}/></span><span>Research Desk<small>LOCAL WORKSPACE</small></span></a>
      <div className="workspace"><span className="avatar">VM</span><div>My research workspace<small>Personal · Local storage</small></div><ChevronRight size={16}/></div>
      <div className="section-label">WORKSPACE</div><button className={"nav "+(view==='research'?'active':'')} onClick={()=>setView('research')}><BookOpen size={18}/> Ask your documents <span>{docs.length}</span></button><button className={"nav "+(view==='evaluations'?'active':'')} onClick={()=>setView('evaluations')}><FlaskConical size={18}/> Evaluation results</button>
      <div className="section-label documents-label">SOURCE LIBRARY <button title="Upload documents" onClick={()=>input.current?.click()} disabled={busy}><Plus size={17}/></button></div>
      <input ref={input} type="file" multiple accept=".txt,.md,.pdf,.csv,.png,.jpg,.jpeg" hidden onChange={e=>upload(e.target.files)}/>
      <div className="doc-list">{docs.map(doc=><div className="doc" key={doc.id}><FileText size={17}/><div title={doc.name}>{doc.name}<small>{doc.kind.toUpperCase()} · {doc.chunks} chunks</small></div><button aria-label={'Delete '+doc.name} disabled={busy} onClick={()=>action(async()=>{await api('/documents/'+doc.id,{method:'DELETE'});if(docId===doc.id)setDocId('');})}><Trash2 size={14}/></button></div>)}{!docs.length&&<p className="muted empty-library">Your sources will appear here.</p>}</div>
      <button className="upload-button" disabled={busy} onClick={()=>input.current?.click()}><Upload size={16}/> Upload documents</button>
      <div className="sidebar-bottom"><ShieldCheck size={18}/><div>Private by default<small>Documents stay on this computer</small></div></div>
    </aside>
    <main><header><div><span className="breadcrumb">Workspace</span><ChevronRight size={13}/><strong>{view==='research'?'Document research':'Evaluation results'}</strong></div><span className="status"><i/> {health?'Local backend connected':'Connecting…'}</span></header>
      {view==='evaluations'&&<EvaluationDashboard/>}<div className="content" hidden={view!=='research'}><div className="eyebrow"><span/> YOUR KNOWLEDGE, CONNECTED</div><h1>A little clarity.<br/><span>A lot less searching.</span></h1><p className="intro">Turn your documents into answers you can trace.<br/>Search, explore, and reason with your own sources.</p>
      <div className="metrics"><div><FileText size={17}/><strong>{docs.length}</strong> documents</div><div><Database size={17}/><strong>{docs.reduce((n,d)=>n+d.chunks,0)}</strong> indexed chunks</div><div><ShieldCheck size={17}/> Runs locally</div></div>
      {!docs.length&&<div className="demo-card"><span className="demo-icon"><FlaskConical size={23}/></span><div><strong>Start with a small discovery</strong><p>Explore the platform guide, team notes, and a sample sales dataset.</p></div><button disabled={busy} onClick={()=>action(()=>api('/demo',{method:'POST'}))}>Load demo sources <ChevronRight size={15}/></button></div>}
      <form onSubmit={ask} className="question-card"><div className="card-label"><span><span className="spark">✦</span> Ask your library</span><span className="mode-label">{operation?'CSV analysis':mode==='extractive'?'Source excerpts':'Local AI'}</span></div><textarea aria-label="Question" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="What would you like to understand?" maxLength={2000} onKeyDown={e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&!busy&&docs.length){e.preventDefault();e.currentTarget.form?.requestSubmit();}}}/>
        <div className="controls"><select aria-label="Answer mode" value={mode} onChange={e=>setMode(e.target.value)}><option value="extractive">Extractive · no model needed</option><option value="ollama" disabled={!health?.models.length}>Ollama · local AI</option></select>{mode==='ollama'&&<select aria-label="Local model" value={model} onChange={e=>setModel(e.target.value)}>{health?.models.map(m=><option key={m}>{m}</option>)}</select>}<select aria-label="Source document" value={docId} onChange={e=>{setDocId(e.target.value);setOperation('');}}><option value="">All sources</option>{docs.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select><button className="submit" aria-label="Ask question" disabled={busy||!question.trim()||!docs.length}>{busy?<LoaderCircle className="spin" size={19}/>:<ArrowUp size={20}/>}</button></div>
        {docs.find(d=>d.id===docId)?.kind==='csv'&&<div className="tool-controls"><select aria-label="CSV operation" value={operation} onChange={e=>setOperation(e.target.value)}><option value="">Search CSV rows</option><option value="count">Count rows</option><option value="summary">Summarize numeric column</option></select>{operation==='summary'&&<select aria-label="Column name" value={column} onChange={e=>setColumn(e.target.value)}><option value="" disabled>Choose numeric column</option>{numericColumns.map(c=><option key={c}>{c}</option>)}</select>}</div>}
      </form><div className="availability">{health?.models.length?'Local AI ready':'Source excerpts ready · start Ollama to enable local AI'} · {health?.ocr_available?'Image OCR ready':'Image OCR needs Tesseract'}<button disabled={busy} onClick={()=>refresh().catch(e=>setError(e.message))}>Refresh connection</button></div><div className="suggestions"><span>TRY ASKING</span>{examples.map(q=><button key={q} disabled={busy} onClick={()=>{setQuestion(q);setOperation('');}}>{q}<ChevronRight size={13}/></button>)}</div>
      {error&&<div role="alert" className="error">{error}</div>}
      {busy&&<div role="status" className="working"><LoaderCircle className="spin" size={16}/> Working with your local sources…</div>}
      {result&&<section className="result"><div className="result-heading"><span className="spark">✦</span><div><strong>{asked}</strong><small>{result.mode==='extractive'?'Source excerpts':result.mode==='tool'?'CSV tool result':result.mode==='clarification'?'Clarification needed':'Local model answer'} · {result.latency_ms} ms</small></div>{result.citation_check?.valid&&<span className="citation-badge"><Check size={13}/> References checked</span>}</div>{result.warning&&<p className="warning">{result.warning}</p>}<div className="answer">{result.answer}</div>
        <div className="tabs"><button className={tab==='sources'?'selected':''} onClick={()=>setTab('sources')}>Sources <span>{result.sources.length}</span></button><button className={tab==='trace'?'selected':''} onClick={()=>setTab('trace')}>Workflow trace</button><button className="export-button" onClick={exportAnswer}>Export answer</button></div>
        {tab==='sources'?<div className="sources">{result.sources.map((s,i)=><details key={s.id}><summary><span className="source-number">S{i+1}</span><strong>{s.name}</strong><span>Page / row {s.page}</span><ChevronRight size={15}/></summary><div className="source-body">{s.evidence_text&&<div className="focused-evidence"><strong>Evidence used for this answer</strong><p>{s.evidence_text}</p></div>}<p>{s.text}</p></div></details>)}{!result.sources.length&&<p className="muted">No document citations for this result.</p>}</div>:<div className="trace">{result.trace.map((t,i)=><div key={i}><span>{i+1}</span><p><strong>{t.step}</strong>{t.detail}</p></div>)}</div>}
        {result.citation_check&&<p className="footnote">{result.citation_check.note}</p>}</section>}
      <footer><span>Built for curiosity. Grounded in your sources.</span><span>TXT · PDF · CSV · Images with OCR</span></footer>
      </div></main></div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
