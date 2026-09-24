"""Build a source + production-assets archive, excluding all local state."""
from pathlib import Path
import hashlib
import zipfile

root = Path(__file__).resolve().parents[1]
destination = root.parent / 'clearcall-part1.zip'
files = [root / name for name in ('README.md', 'start.ps1', '.gitignore', '.env.example',
         'requirements.txt', 'requirements-dev.txt', 'requirements.lock.txt', 'pytest.ini')]
files += [root / 'frontend' / name for name in ('package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts', 'index.html')]
for directory in ('backend/app', 'backend/samples', 'backend/tests', 'frontend/src', 'frontend/public', 'frontend/dist', 'docs', 'tools'):
    files.extend(p for p in (root / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(set(files)):
        archive.write(path, 'clearcall/' + path.relative_to(root).as_posix())
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert not any(any(part in name.split('/') for part in ('node_modules', '.venv', 'data', '.env', '.qa-data', '__pycache__')) for name in names)
    assert 'clearcall/frontend/dist/index.html' in names
digest = hashlib.sha256(destination.read_bytes()).hexdigest()
destination.with_suffix('.zip.sha256').write_text(digest + '  ' + destination.name + '\n', encoding='ascii')
print(f'{destination}\n{len(names)} files; {destination.stat().st_size:,} bytes\nSHA256 {digest}')
