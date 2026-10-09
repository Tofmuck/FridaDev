"""Owned, offline OBS-M7-UI-01 runner. No installation or operator runtime.

Usage: python3 app/tests/support/run_obs_m7_ui_01.py ROOT baseline
       python3 app/tests/support/run_obs_m7_ui_01.py ROOT probe VARIANT
The root must be a new task-owned /tmp directory. Each run owns a fresh PG/HTTP
pair and removes it in finally, including on a failing browser/probe command.
"""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
ROOT = Path(sys.argv[1]).resolve()
MODE = sys.argv[2]
VARIANT = sys.argv[3] if len(sys.argv) > 3 else MODE
PREFIX = 'fridadev-obs-m7-ui-01'
assert ROOT.parent == Path('/tmp') and ROOT.name.startswith(PREFIX)
ROOT.mkdir(exist_ok=True)
RECORDS = ROOT / (VARIANT + '.records.json')
records = []
for source in (Path(__file__), Path(__file__).with_name('probe_obs_m7_ui_01.js')):
    if source.exists():
        (ROOT / (VARIANT + '-program-' + source.name)).write_bytes(source.read_bytes())


def record(label, argv):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    start = time.monotonic()
    log = ROOT / (VARIANT + '-' + label + '.log')
    # Persist TAP as it arrives, including a failure before later cases finish.
    with log.open('wb') as stream:
        proc = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
    raw = log.read_bytes()
    item = dict(label=label, argv=argv, started_utc=started,
                wall_seconds=round(time.monotonic() - start, 3), exit=proc.returncode,
                log_sha256=hashlib.sha256(raw).hexdigest(), log_bytes=len(raw))
    if '--test' in argv:
        output = raw.decode(errors='replace')
        item['test_names'] = re.findall(r'^# Subtest: (.*)$', output, re.M)
        for key in ('tests', 'pass', 'fail', 'skipped', 'cancelled'):
            match = re.search(r'^# ' + key + r' (\d+)$', output, re.M)
            item[key] = int(match[1]) if match else None
        item['unsuccessful_names'] = re.findall(r'^not ok \d+ - (.*)$', output, re.M)
    records.append(item)
    RECORDS.write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(item), flush=True)
    return proc.returncode


def checked(label, argv):
    if record(label, argv):
        raise RuntimeError('command_failed:' + label)


names = [PREFIX + '-http', PREFIX + '-pg', PREFIX + '-browser']
# Never remove a preexisting container on entry.
for name in names:
    found = subprocess.check_output(['docker', 'ps', '-a', '--filter',
                                     'name=^/' + name + '$', '--format', '{{.Names}}'])
    assert not found.strip(), 'owned name already exists'

old = json.loads((REPO / 'app/docs/states/baselines/document-workshop/frida-v1-document-workshop-m7-20261007.json').read_text())
socket = ROOT / 'native-pg-socket'
native = ROOT / 'native'
socket.mkdir(exist_ok=True)
native.mkdir(exist_ok=True)
marker = native / 'http-ready'
marker.unlink(missing_ok=True)


def adapt(argv):
    return [arg.replace('/tmp/fridadev-m7-proof-20261007', str(ROOT))
            .replace('fridadev-m7-proof-native', PREFIX) for arg in argv]


try:
    checked('pg-start', adapt(old['isolation']['setup_records']['native-pg-start']['argv']))
    start = time.monotonic()
    while subprocess.run(['docker', 'exec', names[1], 'pg_isready', '-U', 'm1proof'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        if time.monotonic() - start > 20:
            raise RuntimeError('owned_pg_readiness_timeout')
        time.sleep(.1)
    checked('http-start', adapt(old['isolation']['setup_records']['final-m7-native-v4-http-start']['argv']))
    start = time.monotonic()
    while not marker.exists():
        if time.monotonic() - start > 30:
            raise RuntimeError('owned_http_readiness_timeout')
        time.sleep(.05)
    checked('isolation', ['docker', 'inspect', '--format',
                         '{{.Name}} network={{.HostConfig.NetworkMode}} readonly={{.HostConfig.ReadonlyRootfs}} mounts={{json .Mounts}}', *names[:2]])
    argv = ['docker', 'run', '--rm', '--name', names[2], '--pull=never', '--network', 'container:' + names[0],
            '--read-only', '--tmpfs', '/tmp:rw,nosuid,nodev',
            '-v', str(REPO) + ':/workspace:ro',
            '-v', '/home/tof/.cache/ms-playwright:/proof/browsers:ro',
            '-v', str(ROOT) + ':/evidence:rw', '-w', '/workspace', '--entrypoint',
            '/usr/bin/env', 'mcr.microsoft.com/playwright:v1.54.0-jammy', '-i',
            'PATH=/usr/local/bin:/usr/bin:/bin', 'HOME=/tmp',
            'PLAYWRIGHT_BROWSERS_PATH=/proof/browsers', 'M7_HTTP_BASE=http://127.0.0.1:8767']
    if MODE == 'baseline':
        argv += ['node', '--test', '--test-concurrency=1',
                 'app/tests/integration/frontend_browser/test_frontend_browser_document_http_m7.js']
    elif MODE == 'probe':
        argv += ['OBS_VARIANT=' + VARIANT, 'node', '--test', '--test-concurrency=1',
                 'app/tests/support/probe_obs_m7_ui_01.js']
    else:
        raise ValueError('unknown mode')
    code = record('browser', argv)
finally:
    # Both are exclusively ours, established absent before creating either.
    cleanup_errors = []
    for name in (names[2], names[0], names[1]):
        try:
            exists = lambda: subprocess.check_output(['docker', 'ps', '-a', '--filter',
                                                      'name=^/' + name + '$', '--format', '{{.Names}}']).strip()
            if exists():
                record('stop-' + name, ['docker', 'stop', '-t', '10', name])
                # --rm may already have removed the browser on stop.
                if exists():
                    checked('remove-' + name, ['docker', 'rm', name])
        except Exception as error:
            cleanup_errors.append(dict(container=name, error=type(error).__name__))
    checked('containers-absent', ['docker', 'ps', '-a', '--filter',
                                 'name=^/' + PREFIX + '-', '--format', '{{.Names}}'])
    assert not (ROOT / (VARIANT + '-containers-absent.log')).read_text().strip(), 'owned container remains'
    if cleanup_errors:
        (ROOT / (VARIANT + '-cleanup-errors.json')).write_text(json.dumps(cleanup_errors) + '\n')
        if sys.exc_info()[0] is None:
            raise RuntimeError('owned_cleanup_failed')
sys.exit(code)
