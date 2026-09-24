import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.analysis import validate_answer, chunk_passages

RAW = (Path(__file__).parents[1] / 'samples/Transcript_1_France.txt').read_bytes()

def test_upload_35_and_atomic_failure(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        files = [('files', (f'{i}.txt', RAW.replace(b'Jean Martin', f'Jean Martin {i}'.encode()))) for i in range(35)]
        assert c.post('/api/transcripts', files=files).json()['added'] == 35
        assert len(c.get('/api/transcripts').json()) == 35
        bad = files[:1] + [('files', ('bad.txt', b'invalid'))]
        assert c.post('/api/transcripts', files=bad).status_code == 422
        assert len(c.get('/api/transcripts').json()) == 35

def test_citation_gate():
    rows = {'t1': {'id': 't1', 'expert': 'Jane', 'market': 'UK', 'passages': [
        {'ordinal': 0, 'timestamp': '00:10', 'speaker': 'Jane', 'is_expert': True, 'text': 'Training is the main constraint.', 'start_offset': 50},
        {'ordinal': 1, 'timestamp': '00:20', 'speaker': 'Interviewer', 'is_expert': False, 'text': 'Is it price?', 'start_offset': 100}]}}
    good = {'answer': 'Training limits adoption.', 'evidence': [{'transcript_id': 't1', 'passage_id': 0, 'quote': 'Training is the main constraint.'}]}
    checked = validate_answer(good, rows)
    assert checked['status'] == 'supported'
    assert checked['evidence'][0]['start_offset'] == 50
    for evidence in [[], [{'transcript_id':'t1','passage_id':0,'quote':'Invented'}], [{'transcript_id':'t1','passage_id':1,'quote':'Is it price?'}], [{'transcript_id':'unknown','passage_id':0,'quote':'Training'}]]:
        assert validate_answer({**good, 'evidence':evidence}, rows)['status'] == 'insufficient'

def test_long_passages_are_not_dropped():
    passages = [{'ordinal':0,'text':'x' * 70000,'is_expert':True,'speaker':'A','timestamp':'00:00'}]
    chunks = chunk_passages(passages, 12000)
    assert len(chunks) > 1
    assert ''.join(p['text'] for chunk in chunks for p in chunk) == passages[0]['text']
    assert all(sum(len(p['text']) for p in chunk) <= 12000 for chunk in chunks)

class FakeProvider:
    model = 'test-only-provider'
    configured = True
    calls = 0
    def generate(self, task, payload, schema):
        self.calls += 1
        if task == 'extract':
            p = payload['passages'][0]
            evidence = [{'transcript_id': payload['transcript_id'], 'passage_id': p['ordinal'], 'quote': p['text']}]
            return {'answers':[{'question_index':i, 'answer':'Supported test answer.', 'evidence':evidence} for i in range(len(payload['questions']))]}
        if task == 'synthesize':
            return {'answers':[{'question_index':i,**payload['sources'][0]['answers'][i]} for i in range(len(payload['questions']))]}
        if task == 'ask':
            e = payload['passages'][0]
            return {'answer': 'Supported test answer.', 'evidence':[{'transcript_id':e['transcript_id'],'passage_id':e['ordinal'],'quote':e['text']}]}
        raise AssertionError(task)

def wait_job(c, job_id):
    for _ in range(200):
        job = c.get('/api/analysis/jobs/' + job_id).json()
        if job['status'] in ('completed','partial','failed','cancelled','interrupted'): return job
        time.sleep(.02)
    raise AssertionError('Job did not finish')

def test_35_source_job_cache_qa_and_restart(tmp_path):
    provider = FakeProvider()
    with TestClient(create_app(tmp_path, provider=provider)) as c:
        c.post('/api/transcripts', files=[('files',(f'{i}.txt',RAW.replace(b'Jean Martin',f'Jean Martin {i}'.encode()))) for i in range(35)])
        ids = [r['id'] for r in c.get('/api/transcripts').json()]
        payload = {'transcript_ids':ids,'questions':['What drives adoption?']}
        r = c.post('/api/analysis/jobs',json=payload)
        assert r.status_code == 202
        job = wait_job(c,r.json()['id'])
        assert job['status'] == 'completed'
        assert job['completed'] == 35
        assert len(job['result']['transcripts']) == 35
        calls = provider.calls
        second = wait_job(c,c.post('/api/analysis/jobs',json=payload).json()['id'])
        assert second['status'] == 'completed'
        assert provider.calls == calls + 1  # synthesis only; source analysis cached
        qa = wait_job(c,c.post('/api/analysis/ask',json={'transcript_ids':ids,'question':'What about training?'}).json()['id'])
        assert qa['result']['answer']['evidence']
        saved_id = job['id']
    with TestClient(create_app(tmp_path,provider=provider)) as c:
        assert c.get('/api/analysis/jobs/' + saved_id).json()['completed'] == 35

def test_missing_key_and_unknown_sources(tmp_path,monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.setenv('CLEARCALL_CONFIG_FILE',str(tmp_path/'absent.env'))
    with TestClient(create_app(tmp_path)) as c:
        c.post('/api/samples')
        ids=[r['id'] for r in c.get('/api/transcripts').json()]
        assert c.get('/api/analysis/config').json()['configured'] is False
        assert c.post('/api/analysis/jobs',json={'transcript_ids':ids,'questions':['Question?']}).status_code == 503
    with TestClient(create_app(tmp_path,provider=FakeProvider())) as c:
        assert c.post('/api/analysis/jobs',json={'transcript_ids':['missing'],'questions':['Question?']}).status_code == 404

def test_provider_transport_and_secret_redaction(tmp_path,monkeypatch):
    import httpx
    from app.groq import GroqProvider, AIError
    monkeypatch.setenv('GROQ_API_KEY','test-secret-only')
    def transport(request):
        assert request.headers['authorization']=='Bearer test-secret-only'
        body=json.loads(request.content)
        assert body['response_format']['json_schema']['strict'] is True
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"answer":"","evidence":[]}'}}]})
    p=GroqProvider(tmp_path,httpx.MockTransport(transport))
    assert p.generate('ask',{}, {})=={'answer':'','evidence':[]}
    p.transport=httpx.MockTransport(lambda r:httpx.Response(403,text='test-secret-only'))
    with pytest.raises(AIError) as exc: p.generate('ask',{}, {})
    assert 'test-secret-only' not in str(exc.value)


def test_cancel_busy_and_interrupted(tmp_path):
    import threading
    from app.store import Store
    entered, release=threading.Event(),threading.Event()
    class Slow(FakeProvider):
        def generate(self,*args):
            entered.set(); release.wait(3)
            return super().generate(*args)
    with TestClient(create_app(tmp_path,provider=Slow())) as c:
        c.post('/api/samples')
        ids=[r['id'] for r in c.get('/api/transcripts').json()]
        payload={'transcript_ids':ids,'questions':['Question?']}
        r=c.post('/api/analysis/jobs',json=payload); job_id=r.json()['id']
        assert entered.wait(2)
        assert c.post('/api/analysis/jobs',json=payload).status_code==409
        assert c.post('/api/analysis/jobs/'+job_id+'/cancel').status_code==200
        release.set()
        assert wait_job(c,job_id)['status']=='cancelled'
    store=Store(tmp_path)
    job=store.job(job_id); job['status']='running'; store.save_job(job)
    with TestClient(create_app(tmp_path,provider=FakeProvider())) as c:
        assert c.get('/api/analysis/jobs/'+job_id).json()['status']=='interrupted'


def test_partial_failures_and_question_limits(tmp_path):
    from app.groq import AIError
    class Partial(FakeProvider):
        def generate(self,task,payload,schema):
            if task=='extract' and payload['market']=='France': raise AIError('Test provider unavailable.')
            return super().generate(task,payload,schema)
    with TestClient(create_app(tmp_path,provider=Partial())) as c:
        c.post('/api/samples')
        ids=[r['id'] for r in c.get('/api/transcripts').json()]
        payload={'transcript_ids':ids,'questions':['Question?']}
        job=wait_job(c,c.post('/api/analysis/jobs',json=payload).json()['id'])
        assert job['status']=='partial'
        assert len(job['result']['transcripts'])==2
        assert len(job['result']['failures'])==1
        assert c.post('/api/analysis/jobs',json={**payload,'questions':['x'*501]}).status_code==422

@pytest.mark.parametrize('candidate',[
    {'finish_reason':'length','message':{'content':'{}'}},
    {'finish_reason':'stop','message':{'content':'not JSON'}},
    {'finish_reason':'stop','message':{'content':'[]'}},
])
def test_groq_rejects_unusable_output(tmp_path,monkeypatch,candidate):
    import httpx
    from app.groq import GroqProvider, AIError
    monkeypatch.setenv('GROQ_API_KEY','test-only')
    p=GroqProvider(tmp_path,httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[candidate]})))
    with pytest.raises(AIError):p.generate('ask',{}, {})


def test_groq_obeys_retry_after(tmp_path,monkeypatch):
    import httpx
    from app.groq import GroqProvider
    monkeypatch.setenv('GROQ_API_KEY','test-only')
    pauses=[];monkeypatch.setattr('app.groq.time.sleep',pauses.append)
    calls=[]
    def respond(request):
        calls.append(request)
        if len(calls)==1:return httpx.Response(429,headers={'retry-after':'12'})
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"answer":"","evidence":[]}'}}]})
    assert GroqProvider(tmp_path,httpx.MockTransport(respond)).generate('ask',{}, {})['evidence']==[]
    assert pauses==[12]
    assert len(calls)==2

def test_short_interviews_retain_all_expert_context(tmp_path):
    seen=[]
    class Capture(FakeProvider):
        def generate(self,task,payload,schema):
            if task=='ask':seen.extend(payload['passages'])
            return super().generate(task,payload,schema)
    with TestClient(create_app(tmp_path,provider=Capture())) as c:
        c.post('/api/samples');ids=[r['id'] for r in c.get('/api/transcripts').json()]
        job=wait_job(c,c.post('/api/analysis/ask',json={'transcript_ids':ids,'question':'Budgets and ROI?'}).json()['id'])
        assert job['status']=='completed'
        assert len(seen)==21
        assert any('finance alone' in p['text'] for p in seen)

def test_expert_id_subject_format_keeps_source_offsets(tmp_path):
    raw=b'Expert ID: EXP-05\nRole: Systems Engineer\nCore Subject: Infrastructure\n\n00:00\nInterviewer: What limits performance?\n\n00:18\nCandidate: Memory bandwidth is the limit.\n'
    with TestClient(create_app(tmp_path)) as c:
        r=c.post('/api/transcripts',files=[('files',('expert.txt',raw))]);assert r.status_code==200
        row=c.get('/api/transcripts').json()[0]
        assert row['expert']=='EXP-05' and row['market']=='Not specified'
        detail=c.get('/api/transcripts/'+row['id']).json();p=detail['passages'][1]
        assert raw.decode()[p['start_offset']:p['end_offset']]==p['text']
        assert c.get('/api/transcripts/'+row['id']+'/source').content==raw


def test_guide_returns_one_combined_answer_per_question(tmp_path):
    with TestClient(create_app(tmp_path,provider=FakeProvider())) as c:
        c.post('/api/samples');ids=[r['id'] for r in c.get('/api/transcripts').json()]
        job=wait_job(c,c.post('/api/analysis/jobs',json={'transcript_ids':ids,'questions':['What drives adoption?','What limits it?']}).json()['id'])
        assert len(job['result']['answers'])==2
        assert all(a['evidence'] for a in job['result']['answers'])
        assert 'themes' not in job['result'] and 'differences' not in job['result']

def test_combined_answer_retries_invalid_citation(tmp_path):
    class Retry(FakeProvider):
        synthesis=0
        def generate(self,task,payload,schema):
            if task=='synthesize':
                self.synthesis+=1
                if self.synthesis==1:return {'answers':[{'question_index':0,'answer':'Bad quote','evidence':[]}]}
            return super().generate(task,payload,schema)
    provider=Retry()
    with TestClient(create_app(tmp_path,provider=provider)) as c:
        c.post('/api/samples');ids=[r['id'] for r in c.get('/api/transcripts').json()]
        j=wait_job(c,c.post('/api/analysis/jobs',json={'transcript_ids':ids,'questions':['What drives adoption?']}).json()['id'])
        assert j['result']['answers'][0]['status']=='supported'
        assert provider.synthesis==2
