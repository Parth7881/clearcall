import { useRef, useState } from 'react';
import { FileText, Upload as UploadIcon, X, LoaderCircle } from 'lucide-react';
import Dialog from './Dialog';
import { request, errorMessage } from '../api';
import type { ImportResult } from '../types';

export default function Upload({onClose, onSuccess}: {onClose: () => void; onSuccess: (result: ImportResult) => void}) {
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  function choose(selected: File[]) {
    const next = [...files];
    for (const file of selected) if (!next.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) next.push(file);
    if (next.length > 5) {setError('Choose up to five files per upload.'); return;}
    if (next.some(f => !f.name.toLowerCase().endsWith('.txt') || f.size > 2 * 1024 * 1024)) {setError('Choose .txt files, each 2 MB or smaller.'); return;}
    setFiles(next); setError('');
  }
  async function submit() {
    if (busy || !files.length) return;
    setBusy(true); setError('');
    const data = new FormData(); files.forEach(f => data.append('files', f));
    try {onSuccess(await request<ImportResult>('/transcripts', {method: 'POST', body: data}));}
    catch (e) {setError(errorMessage(e)); setBusy(false);}
  }
  return <Dialog title="Upload transcripts" onClose={onClose} busy={busy}>
    <p className="dialog-intro">Add your interview transcripts to this workspace.</p>
    <div className={'drop-zone' + (dragging ? ' dragging' : '')} onDragOver={e => {e.preventDefault(); if (!busy) setDragging(true);}} onDragLeave={() => setDragging(false)} onDrop={e => {e.preventDefault(); setDragging(false); if (!busy) choose(Array.from(e.dataTransfer.files));}}>
      <UploadIcon size={28} strokeWidth={1.5}/><strong>Drop your files here</strong><span>UTF-8 .txt · Up to 5 files · 2 MB each</span>
      <button className="button secondary" disabled={busy} onClick={() => input.current?.click()}>Choose files</button>
      <input ref={input} className="visually-hidden" type="file" tabIndex={-1} aria-label="Transcript files" accept=".txt,text/plain" multiple onChange={e => {choose(Array.from(e.target.files || [])); e.target.value = '';}}/>
    </div>
    {files.length > 0 && <ul className="file-list">{files.map((f, i) => <li key={f.name + i}><FileText size={18}/><span>{f.name}<small>{Math.max(1, Math.ceil(f.size / 1024))} KB</small></span><button className="icon-button" disabled={busy} aria-label={'Remove ' + f.name} onClick={() => setFiles(files.filter((_, n) => n !== i))}><X size={18}/></button></li>)}</ul>}
    <details className="format-help"><summary>Transcript format</summary><p>One expert per file. Include these headers, then a timestamp and speaker for each passage.</p><pre>{'Expert: Jane Smith\nRole: Research Director\nMarket: United Kingdom\n\n00:00\nInterviewer: Your question?\n\n00:18\nJane Smith: The expert response.'}</pre><p>Use MM:SS or HH:MM:SS. Label questions “Interviewer”, “Moderator” or “Host”; other speakers are treated as the expert.</p></details>
    {error && <p className="error-message" role="alert">{error}</p>}
    <div className="dialog-footer"><button className="button text-button" disabled={busy} onClick={onClose}>Cancel</button><button className="button primary" disabled={busy || !files.length} onClick={submit}>{busy && <LoaderCircle size={18} className="spin"/>}{busy ? 'Uploading…' : 'Upload' + (files.length ? ` ${files.length} ${files.length === 1 ? 'file' : 'files'}` : '')}</button></div>
  </Dialog>;
}
