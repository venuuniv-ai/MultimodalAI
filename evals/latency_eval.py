"""Observational timers around the actual application; no behavior changes."""
import time
from contextlib import contextmanager
from unittest.mock import patch

from backend.app import agent


class TimedStore:
    def __init__(self,store):
        self.store=store
        self.search_ms=[]
        self.retrieved=[]

    def __getattr__(self,name):
        return getattr(self.store,name)

    def search(self,*args,**kwargs):
        start=time.perf_counter()
        try:
            self.retrieved=self.store.search(*args,**kwargs)
            return self.retrieved
        finally:
            self.search_ms.append((time.perf_counter()-start)*1000)


@contextmanager
def generation_timer(timings):
    original=agent.generated_answer
    def measured(*args,**kwargs):
        start=time.perf_counter()
        try:return original(*args,**kwargs)
        finally:timings.append((time.perf_counter()-start)*1000)
    # Used only in single-threaded quality/latency evaluation, never the API server.
    with patch.object(agent,'generated_answer',measured):
        yield


def measured_run(store,case,mode,model,ids):
    proxy=TimedStore(store)
    generation=[]
    kwargs={'mode':mode,'model':model}
    if case['category']=='csv_tool':
        kwargs.update(document_id=ids.get(case['document']),operation=case['operation'],column=case.get('column'))
    start=time.perf_counter()
    result,error={},None
    try:
        with generation_timer(generation):
            result=agent.run(proxy,case['question'],**kwargs)
    except Exception as exc:
        error=f'{type(exc).__name__}: {exc}'
    total_ms=(time.perf_counter()-start)*1000
    return result,error,{'total_ms':total_ms,'retrieval_ms':sum(proxy.search_ms) if proxy.search_ms else None,
                         'generation_ms':sum(generation) if generation else None},proxy.retrieved
