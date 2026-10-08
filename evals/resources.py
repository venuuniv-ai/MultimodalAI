"""macOS/Linux process sampling via ps; no optional benchmark dependency."""
import os
import platform
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .metrics import distribution, mean


def command(args):
    try:
        return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=3).strip()
    except (OSError,subprocess.SubprocessError):
        return None


def cpu_seconds(text):
    days, clock = (text.split('-',1) if '-' in text else ('0',text))
    total = 0.
    for item in clock.split(':'):
        total = total*60 + float(item)
    return int(days)*86400 + total


def process_snapshot():
    output = command(['ps','-axo','pid=,ppid=,rss=,time=,comm='])
    if output is None:
        return {}
    result = {}
    for line in output.splitlines():
        parts = line.split(None,4)
        if len(parts)<5:
            continue
        try:
            pid,parent,rss = map(int,parts[:3])
            result[pid] = dict(parent=parent,rss_bytes=rss*1024,cpu_seconds=cpu_seconds(parts[3]),executable=Path(parts[4]).name)
        except ValueError:
            continue
    return result


def descendants(snapshot, roots):
    found = set(roots)
    while True:
        more = {pid for pid,p in snapshot.items() if p['parent'] in found}
        if more <= found:
            return found & snapshot.keys()
        found |= more


class ResourceSampler:
    def __init__(self, interval=.1):
        self.interval=interval
        self.stop=threading.Event()
        self.rows=[]
        self.phase='setup'
        self.start=time.perf_counter()
        self.thread=threading.Thread(target=self._loop,daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def _loop(self):
        previous={}
        previous_time=time.perf_counter()
        while not self.stop.is_set():
            snapshot=process_snapshot()
            now=time.perf_counter()
            groups={'benchmark_tree':descendants(snapshot,{os.getpid()}),
                    'ollama_processes':descendants(snapshot,{pid for pid,p in snapshot.items() if p['executable']=='ollama'})}
            row={'elapsed_s':now-self.start,'phase':self.phase}
            for name,pids in groups.items():
                cpu=sum(max(0,snapshot[pid]['cpu_seconds']-previous[pid]['cpu_seconds']) for pid in pids if pid in previous)
                row[name]={'rss_bytes':sum(snapshot[pid]['rss_bytes'] for pid in pids),
                           'cpu_percent_one_core':100*cpu/(now-previous_time) if previous else None,
                           'pids':sorted(pids)}
            self.rows.append(row)
            previous,previous_time=snapshot,now
            self.stop.wait(self.interval)

    def __exit__(self,*args):
        self.stop.set()
        self.thread.join(timeout=4)

    def report(self):
        def summarize(rows):
            return {name:{'rss_bytes':distribution(r[name]['rss_bytes'] for r in rows),
                          'cpu_percent_one_core':distribution(r[name]['cpu_percent_one_core'] for r in rows if r[name]['cpu_percent_one_core'] is not None)} for name in ['benchmark_tree','ollama_processes']}
        return {'interval_seconds':self.interval,'samples':len(self.rows),'overall':summarize(self.rows),
                'by_phase':{phase:summarize([r for r in self.rows if r['phase']==phase]) for phase in sorted({r['phase'] for r in self.rows})},
                'raw':self.rows,
                'limitations':'Sampled sum of RSS (shared pages can be counted twice), not exact peak allocation; CPU time deltas use ps resolution and a one-core baseline (100% = one CPU core). Existing Ollama processes may include unrelated activity; benchmark descendants include sampler subprocess overhead. Not system-wide CPU or GPU counters.'}


def environment():
    import importlib.metadata
    import sys
    from datetime import datetime
    from zoneinfo import ZoneInfo
    versions={}
    for package in ['numpy','scikit-learn','pypdf','pillow','pytesseract','httpx','pytest','fastapi','uvicorn']:
        try:versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:versions[package]=None
    return dict(recorded_at=datetime.now(ZoneInfo('America/New_York')).isoformat(),timezone='America/New_York',
                platform=platform.platform(),python=sys.version,processor=command(['sysctl','-n','machdep.cpu.brand_string']) if platform.system()=='Darwin' else platform.processor(),
                ram_bytes=int(command(['sysctl','-n','hw.memsize']) or 0) if platform.system()=='Darwin' else None,
                cpu_count=os.cpu_count(),packages=versions,tesseract=command(['tesseract','--version']),ollama=command(['ollama','--version']),
                gpu_utilization=None,vram_bytes=None,gpu_note='No GPU utilization/VRAM counters collected. Apple unified memory is not dedicated VRAM; NVIDIA tooling unavailable.' if not shutil.which('nvidia-smi') else 'GPU counters not collected by this harness.',
                power_and_background_load='Not controlled; local interactive laptop, no sustained-load or thermal guarantees.')
