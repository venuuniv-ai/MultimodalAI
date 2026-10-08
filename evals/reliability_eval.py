"""Real localhost HTTP reliability/throughput workload, with bounded concurrency."""
import concurrent.futures
import json
import os
import socket
import subprocess
import time
from collections import Counter
from pathlib import Path

import httpx

from backend.app.agent import NO_EVIDENCE,validate_citations
from .metrics import distribution

ROOT=Path(__file__).resolve().parents[1]


def inspect_response(result):
    """Contract failures separate malformed bodies from invalid citation IDs."""
    if not isinstance(result,dict):
        return 'malformed_response'
    if not isinstance(result.get('answer'),str) or not isinstance(result.get('sources'),list) or not isinstance(result.get('trace'),list):
        return 'malformed_response'
    if not all(isinstance(source,dict) and all(key in source for key in ['id','text','name','page']) for source in result['sources']):
        return 'malformed_response'
    check=validate_citations(result['answer'],result['sources'])
    if check['invalid']:
        return 'citation_validation_failure'
    if result.get('mode') not in ['extractive','ollama','clarification','tool']:
        return 'malformed_response'
    if result['answer']!=NO_EVIDENCE and result['mode'] not in ['clarification','tool'] and not check['valid']:
        return 'citation_validation_failure'
    return None


def summarize(rows,wall_s):
    failures=[row for row in rows if row['failure']]
    counts=Counter(row['failure'] for row in failures)
    return dict(total_requests=len(rows),successful_requests=len(rows)-len(failures),failed_requests=len(failures),
                success_rate=(len(rows)-len(failures))/len(rows) if rows else None,
                timeout_rate=counts['timeout']/len(rows) if rows else None,exception_rate=counts['exception']/len(rows) if rows else None,
                malformed_response_rate=counts['malformed_response']/len(rows) if rows else None,
                citation_validation_failures=counts['citation_validation_failure'],failure_reasons=dict(counts),
                latency_ms=distribution(row['latency_ms'] for row in rows),wall_seconds=wall_s,
                requests_per_second=len(rows)/wall_s if wall_s else None,
                successful_requests_per_second=(len(rows)-len(failures))/wall_s if wall_s else None)


def run_http(corpus,dataset,directory,samples=512,model='qwen2.5:1.5b',llm_samples=24):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    env={**os.environ,'RESEARCH_DESK_DB':str(corpus.store.path)}
    log_path=Path(directory)/'benchmark-server.log'
    rows=[]
    batches=[]
    pool=[case for case in dataset['cases'] if case['category'] not in ['adversarial','csv_tool']]
    process=None
    with log_path.open('w') as log:
        try:
            process=subprocess.Popen([os.sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',str(port),'--log-level','warning'],cwd=ROOT,env=env,stdout=log,stderr=log)
            url=f'http://127.0.0.1:{port}'
            with httpx.Client(base_url=url,timeout=130,trust_env=False) as client:
                deadline=time.monotonic()+30
                while True:
                    try:
                        response=client.get('/api/health')
                        response.raise_for_status()
                        break
                    except (httpx.HTTPError,OSError):
                        if process.poll() is not None or time.monotonic()>deadline:
                            raise RuntimeError('Benchmark server failed readiness: '+log_path.read_text())
                        time.sleep(.1)
                def request(index,mode,concurrency):
                    case=pool[(index*37) % len(pool)]
                    start=time.perf_counter()
                    failure,detail,result=None,None,{}
                    try:
                        response=client.post('/api/ask',json={'question':case['question'],'mode':mode,'model':model})
                        if response.status_code!=200:
                            failure,detail='http_error',f'{response.status_code}: {response.text[:500]}'
                        else:
                            try:
                                result=response.json()
                                failure=inspect_response(result)
                            except ValueError as exc:
                                failure,detail='malformed_response',str(exc)
                    except httpx.TimeoutException as exc:
                        failure,detail='timeout',str(exc)
                    except Exception as exc:
                        failure,detail='exception',f'{type(exc).__name__}: {exc}'
                    return dict(index=index,case_id=case['id'],question=case['question'],mode=mode,concurrency=concurrency,
                                latency_ms=(time.perf_counter()-start)*1000,failure=failure,error=detail,
                                answer=result.get('answer') if isinstance(result,dict) else None,
                                citation_check=result.get('citation_check') if isinstance(result,dict) else None)
                # Connection/server warmup excluded; real responses still captured separately.
                warmup=[request(i,'extractive',1) for i in range(4)]
                for batch_index,concurrency in enumerate([1,2,4,8]):
                    count=samples//4+int(batch_index < samples%4)
                    start=time.perf_counter()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                        batch=list(executor.map(lambda i:request(i,'extractive',concurrency),range(count)))
                    wall=time.perf_counter()-start
                    batches.append({'mode':'extractive','concurrency':concurrency,**summarize(batch,wall)})
                    rows.extend(batch)
                if llm_samples:
                    # Separate warmup so process readiness and model loading are excluded.
                    warmup.extend(request(0,'ollama',1) for _ in range(2))
                    start=time.perf_counter()
                    batch=[request(i,'ollama',1) for i in range(llm_samples)]
                    wall=time.perf_counter()-start
                    batches.append({'mode':'ollama','concurrency':1,**summarize(batch,wall)})
                    rows.extend(batch)
        finally:
            if process and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    modes={mode:summarize([r for r in rows if r['mode']==mode],sum(b['wall_seconds'] for b in batches if b['mode']==mode)) for mode in sorted({r['mode'] for r in rows})}
    return {'boundary':'HTTP /api/ask on isolated uvicorn subprocess; loopback client overhead included',
            'timeout_seconds':130,'warmup':warmup,'batches':batches,'by_mode':modes,'raw':rows,
            'server_log':log_path.read_text(),'limitations':'Closed-loop bounded client threads, not arrival-rate capacity or soak test. Repeated synthetic queries, all-source base corpus; adversarial scoped contexts and CSV tools excluded from HTTP load. Success means transport/schema/citation-ID validity, not answer correctness.'}
