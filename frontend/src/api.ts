export let ephemeral = false;
let workspaceToken = '';
export async function initializeWorkspace() {
  const response = await fetch('/api/runtime');
  if(response.status===404) return; // Older local servers do not expose runtime settings.
  if(!response.ok) throw new Error('Unable to open the workspace. Please refresh to retry.');
  ephemeral = (await response.json()).ephemeral === true;
  if(ephemeral) {
    const session = await fetch('/api/session',{method:'POST'});
    const body = await session.json();
    if(!session.ok) throw new Error(body.detail || 'The free demo is busy. Please try again shortly.');
    workspaceToken = body.token;
    history.replaceState(null,'',location.pathname);
    window.addEventListener('pagehide',()=>{void fetch('/api/session',{method:'DELETE',headers:{'X-Workspace-Session':workspaceToken},keepalive:true}).catch(()=>{});});
    window.addEventListener('pageshow',event=>{if(event.persisted) location.reload();});
  }
}
export function workspaceFetch(path:string, options?:RequestInit) {
  const headers = new Headers(options?.headers);
  if(workspaceToken) headers.set('X-Workspace-Session',workspaceToken);
  return fetch('/api'+path,{...options,headers});
}
export async function downloadSource(id:string, filename:string) {
  const response = await workspaceFetch('/transcripts/'+id+'/source');
  if(!response.ok) throw new Error('Source download failed. The workspace may have expired.');
  const url = URL.createObjectURL(await response.blob());
  const link=document.createElement('a'); link.href=url; link.download=filename; link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await workspaceFetch(path, options); }
  catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new Error('Unable to reach Clearcall. Check that the local server is running, then try again.');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === 'string' ? body.detail : 'Something went wrong. Please try again.');
  }
  return response.json();
}
export const errorMessage = (e: unknown) => e instanceof Error ? e.message : 'Something went wrong. Please try again.';
