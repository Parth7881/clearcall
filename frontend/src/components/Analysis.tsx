import { useEffect, useState } from 'react';
import { request, errorMessage } from '../api';
import type { Transcript } from '../types';

type Evidence = {transcript_id:string; passage_id:number; quote:string; expert:string; timestamp:string};
type Answer = {answer:string; status:string; evidence:Evidence[]; question?:string};
type Job = {id:string; kind:string; status:string; completed:number; total:number; error:string; question:string; result:null | {answer?:Answer; passages_used?:number; transcripts?:{id:string; expert:string; market:string; answers:Answer[]}[]; themes?:Answer[]; differences?:Answer[]; failures?:{expert:string; error:string}[]}};
type Config = {configured:boolean; model:string; questions:string[]};
const active = (job:Job|null) => !!job && ['queued','running'].includes(job.status);

export default function Analysis({transcripts, mode, onSource}:{transcripts:Transcript[]; mode:'analysis'|'ask'; onSource:(id:string, passage:number)=>void}) {
  const [config,setConfig] = useState<Config|null>(null);
  const [selected,setSelected] = useState<string[]>(() => transcripts.slice(0,50).map(t => t.id));
  const [questions,setQuestions] = useState('');
  const [question,setQuestion] = useState('');
  const [job,setJob] = useState<Job|null>(null);
  const [history,setHistory] = useState<Job[]>([]);
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const [cancelling,setCancelling] = useState(false);
  async function configure() {
    try {const c=await request<Config>('/analysis/config'); setConfig(c); setQuestions(q=>q||c.questions.join('\n'));}
    catch(e) {setError(errorMessage(e));}
  }
  useEffect(() => {void configure();},[]);
  useEffect(() => {
    const controller=new AbortController(); setJob(null); setError('');
    request<Job[]>('/analysis/jobs',{signal:controller.signal}).then(async all => {
      if(controller.signal.aborted) return;
      setHistory(all);
      const last=all.find(j=>j.kind===mode);
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
      setJob(next); setHistory(h=>[next,...h]);
    } catch(e) {setError(errorMessage(e));} finally {setBusy(false);}
  }
  function answer(a:Answer, key:string|number) {return <article className="analysis-answer" key={key}>
    {a.question && <h3>{a.question}</h3>}<p>{a.answer}</p>
    {a.evidence.map((e,i)=><blockquote key={i}><p>{e.quote}</p><button className="button text-button" onClick={()=>onSource(e.transcript_id,e.passage_id)}>{e.expert} · {e.timestamp}</button></blockquote>)}
  </article>;}
  return <section className="analysis-panel" id="workspace" tabIndex={-1} aria-label={mode==='ask'?'Ask interviews':'Interview analysis'}>
    <div className="analysis-controls">
      <h2>{mode==='ask'?'Ask interviews':'Analysis'}</h2>
      {config && !config.configured && <div className="config-note"><p>Add GEMINI_API_KEY to your local .env file to enable Gemini.</p><button className="button secondary" onClick={configure}>Check configuration</button></div>}
      <details className="source-picker"><summary>{selected.length} interviews selected</summary><button className="button text-button" disabled={active(job)} onClick={()=>setSelected(selected.length?[]:transcripts.slice(0,50).map(t=>t.id))}>{selected.length?'Clear selection':'Select first 50'}</button>
        {transcripts.map(t=><label key={t.id}><input type="checkbox" checked={selected.includes(t.id)} disabled={active(job)||(!selected.includes(t.id)&&selected.length>=50)} onChange={e=>setSelected(s=>e.target.checked?[...s,t.id]:s.filter(id=>id!==t.id))}/><span>{t.expert}<small>{t.market}</small></span></label>)}
      </details>
      {mode==='ask'?<label className="analysis-field">Question<textarea rows={3} maxLength={2000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="What limits adoption across these interviews?"/></label>:<details><summary>Analysis questions</summary><label className="analysis-field">One question per line (up to 12)<textarea rows={9} value={questions} onChange={e=>setQuestions(e.target.value)}/></label></details>}
      <p className="analysis-note">Selected interview text is sent to Gemini. Provider usage charges may apply.</p>
      <button className="button primary" disabled={!config?.configured||!selected.length||active(job)||busy||(mode==='ask'?!question.trim():!questions.trim())} onClick={start}>{busy?'Starting…':mode==='ask'?'Ask':'Run analysis'}</button>
      {history.filter(j=>j.kind===mode).length>0 && <label className="analysis-field">Saved runs<select value={job?.id||''} disabled={active(job)||busy} onChange={async e=>{try{setJob(await request<Job>('/analysis/jobs/'+e.target.value));}catch(err){setError(errorMessage(err));}}}><option value="" disabled>Select a run</option>{history.filter(j=>j.kind===mode).map((j,i)=><option key={j.id} value={j.id}>Run {history.filter(j=>j.kind===mode).length-i} · {j.total} interviews{j.question?' · '+j.question.slice(0,40):''}</option>)}</select></label>}
    </div>
    <div className="analysis-results">
      {error && <p role="alert" className="error-banner">{error}</p>}
      {!job && <p>Select interviews and {mode==='ask'?'ask a question.':'run analysis.'}</p>}
      {job && <><div className="job-status" role="status"><span>{job.status} · {job.completed}/{job.total} interviews</span>{active(job)&&<button className="button secondary" disabled={cancelling} onClick={async()=>{try{await request('/analysis/jobs/'+job.id+'/cancel',{method:'POST'});setCancelling(true);}catch(e){setError(errorMessage(e));}}}>{cancelling?'Cancelling…':'Cancel'}</button>}</div>
        {active(job)&&<progress value={job.completed} max={job.total} aria-label="Analysis progress"/>}
        {job.error&&<p role="alert">{job.error}</p>}
        {job.result?.answer && <><p className="analysis-note">Based on {job.result.passages_used} retrieved passages. Review the source quotes.</p>{answer(job.result.answer,'answer')}</>}
        {!!job.result?.themes?.length&&<><h2>Common themes</h2>{job.result.themes.map((a,i)=>answer(a,'t'+i))}</>}
        {!!job.result?.differences?.length&&<><h2>Differences</h2>{job.result.differences.map((a,i)=>answer(a,'d'+i))}</>}
        {job.result?.transcripts?.map(t=><details className="expert-analysis" key={t.id}><summary>{t.expert} · {t.market}</summary>{t.answers.map((a,i)=>answer(a,i))}</details>)}
        {job.result?.failures?.map((f,i)=><p key={i}>{f.expert}: {f.error}</p>)}
      </>}
    </div>
  </section>;
}
