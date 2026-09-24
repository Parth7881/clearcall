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

def create_app(data_dir: Path | None = None) -> FastAPI:
    store = Store(data_dir or Path(os.environ.get('CLEARCALL_DATA_DIR', ROOT / 'data')))
    app = FastAPI(title='Clearcall', version='1.0.0', docs_url='/api/docs', redoc_url=None)
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
        if not 1 <= len(files) <= 5:
            raise HTTPException(422, 'Choose between one and five transcripts.')
        items = []
        try:
            for file in files:
                filename = (file.filename or 'transcript.txt').replace('\\', '/').split('/')[-1]
                raw = await file.read(MAX_BYTES + 1)
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

    dist = ROOT / 'frontend' / 'dist'
    if dist.is_dir():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app
