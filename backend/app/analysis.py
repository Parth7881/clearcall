"""Persistent, bounded analysis jobs with server-validated source citations."""
import hashlib
import json
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from .groq import AIError

QUESTIONS = ['How would you describe current adoption of robotic surgery in your market?',
             'What are the main barriers to adoption?',
             'How important are hospital budgets and ROI in purchasing decisions?',
             'How important are surgeon training and clinical outcomes?',
             'What adoption trend do you expect over the next 3–5 years?',
             'What is the typical hospital decision-making timeline for purchasing a new robotic system?']

def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}

STRING = {'type':'string'}
EVIDENCE = obj({'transcript_id':STRING,'passage_id':{'type':'integer'},'quote':STRING})
ANSWER = obj({'answer':STRING,'evidence':{'type':'array','items':EVIDENCE}})
EXTRACT = obj({'answers':{'type':'array','items':obj({**ANSWER['properties'],'question_index':{'type':'integer'}})}})
SYNTHESIS = EXTRACT

def validate_answer(value, rows):
    empty = {'answer':'No supported answer in these sources.','status':'insufficient','evidence':[]}
    if not isinstance(value,dict) or not isinstance(value.get('answer'),str) or not value['answer'].strip():
        return empty
    evidence = value.get('evidence')
    if not isinstance(evidence,list) or not evidence:
        return empty
    checked = []
    for e in evidence:
        if not isinstance(e,dict): return empty
        row = rows.get(e.get('transcript_id'))
        if not row or type(e.get('passage_id')) is not int: return empty
        quote = e.get('quote')
        p = next((p for p in row['passages'] if p['ordinal'] == e['passage_id'] and isinstance(quote,str) and quote in p['text']),None)
        if not p or not p['is_expert'] or not isinstance(quote,str) or not quote.strip() or quote not in p['text']:
            return empty
        start = p.get('start_offset',0) + p['text'].index(quote)
        checked.append({'transcript_id':row['id'],'passage_id':p['ordinal'],'quote':quote,
                        'expert':row['expert'],'market':row['market'],'timestamp':p['timestamp'],
                        'start_offset':start,'end_offset':start+len(quote)})
    return {'answer':value['answer'].strip(),'status':'supported','evidence':checked}

def chunk_passages(passages, budget=24000):
    chunks, current, size = [], [], 0
    for p in passages:
        if not p['is_expert']: continue
        for start in range(0,len(p['text']),budget):
            piece = {**p,'text':p['text'][start:start+budget], 'start_offset':p.get('start_offset',0)+start}
            if current and size + len(piece['text']) > budget:
                chunks.append(current); current, size = [], 0
            current.append(piece); size += len(piece['text'])
    if current: chunks.append(current)
    return chunks

class AnalysisManager:
    def __init__(self, store):
        self.store = store
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.lock = threading.Lock()
        self.active = None
        self.cancel = threading.Event()
        for job in store.jobs(10000):
            if job['status'] in ('running','queued'):
                job['status'] = 'interrupted'; job['error'] = 'Server restarted. Run again to resume cached work.'
                store.save_job(job)

    def start(self, provider, rows, questions=None, question=None):
        with self.lock:
            if self.active: raise AIError('Another analysis is running. Wait or cancel it first.')
            job = {'id':uuid.uuid4().hex,'kind':'ask' if question else 'analysis','status':'queued',
                   'model':provider.model,'transcript_ids':list(rows),'questions':questions or [],
                   'question':question or '', 'completed':0,'total':len(rows),'result':None,'error':''}
            self.active = job['id']; self.cancel.clear()
            self.store.save_job(job)
            self.pool.submit(self.run,job,provider,rows)
            return job

    def run(self, job, provider, rows):
        try:
            job['status'] = 'running'; self.store.save_job(job)
            if job['kind'] == 'ask':
                words = set(re.findall(r'\w+',job['question'].lower()))
                selected, extra = [], []
                count = 0
                for row in rows.values():
                    pieces = [p for chunk in chunk_passages(row['passages'],1200) for p in chunk]
                    count += len(pieces)
                    pieces.sort(key=lambda p:len(words & set(re.findall(r'\w+',p['text'].lower()))),reverse=True)
                    selected.extend({**p,'transcript_id':row['id']} for p in pieces[:1])
                    extra.extend({**p,'transcript_id':row['id']} for p in pieces[1:])
                extra.sort(key=lambda p:len(words & set(re.findall(r'\w+',p['text'].lower()))),reverse=True)
                used = sum(len(p['text']) for p in selected)
                for p in extra:
                    if used + len(p['text']) <= 64000:
                        selected.append(p); used += len(p['text'])
                context = {k:{**v,'passages':[p for p in selected if p['transcript_id']==k]} for k,v in rows.items()}
                value = provider.generate('ask',{'question':job['question'],'passages':selected},ANSWER)
                job['result'] = {'answer':validate_answer(value,context),'passages_searched':count,'passages_used':len(selected)}
                job['completed'] = len(rows)
            else:
                results, failures = [], []
                job['result'] = {'transcripts':results,'answers':[],'failures':failures}
                for row in rows.values():
                    if self.cancel.is_set(): break
                    try:
                        key = hashlib.sha256(json.dumps([row['id'],row['digest'],job['questions'],provider.model,'groq-v3']).encode()).hexdigest()
                        result = self.store.cached(key)
                        if result is None:
                            grouped = [[] for _ in job['questions']]
                            for chunk in chunk_passages(row['passages']):
                                if self.cancel.is_set(): break
                                value = provider.generate('extract',{'transcript_id':row['id'],'expert':row['expert'],'market':row['market'],
                                    'questions':job['questions'],'passages':chunk},EXTRACT)
                                answers = value.get('answers')
                                if not isinstance(answers,list): raise AIError('Groq returned an invalid answer list.')
                                for answer in answers:
                                    index = answer.get('question_index') if isinstance(answer,dict) else None
                                    if type(index) is int and 0 <= index < len(grouped):
                                        checked = validate_answer(answer,{row['id']:{**row,'passages':chunk}})
                                        if checked['status'] == 'supported': grouped[index].append(checked)
                            if self.cancel.is_set(): break
                            result = {'id':row['id'],'expert':row['expert'],'market':row['market'],'answers':[
                                {'question':q, **( {'answer':'\n\n'.join(a['answer'] for a in group),'status':'supported',
                                  'evidence':[e for a in group for e in a['evidence']]} if group else validate_answer({},{}))}
                                for q,group in zip(job['questions'],grouped)]}
                            self.store.cache(key,result)
                        results.append(result)
                    except AIError as exc:
                        failures.append({'expert':row['expert'],'error':str(exc)})
                    job['completed'] += 1; self.store.save_job(job)
                if results and not self.cancel.is_set():
                    compact = [{'expert':r['expert'],'market':r['market'],'answers':[{'question':a['question'],'answer':a['answer'][:500],
                        'evidence':[{'transcript_id':e['transcript_id'],'passage_id':e['passage_id'],'quote':e['quote'][:500]} for e in a['evidence'][:2]]} for a in r['answers']]} for r in results]
                    try:
                        synthesis = provider.generate('synthesize',{'questions':job['questions'],'sources':compact},SYNTHESIS)
                        values = synthesis.get('answers',[])
                        if not isinstance(values,list): raise AIError('The combined answer could not be read. Try again.')
                        for index, question in enumerate(job['questions']):
                            value = next((a for a in values if isinstance(a,dict) and a.get('question_index') == index),{})
                            checked = validate_answer(value,rows)
                            has_evidence = any(r['answers'][index]['evidence'] for r in results)
                            if checked['status'] != 'supported' and has_evidence:
                                retry_sources = [{**source,'answers':[source['answers'][index]]} for source in compact]
                                retry = provider.generate('synthesize',{'questions':[question],'sources':retry_sources,
                                    'validation_note':'Previous answer lacked valid exact quotes. Copy evidence quote strings exactly, including punctuation and spacing.'},SYNTHESIS)
                                retry_values = retry.get('answers',[])
                                checked = validate_answer(retry_values[0] if isinstance(retry_values,list) and retry_values else {},rows)
                                if checked['status'] != 'supported':
                                    checked['answer'] = 'An answer could not be verified against the source quotes. Please try again.'
                            job['result']['answers'].append({'question':question,**checked})
                    except AIError as exc:
                        job['error'] = str(exc)
                if failures: job['error'] = f'{len(failures)} interviews could not be analyzed. Run again to retry.'
            job['status'] = 'cancelled' if self.cancel.is_set() else ('partial' if job['error'] else 'completed')
        except AIError as exc:
            job['status'] = 'failed'; job['error'] = str(exc)
        except Exception:
            job['status'] = 'failed'; job['error'] = 'Analysis could not finish. Run again to retry.'
        finally:
            with self.lock:
                self.store.save_job(job)
                self.active = None

    def close(self):
        self.cancel.set()
        self.pool.shutdown(wait=True,cancel_futures=True)
