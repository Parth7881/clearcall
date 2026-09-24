from fastapi.testclient import TestClient
from app.public import create_public_app, BudgetProvider
from app.groq import AIError
from test_analysis import FakeProvider, RAW
import pytest


def test_public_workspaces_isolated_and_reset():
    with TestClient(create_public_app(provider=FakeProvider())) as c:
        assert c.get('/api/runtime').json()=={'ephemeral':True}
        a=c.post('/api/session').json()['token']
        b=c.post('/api/session').json()['token']
        ha={'X-Workspace-Session':a};hb={'X-Workspace-Session':b}
        assert c.post('/api/transcripts',headers=ha,files=[('files',('sample.txt',RAW))]).status_code==200
        rows=c.get('/api/transcripts',headers=ha).json();assert len(rows)==1
        assert c.get('/api/transcripts',headers=hb).json()==[]
        assert c.get('/api/transcripts/'+rows[0]['id'],headers=hb).status_code==404
        assert c.get('/api/transcripts/'+rows[0]['id']+'/source',headers=ha).content==RAW
        assert c.get('/api/transcripts').status_code==401
        assert c.delete('/api/session',headers=ha).status_code==200
        assert c.get('/api/transcripts',headers=ha).status_code==401
        assert c.post('/api/samples',headers=hb).status_code==404
        assert c.post('/api/session',headers={'Origin':'https://untrusted.example'}).status_code==403


def test_public_budget(monkeypatch):
    monkeypatch.setenv('PUBLIC_DAILY_AI_CALLS','0')
    p=BudgetProvider(FakeProvider())
    with pytest.raises(AIError,match='allowance'):p.generate('ask',{}, {})
