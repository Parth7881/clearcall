import { useEffect, useState } from 'react';
import { request, errorMessage, ephemeral } from '../api';
import type { Transcript } from '../types';

type Evidence = {transcript_id:string; passage_id:number; quote:string; expert:string; timestamp:string};
type Answer = {answer:string; status:string; evidence:Evidence[]; question?:string};
type Job = {id:string; kind:string; status:string; completed:number; total:number; error:string; question:string; result:null | {answers?:Answer[]; answer?:Answer; passages_used?:number; transcripts?:{id:string; expert:string; market:string; answers:Answer[]}[]; themes?:Answer[]; differences?:Answer[]; failures?:{expert:string; error:string}[]}};
type Config = {configured:boolean; model:string; questions:string[]};
const currentJobs = new Map<string,string>();
const active = (job:Job|null) => !!job && ['queued','running'].includes(job.status);

const draftMemory = new Map<string,string>();
function useDraft(name:string) {
  const key = 'clearcall.draft.' + name;
  const [value,setValue] = useState(() => {
    try {if(ephemeral) return draftMemory.get(key) ?? ''; return localStorage.getItem(key) ?? draftMemory.get(key) ?? '';}
    catch {return draftMemory.get(key) ?? '';}
  });
  const [saveError,setSaveError] = useState(false);
  function update(next:string) {
    setValue(next);
    draftMemory.set(key,next);
    try {
      if(ephemeral) return;
      if(next) localStorage.setItem(key,next);
      else localStorage.removeItem(key);
      setSaveError(false);
    } catch {setSaveError(true);}
  }
  return [value,update,saveError] as const;
}


export default function Analysis({transcripts, mode, onSource}:{transcripts:Transcript[]; mode:'analysis'|'ask'; onSource:(id:string, passage:number)=>void}) {
  const [config,setConfig] = useState<Config|null>(null);
  const [selected,setSelected] = useState<string[]>(() => transcripts.slice(0,50).map(t => t.id));
  const [questions,setQuestions,guideSaveError] = useDraft('guide');
  const [question,setQuestion,askSaveError] = useDraft('ask');
  const [job,setJob] = useState<Job|null>(null);
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const [cancelling,setCancelling] = useState(false);
  async function configure() {
    try {const c=await request<Config>('/analysis/config'); setConfig(c);}
    catch(e) {setError(errorMessage(e));}
  }
  useEffect(() => {void configure();},[]);
  useEffect(() => {
    const controller=new AbortController(); setJob(null); setError('');
    request<Job[]>('/analysis/jobs',{signal:controller.signal}).then(async all => {
      if(controller.signal.aborted) return;

      const last=all.find(j=>j.kind===mode && (j.id===currentJobs.get(mode)||active(j)));
      if(last) {const detail=await request<Job>('/analysis/jobs/'+last.id,{signal:controller.signal}); if(!controller.signal.aborted) setJob(detail);}
    }).catch(e=>{if(!controller.signal.aborted) setError(errorMessage(e));});
    return ()=>controller.abort();
  },[mode]);
  useEffect(() => {
    if(!active(job)) return;
    const controller=new AbortController();
    const timer=window.setInterval(()=>{request<Job>('/analysis/jobs/'+job!.id,{signal:controller.signal}).then(j=>{setJob(j); setError('');}).catch(e=>{if(!controller.signal.aborted) setError(errorMessage(e));});},1500);
    return ()=>{clearInterval(timer); controller.abort();};
  },[job?.id,job?.status]);
  async function start() {
    setBusy(true); setError(''); setCancelling(false);
    try {
      const body=mode==='ask'?{transcript_ids:selected,question}:{transcript_ids:selected,questions:questions.split('\n').filter(q=>q.trim())};
      const next=await request<Job>(mode==='ask'?'/analysis/ask':'/analysis/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      currentJobs.set(mode,next.id); setJob(next);
    } catch(e) {setError(errorMessage(e));} finally {setBusy(false);}
  }
  function answer(a:Answer, key:string|number) {return <article className="analysis-answer" key={key}>
    {a.question && <h3>{a.question}</h3>}<p>{a.answer}</p>
    {a.evidence.length>0 && <details className="answer-sources"><summary>Sources ({a.evidence.length})</summary>{a.evidence.filter((e,i,all)=>all.findIndex(x=>x.transcript_id===e.transcript_id&&x.passage_id===e.passage_id&&x.quote===e.quote)===i).map((e,i)=><blockquote key={i}><p>{e.quote}</p><button className="button text-button" onClick={()=>onSource(e.transcript_id,e.passage_id)}>{e.expert} · {e.timestamp}</button></blockquote>)}</details>}
  </article>;}
  return <section className="analysis-panel" id="workspace" tabIndex={-1} aria-label={mode==='ask'?'Ask interviews':'Interview analysis'}>
    <div className="analysis-controls">
      <h2>{mode==='ask'?'Ask':'Guide answers'}</h2>
      {config && !config.configured && <div className="config-note"><p>{ephemeral?'AI is temporarily unavailable. Please try again later.':'Add GROQ_API_KEY to your local .env file to enable Groq.'}</p><button className="button secondary" onClick={configure}>Check configuration</button></div>}
      <details className="source-picker"><summary>{selected.length} interviews selected</summary><button className="button text-button" disabled={active(job)} onClick={()=>setSelected(selected.length?[]:transcripts.slice(0,50).map(t=>t.id))}>{selected.length?'Clear selection':'Select first 50'}</button>
        {transcripts.map(t=><label key={t.id}><input type="checkbox" checked={selected.includes(t.id)} disabled={active(job)||(!selected.includes(t.id)&&selected.length>=50)} onChange={e=>setSelected(s=>e.target.checked?[...s,t.id]:s.filter(id=>id!==t.id))}/><span>{t.expert}<small>{t.market}</small></span></label>)}
      </details>
      <p className="analysis-note">{mode==='ask'?'Ask one question across the selected interviews.':'Get one answer per question, comparing the selected experts.'}</p>
      {mode==='ask'?<label className="analysis-field">Your question<textarea rows={4} maxLength={2000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Type your question"/></label>:<><label className="analysis-field">Your questions<textarea rows={7} value={questions} onChange={e=>setQuestions(e.target.value)} placeholder="One question per line (up to 12)"/></label></>}
      {(mode==='ask'?question:questions) && <button className="button text-button" onClick={()=>mode==='ask'?setQuestion(''):setQuestions('')}>Clear draft</button>}
      {(mode==='ask'?askSaveError:guideSaveError) && <p role="alert">Draft could not be saved in this browser. Copy it before closing or refreshing the page.</p>}
      <p className="analysis-note">Selected interview text is sent to Groq. Provider usage charges may apply.</p>
      <button className="button primary" disabled={!config?.configured||!selected.length||active(job)||busy||(mode==='ask'?!question.trim():!questions.trim())} onClick={start}>{busy?'Starting…':mode==='ask'?'Get answer':'Get answers'}</button>
    </div>
    <div className="analysis-results">
      {error && <p role="alert" className="error-banner">{error}</p>}
      {!job && <p>Select interviews and {mode==='ask'?'ask a question.':'run analysis.'}</p>}
      {job && <><div className="job-status" role="status"><span>{job.status} · {job.completed}/{job.total} interviews</span>{active(job)&&<button className="button secondary" disabled={cancelling} onClick={async()=>{try{await request('/analysis/jobs/'+job.id+'/cancel',{method:'POST'});setCancelling(true);}catch(e){setError(errorMessage(e));}}}>{cancelling?'Cancelling…':'Cancel'}</button>}</div>
        {active(job)&&<progress value={job.completed} max={job.total} aria-label="Analysis progress"/>}
        {job.error&&<p role="alert">{job.error}</p>}
        {job.result?.answer && <><p className="analysis-note">Based on {job.result.passages_used} retrieved passages. Review the source quotes.</p>{answer(job.result.answer,'answer')}</>}
        {job.result?.answers?.map((a,i)=>answer(a,i))}
        {job.result?.transcripts && !job.result.answers?.length && !active(job) && <p>Combined answers are unavailable. Your source analysis is cached; try again to finish.</p>}
        {job.result?.failures?.map((f,i)=><p key={i}>{f.expert}: {f.error}</p>)}
      </>}
    </div>
  </section>;
}
