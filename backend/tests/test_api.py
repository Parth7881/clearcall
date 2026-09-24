from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.parser import parse_transcript

SAMPLES = Path(__file__).parents[1] / 'samples'
RAW = (SAMPLES / 'Transcript_1_France.txt').read_bytes()

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        yield c

def test_samples_and_exact_sources(client):
    assert client.post('/api/samples').json()['added'] == 3
    rows = client.get('/api/transcripts').json()
    assert len(rows) == 3
    details = [client.get('/api/transcripts/' + r['id']).json() for r in rows]
    assert sum(len(d['passages']) for d in details) == 42
    assert sum(p['is_expert'] for d in details for p in d['passages']) == 21
    for d in details:
        original = (SAMPLES / d['filename']).read_bytes()
        assert client.get('/api/transcripts/' + d['id'] + '/source').content == original
        source = original.decode('utf-8-sig')
        for p in d['passages']:
            assert source[p['start_offset']:p['end_offset']] == p['text']
    assert client.post('/api/samples').json() == {'added': 0, 'duplicates': 3}

def test_renamed_duplicate_and_persistence(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        assert c.post('/api/transcripts', files=[('files', ('first.txt', RAW))]).json()['added'] == 1
        assert c.post('/api/transcripts', files=[('files', ('renamed.txt', RAW))]).json()['duplicates'] == 1
    with TestClient(create_app(tmp_path)) as c:
        assert len(c.get('/api/transcripts').json()) == 1

def test_atomic_invalid_batch(client):
    r = client.post('/api/transcripts', files=[('files', ('good.txt', RAW)), ('files', ('bad.txt', b'invalid'))])
    assert r.status_code == 422
    assert client.get('/api/transcripts').json() == []

@pytest.mark.parametrize('raw', [b'\xff', b'\x00', b'', RAW.replace(b'Market:', b'Country:'), RAW.replace(b'01:12', b'00:10'), RAW.replace(b'01:12', b'01:99'), RAW.replace(b'Interviewer:', b'Interviewer', 1)])
def test_reject_malformed(raw):
    with pytest.raises(ValueError):
        parse_transcript(raw, 'test.txt')

def test_unicode_crlf():
    raw = b'\xef\xbb\xbf' + RAW.decode('utf-8').replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8')
    p = parse_transcript(raw, 'test.txt')
    for passage in p['passages']:
        assert raw.decode('utf-8-sig')[passage['start_offset']:passage['end_offset']] == passage['text']

def test_limits_and_missing(client):
    assert client.post('/api/transcripts', files=[('files', ('x.pdf', RAW))]).status_code == 422
    assert client.post('/api/transcripts', files=[('files', ('x.txt', b'x' * (2 * 1024 * 1024 + 1)))]).status_code == 422
    assert client.post('/api/transcripts', files=[('files', (str(i) + '.txt', RAW)) for i in range(51)]).status_code == 422
    assert client.get('/api/transcripts/missing').status_code == 404
    assert client.get('/api/transcripts/missing/source').status_code == 404

def test_untrusted_origin(client):
    assert client.post('/api/samples', headers={'origin': 'https://example.com'}).status_code == 403

@pytest.mark.parametrize('raw', [
    b'Expert: Jane\nRole:\nMarket: UK\n\n00:00\nJane: Hello',
    b'Expert: Jane\nRole: Lead\nMarket: UK\n\nJane: Lost speech\n\n00:20\nJane: Goodbye',
    b'Expert: Jane\nRole: Lead\nMarket: UK\n\n00:00\nJane: Answer\n\nInterviewer: Missing timestamp?',
])
def test_reject_lost_or_merged_speech(raw):
    with pytest.raises(ValueError):
        parse_transcript(raw, 'test.txt')
