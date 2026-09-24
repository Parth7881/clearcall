"""Single-process, temporary-workspace public demo entrypoint."""
import asyncio
import os
import secrets
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .main import ROOT, create_app
from .groq import GroqProvider, AIError


class BudgetProvider:
    def __init__(self, provider):
        self.provider = provider
        self.model = provider.model
        self.configured = provider.configured
        self.lock = threading.Lock()
        self.calls = []
        self.limit = int(os.getenv('PUBLIC_DAILY_AI_CALLS','100'))

    def generate(self, *args):
        now = time.time()
        with self.lock:
            self.calls = [t for t in self.calls if t > now - 86400]
            if len(self.calls) >= self.limit:
                raise AIError('The public demo has reached its daily AI allowance. Please try again later.')
            self.calls.append(now)
        return self.provider.generate(*args)


def create_public_app(provider=None):
    sessions = {}
    creation_times = []
    closing = set()
    shared_provider = BudgetProvider(provider or GroqProvider(ROOT))

    async def dispose(entry):
        while entry['inflight']:
            await asyncio.sleep(.1)
        manager = entry['app'].state.analysis_manager
        manager.cancel.set()
        await asyncio.to_thread(manager.close)
        entry['directory'].cleanup()

    def retire(token):
        entry = sessions.pop(token,None)
        if entry:
            task = asyncio.create_task(dispose(entry))
            closing.add(task)
            task.add_done_callback(closing.discard)

    async def sweep():
        while True:
            await asyncio.sleep(30)
            now = time.monotonic()
            for token,entry in list(sessions.items()):
                if now-entry['seen'] > 900 or now-entry['created'] > 3600:
                    retire(token)

    @asynccontextmanager
    async def lifespan(app):
        cleaner = asyncio.create_task(sweep())
        yield
        cleaner.cancel()
        for token in list(sessions): retire(token)
        if closing: await asyncio.gather(*closing,return_exceptions=True)

    app = FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    hosts = ['localhost','127.0.0.1','testserver']
    hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME') or os.getenv('PUBLIC_HOSTNAME')
    if hostname: hosts.append(hostname)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=hosts)

    @app.middleware('http')
    async def headers(request: Request, call_next):
        origin = request.headers.get('origin')
        if request.method not in ('GET','HEAD') and origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'This request must come from this website.'},status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.get('/api/health')
    def health(): return {'status':'ok'}

    @app.get('/api/runtime')
    def runtime(): return {'ephemeral':True}

    # Delegate APIs to isolated apps, never the local user's database.
    class WorkspaceRouter:
        async def __call__(self,scope,receive,send):
            if scope['type'] != 'http': return
            path = scope['path']
            method = scope['method']
            headers = dict(scope['headers'])
            async def error(message,status):
                await JSONResponse({'detail':message},status_code=status)(scope,receive,send)
            if path == '/api/session' and method == 'POST':
                now = time.monotonic()
                creation_times[:] = [t for t in creation_times if t > now-60]
                if len(sessions)+len(closing) >= 4 or len(creation_times) >= 20:
                    return await error('The free demo is busy. Please try again shortly.',429)
                creation_times.append(now)
                directory = tempfile.TemporaryDirectory(prefix='clearcall-public-')
                token = secrets.token_urlsafe(32)
                child = create_app(Path(directory.name),provider=shared_provider,public_session=True)
                sessions[token] = {'app':child,'directory':directory,'seen':now,'created':now,'inflight':0}
                return await JSONResponse({'token':token})(scope,receive,send)
            token = headers.get(b'x-workspace-session',b'').decode('ascii',errors='ignore')
            entry = sessions.get(token)
            if not entry: return await error('This temporary workspace has expired. Refresh to start again.',401)
            if path == '/api/session' and method == 'DELETE':
                retire(token)
                return await JSONResponse({'cleared':True})(scope,receive,send)
            if path == '/api/samples' or path.startswith('/api/docs') or path.endswith('openapi.json'):
                return await error('Not found.',404)
            try: size = int(headers.get(b'content-length',b'0'))
            except ValueError: return await error('Invalid request size.',400)
            if method == 'POST' and b'content-length' not in headers:
                return await error('A request size is required.',411)
            limit = 51*1024*1024 if path == '/api/transcripts' else 1024*1024
            if size > limit: return await error('This request is too large.',413)
            entry['seen'] = time.monotonic()
            child_scope = dict(scope,root_path='')
            entry['inflight'] += 1
            try:
                await entry['app'](child_scope,receive,send)
            finally:
                entry['inflight'] -= 1

    # Keep runtime and health outside session routing.
    app.mount('/api',WorkspaceRouter())
    dist = ROOT/'frontend'/'dist'
    if dist.is_dir(): app.mount('/',StaticFiles(directory=dist,html=True))
    return app
