import { useEffect, useRef, useState } from 'react';
import { CircleHelp, Plus, Search, LockKeyhole, FileText, LoaderCircle, X, ArrowLeft, RefreshCw } from 'lucide-react';
import { request, errorMessage } from './api';
import type { Detail, ImportResult, Transcript } from './types';
import Dialog from './components/Dialog';
import Upload from './components/Upload';
import Reader from './components/Reader';

function savedSelection() {
  const hash = new URLSearchParams(location.hash.slice(1)).get('transcript');
  try {return hash || localStorage.getItem('clearcall.selection') || '';} catch {return hash || '';}
}
function initials(name: string) {return name.replace(/^(Dr\.?|Prof\.?)\s+/i, '').split(/\s+/).map(w => w[0]).filter(Boolean).slice(0, 2).join('');}

export default function App() {
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [selected, setSelected] = useState(savedSelection);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detailError, setDetailError] = useState('');
  const [retry, setRetry] = useState(0);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [dialog, setDialog] = useState<'upload' | 'help' | null>(null);
  const [mobileReader, setMobileReader] = useState(() => location.hash.includes('transcript='));
  const importLock = useRef(false);

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
  async function samples() {
    if (importLock.current) return;
    importLock.current = true; setBusy(true); setError('');
    try {await imported(await request<ImportResult>('/samples', {method: 'POST'}));}
    catch (e) {setError(errorMessage(e));}
    finally {importLock.current = false; setBusy(false);}
  }
  function select(id: string) {setSelected(id); setMobileReader(true); history.replaceState(null, '', '#transcript=' + id);}
  const filtered = transcripts.filter(t => `${t.expert} ${t.role} ${t.market}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const markets = [...new Set(transcripts.map(t => t.market))];
  return <>
    <a href="#workspace" className="skip-link">Skip to workspace</a>
    <header className="app-header"><div className="brand"><span className="brand-mark" aria-hidden="true"><i/><i/><i/><i/></span>clearcall<span className="brand-divider"/><span className="brand-context">Research workspace</span></div><div className="header-right"><span className="header-local"><LockKeyhole size={14}/>Stored on your device</span><button className="icon-button" aria-label="Help" onClick={() => setDialog('help')}><CircleHelp size={21}/></button></div></header>
    <main className={mobileReader && selected ? 'reading-mode' : ''}>
      <div className="intro"><div><p className="intro-kicker"><span/>THE RESEARCH LIBRARY</p><h1>Every conversation.<br className="small-break"/> <span>A clearer perspective.</span></h1><p>Explore your interviews. Stay close to the source.</p></div><div className="intro-actions"><button className="button secondary" disabled={busy || loading} onClick={samples}>{busy && <LoaderCircle size={17} className="spin"/>}{busy ? 'Loading samples…' : 'Load sample project'}</button><button className="button primary" disabled={busy} onClick={() => setDialog('upload')}><Plus size={19}/>Upload transcripts</button></div></div>
      {notice && <div className="notice" role="status"><span>{notice}</span><button className="icon-button" aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={18}/></button></div>}
      {error && <div className="error-banner" role="alert"><span>{error}</span><button className="button text-button" onClick={() => {setLoading(true); refresh().catch(e => setError(errorMessage(e))).finally(() => setLoading(false));}}><RefreshCw size={16}/>Retry</button></div>}
      <div className="project-summary"><div className="study-title"><span className="study-icon"><FileText size={20}/></span><div><span className="study-eyebrow">CURRENT STUDY</span><h2>European Robotic Surgery Market</h2></div></div><div className="study-sources"><span className="source-count">{transcripts.length} {transcripts.length === 1 ? 'transcript' : 'transcripts'}</span><div className="market-list">{markets.length ? markets.map((market, i) => <span className={'market-tag market-' + i % 3} key={market}><i/>{market}</span>) : <span className="muted">Your source interviews will appear here</span>}</div></div></div>
      <div id="workspace" tabIndex={-1} className={'workspace' + (mobileReader && selected ? ' showing-reader' : '')}>
        <aside className="library" aria-label="Transcript library"><div className="library-heading"><h2>Transcripts <span>{transcripts.length}</span></h2><div className="search-input"><Search size={18}/><input aria-label="Find an expert or market" placeholder="Find an expert or market" value={query} onChange={e => setQuery(e.target.value)}/>{query && <button className="clear-button" aria-label="Clear library search" onClick={() => setQuery('')}><X size={16}/></button>}</div></div>
          <div className="transcript-list">{loading ? <div className="loading-state" role="status"><LoaderCircle className="spin" size={22}/>Loading transcripts…</div> : filtered.map((t) => <button key={t.id} className={'transcript-card' + (selected === t.id ? ' selected' : '')} aria-pressed={selected === t.id} onClick={() => select(t.id)}><span className={'avatar color-' + (transcripts.indexOf(t) % 3)}>{initials(t.expert)}</span><span className="card-text"><strong>{t.expert}</strong><span>{t.role}</span><small>{t.market}</small></span></button>)}
          {!loading && !filtered.length && <div className="library-empty"><p>{query ? 'No matching transcripts.' : 'No transcripts yet.'}</p>{query && <button className="button text-button" onClick={() => setQuery('')}>Clear search</button>}</div>}</div><p className="privacy-note"><LockKeyhole size={14}/>Your files stay on this device.</p>
        </aside>
        {selected ? detail && detail.id === selected ? <Reader key={detail.id} detail={detail} onBack={() => setMobileReader(false)}/> : <section className="reader reader-status"><button className="button text-button mobile-back" onClick={() => setMobileReader(false)}><ArrowLeft size={18}/>Transcripts</button>{detailError ? <div className="no-results" role="alert"><p>{detailError}</p><button className="button secondary" onClick={() => setRetry(n => n + 1)}>Try again</button></div> : <div className="loading-state" role="status"><LoaderCircle size={24} className="spin"/>Opening transcript…</div>}</section> : <section className="empty-reader"><span className="empty-icon"><FileText size={30} strokeWidth={1.5}/></span><h2>A clear view of every conversation</h2><p>Bring your interviews together.<br/>Read the original words, one timestamp at a time.</p><button className="button secondary" disabled={busy || loading} onClick={samples}>Explore sample transcripts</button><small>3 interviews on the European robotic surgery market</small></section>}
      </div>
    </main>
    {dialog === 'upload' && <Upload onClose={() => setDialog(null)} onSuccess={imported}/>}
    {dialog === 'help' && <Dialog title="About this workspace" onClose={() => setDialog(null)}><div className="help-content"><p>Clearcall brings your expert interviews into one place, with original wording and timestamps intact.</p><h3>Get started</h3><p>Load the three supplied interviews or upload your own UTF-8 .txt transcripts. Choose an expert, search their words, or use “Jump to” to find a timestamp.</p><h3>Your sources stay local</h3><p>Files are saved in this app’s local database. No AI service is called in Part 1. “Original file” downloads exactly what you uploaded.</p><p className="muted">Timestamps mark the start of each passage. The files do not include audio.</p></div><div className="dialog-footer"><button className="button primary" onClick={() => setDialog(null)}>Got it</button></div></Dialog>}
  </>;
}
