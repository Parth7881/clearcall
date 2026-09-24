import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

export default function Dialog({title, onClose, busy = false, children}: {title: string; onClose: () => void; busy?: boolean; children: ReactNode}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = ref.current!;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    element.showModal();
    return () => {element.close(); opener?.focus();};
  }, []);
  return <dialog ref={ref} aria-labelledby="dialog-title" onKeyDown={e => {
    if (e.key !== 'Tab') return;
    const focusable = Array.from(ref.current!.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled):not([tabindex="-1"]), a[href], select, summary')).filter(node => node.getClientRects().length > 0);
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (!first) {e.preventDefault(); return;}
    if (e.shiftKey && document.activeElement === first) {e.preventDefault(); last.focus();}
    else if (!e.shiftKey && document.activeElement === last) {e.preventDefault(); first.focus();}
  }} onCancel={e => {e.preventDefault(); if (!busy) onClose();}}>
    <div className="dialog-heading"><h2 id="dialog-title">{title}</h2><button className="icon-button" aria-label="Close dialog" disabled={busy} onClick={onClose}><X size={20}/></button></div>
    {children}
  </dialog>;
}
