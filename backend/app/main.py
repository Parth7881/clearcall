from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated
from .analysis import AnalysisManager, QUESTIONS
from .gemini import GeminiProvider, AIError
import json
import os
from pathlib import Path
from urllib.parse import quote, urlparse
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .parser import MAX_BYTES, parse_transcript
from .store import Store

ROOT = Path(__file__).resolve().parents[2]

class AnalysisRequest(BaseModel):
    transcript_ids: list[str] = Field(min_length=1,max_length=50)
    questions: list[Annotated[str, StringConstraints(min_length=1,max_length=500)]] = Field(default=QUESTIONS,min_length=1,max_length=12)

class AskRequest(BaseModel):
    transcript_ids: list[str] = Field(min_length=1,max_length=50)
    question: str = Field(min_length=1,max_length=2000)

def create_app(data_dir: Path | None = None, provider=None) -> FastAPI:
    store = Store(data_dir or Path(os.environ.get('CLEARCALL_DATA_DIR', ROOT / 'data')))
    manager = AnalysisManager(store)
    @asynccontextmanager
    async def lifespan(app):
        yield
        manager.close()
    app = FastAPI(lifespan=lifespan, title='Clearcall', version='1.0.0', docs_url='/api/docs', redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

    @app.middleware('http')
    async def local_origin(request: Request, call_next):
        origin = request.headers.get('origin')
        if request.method == 'POST' and origin:
            parsed = urlparse(origin)
            if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('127.0.0.1', 'localhost', 'testserver'):
                return JSONResponse({'detail': 'Only the local app can upload files.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'version': '1.0.0'}

    @app.get('/api/transcripts')
    def transcripts():
        return store.all()

    def find(transcript_id):
        row = store.get(transcript_id)
        if row is None:
            raise HTTPException(404, 'Transcript not found.')
        return row

    @app.get('/api/transcripts/{transcript_id}')
    def detail(transcript_id: str):
        row = find(transcript_id)
        return {k: v for k, v in row.items() if k not in ('raw', 'digest', 'passages')} | {'passages': json.loads(row['passages'])}

    @app.get('/api/transcripts/{transcript_id}/source')
    def source(transcript_id: str):
        row = find(transcript_id)
        return Response(row['raw'], media_type='application/octet-stream', headers={
            'Content-Disposition': "attachment; filename*=UTF-8''" + quote(row['filename'], safe='')})

    @app.post('/api/transcripts')
    async def upload(files: list[UploadFile]):
        items = []
        try:
            if not 1 <= len(files) <= 50:
                raise HTTPException(422, 'Choose between one and 50 transcripts.')
            total_bytes = 0
            for file in files:
                filename = (file.filename or 'transcript.txt').replace('\\', '/').split('/')[-1]
                raw = await file.read(MAX_BYTES + 1)
                total_bytes += len(raw)
                if total_bytes > 50 * 1024 * 1024:
                    raise HTTPException(422, 'Keep each upload below 50 MB total.')
                try:
                    parsed = parse_transcript(raw, filename)
                except ValueError as exc:
                    raise HTTPException(422, f'{filename}: {exc}') from exc
                items.append((filename, raw, parsed))
            return store.ingest(items)
        finally:
            for file in files:
                await file.close()

    @app.post('/api/samples')
    def samples():
        items = []
        for path in sorted((ROOT / 'backend' / 'samples').glob('Transcript_*.txt')):
            raw = path.read_bytes()
            items.append((path.name, raw, parse_transcript(raw, path.name)))
        return store.ingest(items)

    @app.get('/api/analysis/config')
    def config():
        current = provider or GeminiProvider(ROOT)
        return {'configured':current.configured,'model':current.model,'questions':QUESTIONS,'max_sources':50}

    def submit(body, ask=False):
        ids = list(dict.fromkeys(body.transcript_ids))
        rows = {i:find(i) for i in ids}
        for row in rows.values(): row['passages'] = json.loads(row['passages'])
        current = provider or GeminiProvider(ROOT)
        if not current.configured: raise HTTPException(503,'Add GEMINI_API_KEY to your local .env file to enable analysis.')
        try:
            return manager.start(current,rows,question=body.question.strip()) if ask else manager.start(current,rows,questions=[q.strip() for q in body.questions])
        except AIError as exc: raise HTTPException(409,str(exc)) from exc

    @app.post('/api/analysis/jobs',status_code=202)
    def analyze(body: AnalysisRequest):
        if any(not q.strip() for q in body.questions): raise HTTPException(422,'Questions cannot be blank.')
        return submit(body)

    @app.post('/api/analysis/ask',status_code=202)
    def ask(body: AskRequest):
        if not body.question.strip(): raise HTTPException(422,'Enter a question.')
        return submit(body,True)

    @app.get('/api/analysis/jobs')
    def jobs():
        return [{k:v for k,v in j.items() if k != 'result'} for j in store.jobs()]

    @app.get('/api/analysis/jobs/{job_id}')
    def job_detail(job_id: str):
        job = store.job(job_id)
        if not job: raise HTTPException(404,'Analysis not found.')
        return job

    @app.post('/api/analysis/jobs/{job_id}/cancel')
    def cancel(job_id: str):
        with manager.lock:
            if manager.active != job_id: raise HTTPException(409,'This analysis is no longer running.')
            manager.cancel.set()
        return {'status':'cancelling'}

    dist = ROOT / 'frontend' / 'dist'
    if dist.is_dir():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app
