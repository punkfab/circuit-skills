#!/usr/bin/env python3
"""Local Freerouting/FastRoute DSN→SES, bounded runtime and live viewer status."""
import argparse, json, os, re, shutil, subprocess, time
from pathlib import Path

def command(backend, executable, dsn, ses, passes, seconds, report):
    args = [executable, '-de', str(dsn), '-do', str(ses), '-mp', str(passes)]
    return args + ([f'--max-time={seconds}', f'--report={report}'] if backend == 'fastroute' else ['-oit','0'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dsn',type=Path); p.add_argument('-o','--output',type=Path,required=True)
    p.add_argument('--backend',choices=['freerouting','fastroute'],default=os.getenv('ROUTER','freerouting'))
    p.add_argument('--executable'); p.add_argument('--board',type=Path)
    p.add_argument('--max-time',type=int,default=int(os.getenv('MAXT','120')))
    p.add_argument('--max-passes',type=int,default=int(os.getenv('MP','12')))
    a=p.parse_args()
    if a.max_time<1 or a.max_passes<1: p.error('time and passes must be positive')
    dsn,ses=a.dsn.resolve(),a.output.resolve()
    if not dsn.is_file(): p.error(f'DSN does not exist: {dsn}')
    if ses.exists(): p.error(f'Output exists; choose a fresh candidate: {ses}')
    exe=a.executable or os.getenv('FASTROUTE_BIN' if a.backend=='fastroute' else 'FREERT') or shutil.which('fastroute' if a.backend=='fastroute' else 'freert')
    if not exe: p.error(f'{a.backend} missing; set --executable')
    ses.parent.mkdir(parents=True,exist_ok=True)
    log,report=Path(str(ses)+'.log'),Path(str(ses)+'.report.json')
    status=Path(str(a.board.resolve())+'.routing.json') if a.board else None
    started=time.monotonic()
    def publish(state,message):
        unrouted = None
        if report.is_file():
            try: unrouted = json.loads(report.read_text()).get('stats',{}).get('unrouted')
            except (OSError, ValueError): pass
        if unrouted is None and log.is_file():
            with log.open('rb') as tail:
                tail.seek(max(0,log.stat().st_size-8192)); samples=re.findall(rb'(\d+) unrouted',tail.read())
            if samples: unrouted=int(samples[-1])
        if unrouted is not None: message += f'; router reports {unrouted} unrouted'
        data=dict(backend=a.backend,state=state,message=message,elapsed_s=round(time.monotonic()-started,1),output=str(ses),log=str(log),report=str(report))
        if status:
            tmp=status.with_name(status.name+'.tmp'); tmp.write_text(json.dumps(data)+'\n'); tmp.replace(status)
        print(f'{a.backend}: {state} · {message}',flush=True)
    env=os.environ.copy()
    if a.backend=='freerouting': env['JAVA_TOOL_OPTIONS']=env.get('JAVA_TOOL_OPTIONS','')+' -Djava.awt.headless=true'
    publish('running','routing candidate; KiCad verification pending')
    try:
        with log.open('w') as out:
            proc=subprocess.Popen(command(a.backend,exe,dsn,ses,a.max_passes,a.max_time,report),stdout=out,stderr=subprocess.STDOUT,env=env)
            try:
                while proc.poll() is None:
                    if time.monotonic()-started>a.max_time+10:
                        proc.terminate()
                        try: proc.wait(timeout=5)
                        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                        break
                    time.sleep(1); publish('running',f'{int(time.monotonic()-started)}s elapsed; KiCad verification pending')
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        if ses.is_file() and ses.stat().st_size:
            if a.backend=='freerouting': ses.write_text(ses.read_text().replace('(host_version )','(host_version "freerouting")'))
            publish('candidate',f'SES saved (exit {proc.returncode}); import, refill zones and run KiCad DRC'); return 0
        publish('failed',f'No SES saved (exit {proc.returncode}); see log'); return 1
    except Exception as e: publish('failed',str(e)); return 1
if __name__=='__main__': raise SystemExit(main())
