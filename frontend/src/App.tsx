import { useEffect, useState } from 'react';
import { CircleHelp, Plus, Search, FileText, LoaderCircle, X, ArrowLeft, RefreshCw } from 'lucide-react';
import { request, errorMessage } from './api';
import type { Detail, ImportResult, Transcript } from './types';
import Dialog from './components/Dialog';
import Upload from './components/Upload';
import Reader from './components/Reader';

function savedSelection() {
  const hash = new URLSearchParams(location.hash.slice(1)).get('transcript');
  try {return hash || localStorage.getItem('clearcall.selection') || '';} catch {return hash || '';}
}

export default function App() {
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [selected, setSelected] = useState(savedSelection);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detailError, setDetailError] = useState('');
  const [retry, setRetry] = useState(0);
  const [notice, setNotice] = useState('');
  const [dialog, setDialog] = useState<'upload' | 'help' | null>(null);
  const [mobileReader, setMobileReader] = useState(() => location.hash.includes('transcript='));

  async function refresh(signal?: AbortSignal) {
    setError('');
    const rows = await request<Transcript[]>('/transcripts', {signal});
    setTranscripts(rows);
    setSelected(current => rows.some(r => r.id === current) ? current : (rows[0]?.id || ''));
  }
  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal).catch(e => {if (!controller.signal.aborted) setError(errorMessage(e));}).finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController(); setDetail(null); setDetailError('');
    try {localStorage.setItem('clearcall.selection', selected);} catch { /* Storage may be disabled. */ }
    request<Detail>('/transcripts/' + selected, {signal: controller.signal}).then(d => {if (!controller.signal.aborted) setDetail(d);}).catch(e => {if (!controller.signal.aborted) setDetailError(errorMessage(e));});
    return () => controller.abort();
  }, [selected, retry]);
  useEffect(() => {
    const onHash = () => {const id = new URLSearchParams(location.hash.slice(1)).get('transcript'); if (id && transcripts.some(t => t.id === id)) {setSelected(id); setMobileReader(true);}};
    window.addEventListener('hashchange', onHash); return () => window.removeEventListener('hashchange', onHash);
  }, [transcripts]);
  async function imported(result: ImportResult) {
    setDialog(null);
    setNotice(`${result.added} ${result.added === 1 ? 'transcript' : 'transcripts'} added.${result.duplicates ? ` ${result.duplicates} already in your workspace.` : ''}`);
    try {await refresh();} catch (e) {setError(errorMessage(e));}
  }
  function select(id: string) {setSelected(id); setMobileReader(true); history.replaceState(null, '', '#transcript=' + id);}
  const filtered = transcripts.filter(t => `${t.expert} ${t.role} ${t.market}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  return <>
    <a href="#workspace" className="skip-link">Skip to workspace</a>
    <header className="app-header"><div className="brand"><FileText size={25} strokeWidth={1.7}/>Clearcall</div><button className="icon-button" aria-label="Help" onClick={() => setDialog('help')}><CircleHelp size={21}/></button></header>
    <main className={mobileReader && selected ? 'reading-mode' : ''}>
      <div className="study-header"><h1>European Robotic Surgery Market</h1><button className="button primary" onClick={() => setDialog('upload')}><Plus size={19}/>Upload transcripts</button></div>
      {notice && <div className="notice" role="status"><span>{notice}</span><button className="icon-button" aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={18}/></button></div>}
      {error && <div className="error-banner" role="alert"><span>{error}</span><button className="button text-button" onClick={() => {setLoading(true); refresh().catch(e => setError(errorMessage(e))).finally(() => setLoading(false));}}><RefreshCw size={16}/>Retry</button></div>}
      <div id="workspace" tabIndex={-1} className={'workspace' + (mobileReader && selected ? ' showing-reader' : '')}>
        <aside className="library" aria-label="Transcript library"><div className="library-heading"><h2>Transcripts</h2><div className="search-input"><Search size={18}/><input aria-label="Find an expert or market" placeholder="Find an expert or market" value={query} onChange={e => setQuery(e.target.value)}/>{query && <button className="clear-button" aria-label="Clear library search" onClick={() => setQuery('')}><X size={16}/></button>}</div></div>
          <div className="transcript-list">{loading ? <div className="loading-state" role="status"><LoaderCircle className="spin" size={22}/>Loading transcripts…</div> : filtered.map((t) => <button key={t.id} className={'transcript-card' + (selected === t.id ? ' selected' : '')} aria-pressed={selected === t.id} onClick={() => select(t.id)}><span className="card-text"><strong>{t.expert}</strong><span>{t.role}</span><small>{t.market}</small></span></button>)}
          {!loading && !filtered.length && <div className="library-empty"><p>{query ? 'No matching transcripts.' : 'No transcripts yet.'}</p>{query && <button className="button text-button" onClick={() => setQuery('')}>Clear search</button>}</div>}</div>
        </aside>
        {selected ? detail && detail.id === selected ? <Reader key={detail.id} detail={detail} onBack={() => setMobileReader(false)}/> : <section className="reader reader-status"><button className="button text-button mobile-back" onClick={() => setMobileReader(false)}><ArrowLeft size={18}/>Transcripts</button>{detailError ? <div className="no-results" role="alert"><p>{detailError}</p><button className="button secondary" onClick={() => setRetry(n => n + 1)}>Try again</button></div> : <div className="loading-state" role="status"><LoaderCircle size={24} className="spin"/>Opening transcript…</div>}</section> : <section className="empty-reader"><FileText size={32} strokeWidth={1.4}/><h2>No transcript selected</h2><button className="button secondary" onClick={() => setDialog('upload')}>Upload transcripts</button></section>}
      </div>
    </main>
    {dialog === 'upload' && <Upload onClose={() => setDialog(null)} onSuccess={imported}/>}
    {dialog === 'help' && <Dialog title="Transcript help" onClose={() => setDialog(null)}><div className="help-content"><p>Upload UTF-8 .txt files, up to 2 MB each. Include Expert, Role and Market headers, then a timestamp and speaker for each passage.</p><p>Search within an interview or select a timestamp to jump to a passage. Use “Original file” to download the transcript.</p></div><div className="dialog-footer"><button className="button primary" onClick={() => setDialog(null)}>Close</button></div></Dialog>}

  </>;
}
