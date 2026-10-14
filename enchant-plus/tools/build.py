#!/usr/bin/env python3
"""Package Enchant+ into dist/Enchant_Plus_v<version>.mcaddon (behavior pack + resource pack).

The archive is deterministic: files are sorted and stamped with a fixed date, so the same sources
always give the same bytes.

Usage:  python3 tools/build.py [--check] [--samples DIR]
  --check     first run the type check, the headless tests and the validator; stop on any failure
"""
import argparse
import json
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = ('Enchant_Table_BP', 'Enchant_Table_RP')
FIXED_TIME = (2026, 10, 14, 0, 0, 0)


def run(cmd):
    print('[build] $', ' '.join(cmd))
    if subprocess.run(cmd, cwd=ROOT).returncode != 0:
        sys.exit(f'[build] failed: {" ".join(cmd)}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--samples', default=os.environ.get('BEDROCK_SAMPLES'))
    args = ap.parse_args()
    if args.check:
        tsc = os.path.join(os.path.dirname(ROOT), 'node_modules', '.bin', 'tsc')
        run([tsc, '-p', 'tsconfig.json'])
        run(['node', 'tools/tests/test_enchant.mjs'])
        run([sys.executable, 'tools/validate.py'] + (['--samples', args.samples] if args.samples else []))

    version = '.'.join(map(str, json.load(open(os.path.join(ROOT, 'packs', PACKS[0], 'manifest.json')))['header']['version']))
    out = os.path.join(ROOT, 'dist', f'Enchant_Plus_v{version}.mcaddon')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    count = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for pack in PACKS:
            base = os.path.join(ROOT, 'packs', pack)
            for folder, dirs, names in os.walk(base):
                dirs.sort()
                for name in sorted(names):
                    full = os.path.join(folder, name)
                    arc = os.path.join(pack, os.path.relpath(full, base)).replace(os.sep, '/')
                    info = zipfile.ZipInfo(arc, date_time=FIXED_TIME)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    with open(full, 'rb') as f:
                        zf.writestr(info, f.read())
                    count += 1
    print(f'[build] {os.path.relpath(out, ROOT)}: {count} files, {os.path.getsize(out) / 1024:.0f} KiB')


if __name__ == '__main__':
    main()
