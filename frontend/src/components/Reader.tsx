import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Search, FileText, X } from 'lucide-react';
import type { Detail } from '../types';

function Highlight({text, query}: {text: string; query: string}) {
  if (!query.trim()) return <>{text}</>;
  const parts = []; let start = 0;
  const lower = text.toLocaleLowerCase(), needle = query.trim().toLocaleLowerCase();
  let i = lower.indexOf(needle);
  while (i !== -1) {parts.push(text.slice(start, i), <mark key={i}>{text.slice(i, i + needle.length)}</mark>); start = i + needle.length; i = lower.indexOf(needle, start);}
  parts.push(text.slice(start)); return <>{parts}</>;
}

export default function Reader({detail, onBack}: {detail: Detail; onBack: () => void}) {
  const [query, setQuery] = useState('');
  const [expertOnly, setExpertOnly] = useState(false);
  const [active, setActive] = useState<number | null>(null);
  const passageNodes = useRef(new Map<number, HTMLElement>());
  const list = useRef<HTMLDivElement>(null);
  const pending = useRef<number | null>(null);
  function jump(n: number) {
    setQuery(''); setExpertOnly(false); setActive(n); pending.current = n;
    history.replaceState(null, '', `#transcript=${detail.id}&passage=${n}`);
  }
  useEffect(() => {
    const apply = () => {
      const hash = new URLSearchParams(location.hash.slice(1));
      const n = Number(hash.get('passage'));
      if (hash.get('transcript') === detail.id && hash.has('passage') && detail.passages.some(p => p.ordinal === n)) jump(n);
    };
    apply(); window.addEventListener('hashchange', apply);
    return () => window.removeEventListener('hashchange', apply);
  }, [detail.id]);
  useEffect(() => {
    if (pending.current !== null) {passageNodes.current.get(pending.current)?.scrollIntoView({block: 'start', behavior: 'instant'}); pending.current = null;}
  });
  const filtered = detail.passages.filter(p => (!expertOnly || p.is_expert) && (p.text + ' ' + p.speaker).toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  return <section className="reader" aria-label="Transcript reader">
    <div className="reader-heading">
      <button className="button text-button mobile-back" onClick={onBack}><ArrowLeft size={18}/>Transcripts</button>
      <div className="reader-title-row"><div><p className="eyebrow"><span className="source-dot"/>SOURCE INTERVIEW <span className="eyebrow-separator">/</span> {detail.market}</p><h2>{detail.expert}</h2><p className="reader-meta">{detail.role} <span>·</span> {detail.market}</p></div><a className="button source-button" aria-label="Original file" href={`/api/transcripts/${detail.id}/source`} download><FileText size={17}/><span>Original file</span></a></div>
      <div className="reader-tools"><div className="search-input"><Search size={18}/><input aria-label="Search this transcript" placeholder="Search this transcript" value={query} onChange={e => {setQuery(e.target.value); list.current?.scrollTo(0, 0);}}/>{query && <button className="clear-button" aria-label="Clear transcript search" onClick={() => setQuery('')}><X size={16}/></button>}</div>
        <label className="switch-label"><input type="checkbox" checked={expertOnly} onChange={e => {setExpertOnly(e.target.checked); list.current?.scrollTo(0, 0);}}/><span className="switch" aria-hidden="true"/>Expert only</label>
      </div>
      <div className="reader-subtools"><span aria-live="polite">{filtered.length} {filtered.length === 1 ? 'passage' : 'passages'}{query || expertOnly ? ` of ${detail.passages.length}` : ''}</span><label className="jump-label">Jump to <select aria-label="Jump to timestamp" value={active ?? ''} onChange={e => jump(Number(e.target.value))}><option value="" disabled>timestamp</option>{detail.passages.map(p => <option key={p.ordinal} value={p.ordinal}>{p.timestamp} · {p.speaker}</option>)}</select></label></div>
    </div>
    <div ref={list} className="passages" tabIndex={0} aria-label="Transcript passages">
      {filtered.map(p => <article ref={node => {if (node) passageNodes.current.set(p.ordinal, node); else passageNodes.current.delete(p.ordinal);}} key={p.ordinal} id={`passage-${p.ordinal}`} className={'passage' + (p.is_expert ? ' expert-passage' : ' interviewer-passage') + (active === p.ordinal ? ' active-passage' : '')}>
        <button className="timestamp" aria-label={'Go to ' + p.timestamp} onClick={() => jump(p.ordinal)}>{p.timestamp}</button><div><p className="speaker">{p.speaker}{p.is_expert && <span className="expert-label">Expert</span>}</p><p className="passage-text"><Highlight text={p.text} query={query}/></p></div>
      </article>)}
      {!filtered.length && <div className="no-results"><Search size={26} strokeWidth={1.5}/><h3>No matching passages</h3><p>Try a different search or include the interviewer.</p><button className="button text-button" onClick={() => {setQuery(''); setExpertOnly(false);}}>Clear filters</button></div>}
    </div>
    <footer className="reader-footer">Source text preserved <span>·</span> Timestamps from transcript</footer>
  </section>;
}
