"""Offline runners for the bounded OBS-M7-UI-01 correction.

ROOT native LABEL | ROOT probe completed|pending|no-wait|old-click
ROOT historical after-transition | ROOT neighbors | ROOT compare | ROOT compare-neighbors
Historical mode archives the exact pre-fix app tree, leaving current sources
untouched. Comparisons replay the committed 1691-ID reference selections.
ROOT must be directly under /tmp and start with fridadev-obs-m7-ui-01-fix-.
"""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

REPO = Path(__file__).resolve().parents[3]
ROOT = Path(sys.argv[1]).resolve()
MODE = sys.argv[2]
ARG = sys.argv[3] if len(sys.argv) > 3 else MODE
BASE = 'be9e3a8a0bdbc246659ccde4f286a2a91e2cbab3'
ROOT_PREFIX = 'fridadev-obs-m7-ui-01-fix-'
assert ROOT.parent == Path('/tmp') and ROOT.name.startswith(ROOT_PREFIX)
ROOT.mkdir(exist_ok=True)
(ROOT / (MODE + '-program-run_obs_m7_ui_01_fix.py')).write_bytes(Path(__file__).read_bytes())
REFERENCE = REPO / 'app/docs/states/baselines/document-workshop/frida-v1-document-workshop-obs-m7-conc-01-fix-20261009.json'

if MODE in ('native', 'probe', 'historical'):
    repo = REPO
    if MODE == 'historical':
        repo = ROOT / 'base-checkout'
        assert not repo.exists(), 'historical archive already exists'
        repo.mkdir()
        archive = subprocess.check_output(['git', '-C', str(REPO), 'archive', '--format=tar', BASE, 'app'])
        with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
            assert all((p.name == 'app' or p.name.startswith('app/')) and '..' not in Path(p.name).parts for p in contents.getmembers())
            contents.extractall(repo, filter='data')
        # The nested readonly dependency bind needs a destination in the
        # readonly checkout mount. No dependency is copied or installed here.
        (repo / 'node_modules').mkdir()
    source = (repo / 'app/tests/support/run_obs_m7_ui_01.py').read_text()
    source = source.replace("PREFIX = 'fridadev-obs-m7-ui-01'", "PREFIX = 'fridadev-obs-m7-ui-01-fix'")
    root_guard = 'ROOT.name.startswith(PREFIX)'
    assert source.count(root_guard) == 1
    source = source.replace(root_guard, 'ROOT.name.startswith(' + repr(ROOT_PREFIX) + ')')
    if MODE == 'historical':
        anchor = 'def adapt(argv):'
        assert source.count(anchor) == 1
        source = source.replace(anchor, anchor + "\n    argv = [arg.replace('/opt/platform/fridadev:/workspace:ro', str(REPO) + ':/workspace:ro') for arg in argv]")
        anchor = "'-v', str(REPO) + ':/workspace:ro',"
        assert source.count(anchor) == 1
        dependencies = str(REPO / 'node_modules') + ':/workspace/node_modules:ro'
        source = source.replace(anchor, anchor + "\n            '-v', " + repr(dependencies) + ',')
    filename = repo / 'app/tests/support/run_obs_m7_ui_01.py'
    if MODE != 'historical':
        source = source.replace('probe_obs_m7_ui_01.js', 'probe_obs_m7_ui_01_fix.js')
        filename = REPO / 'app/tests/support/run_obs_m7_ui_01_fix.py'
    (ROOT / (ARG + '-owned-runner.py')).write_text(source)
    sys.argv = [str(filename), str(ROOT), 'baseline' if MODE == 'native' else 'probe', ARG]
    exec(compile(source, str(filename), 'exec'), {'__name__': '__main__', '__file__': str(filename)})
    raise AssertionError('native runner must exit explicitly')

assert MODE in ('neighbors', 'compare', 'compare-neighbors')
reference = json.loads(REFERENCE.read_text())
for source, name in [('frida-v1-document-workshop-m7-20261007.json', 'm7.json'),
                     ('frida-v1-document-workshop-p2-m8c-aud-02-20261009.json', 'aud02.json')]:
    (ROOT / name).write_bytes((REFERENCE.parent / source).read_bytes())
source = reference['proof_programs']['run.py']['source']
source = source.replace("PREFIX='fridadev-m7-conc-fix'", "PREFIX='fridadev-obs-m7-ui-01-fix-compare'")
source = source.replace("for old in ['/tmp/fridadev-m8c-aud02-20261009'", "for old in ['/tmp/fridadev-m7-conc-fix-20261009','/tmp/fridadev-m8c-aud02-20261009'")
source = source.replace("for old in ['fridadev-m7-proof'", "for old in ['fridadev-m7-conc-fix','fridadev-m7-proof'")
# Persist every line immediately rather than waiting for a subprocess to exit.
source = source.replace('p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)', 'p=stream(argv,ROOT/(label+".log"))')
(ROOT / (MODE + '-owned-comparison.py')).write_text(source)

def stream(argv, log):
    with log.open('wb') as output:
        p = subprocess.run(argv, stdout=output, stderr=subprocess.STDOUT)
    return subprocess.CompletedProcess(argv, p.returncode, log.read_bytes())

scope = {'__name__': 'owned_comparison', '__file__': str(ROOT / 'owned_comparison.py'), 'stream': stream}
exec(compile(source, str(ROOT / 'owned_comparison.py'), 'exec'), scope)
prefix = scope['PREFIX']
assert not subprocess.check_output(['docker', 'ps', '-a', '--filter', 'name=^/' + prefix + '-', '--format', '{{.Names}}']).strip()
record = scope['record']
created = []
exits = []

def tracked_record(label, argv):
    if argv[:2] == ['docker', 'run']:
        if '--name' not in argv:
            argv = argv[:2] + ['--name', prefix + '-' + label] + argv[2:]
        name = argv[argv.index('--name') + 1]
        assert not subprocess.check_output(['docker', 'ps', '-a', '--filter', 'name=^/' + name + '$', '--format', '{{.Names}}']).strip()
        if name not in created:
            created.append(name)
    return record(label, argv)

scope['record'] = tracked_record
try:
    if MODE in ('compare', 'compare-neighbors'):
        scope['setup']()
    else:
        for key in ('http-pg-start-good', 'native-pg-start'):
            argv = scope['adapt'](scope['M']['isolation']['setup_records'][key]['argv'])
            for arg in argv:
                if arg.endswith(':/var/run/postgresql'):
                    Path(arg.split(':')[0]).mkdir(exist_ok=True)
            assert tracked_record('neighbors-' + key, argv) == 0
            name = argv[argv.index('--name') + 1]
            for _ in range(100):
                if subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'm1proof'], capture_output=True).returncode == 0:
                    break
                scope['time'].sleep(.1)
            else:
                raise RuntimeError('owned_pg_not_ready')
    keys = (reference['comparisons']['after']['selections'] + ['neighbors70', 'exports-readers26'] if MODE == 'compare' else
            ['neighbors70', 'exports-readers26'] if MODE == 'compare-neighbors' else
            ['m7-native-http', 'browser-native-http', 'browser-simulated'])
    for key in keys:
        if key in ('browser-native-http', 'm7-native-http'):
            code = scope['native'](MODE, 'm6' if key == 'browser-native-http' else 'm7')
        else:
            label = 'compare' if MODE == 'compare-neighbors' else MODE
            code = tracked_record(label + '-' + key, scope['adapt'](reference['records']['after-' + key]['argv']))
        exits.append({'selection': key, 'exit': code})
finally:
    errors = []
    for name in reversed(created):
        try:
            def exists():
                return subprocess.check_output(['docker', 'ps', '-a', '--filter', 'name=^/' + name + '$', '--format', '{{.Names}}']).strip()
            if exists():
                assert record(MODE + '-stop-' + name, ['docker', 'stop', '-t', '10', name]) == 0
                if exists():
                    assert record(MODE + '-remove-' + name, ['docker', 'rm', name]) == 0
        except Exception as error:
            errors.append({'container': name, 'type': type(error).__name__})
    assert record(MODE + '-containers-absent', ['docker', 'ps', '-a', '--filter', 'name=^/' + prefix + '-', '--format', '{{.Names}}']) == 0
    assert not (ROOT / (MODE + '-containers-absent.log')).read_text().strip()
    (ROOT / (MODE + '-summary.json')).write_text(json.dumps({'exits': exits, 'cleanup_errors': errors}, indent=2) + '\n')
    assert not errors
sys.exit(1 if any(r['exit'] for r in exits) else 0)
