"""Manifest, language files and .mcpack packaging."""
import json
import os
import zipfile

NAME = 'Terra Lucida'
DESCRIPTION = ('Naturalistic high-fidelity textures, skies, water and atmosphere for the standard renderer. '
               'No Vibrant Visuals or ray tracing needed. Pick 32x / 64x / 128x in pack settings.')
UUID_HEADER = '525e84a5-63cf-46f4-8737-1472aadf097b'
UUID_MODULE = '93a6a832-26b3-4ceb-948b-84a9f5d94612'
MIN_ENGINE = '1.26.50'
# Manifest v3 subpacks: {folder_name, name, memory_performance_tier 0..5} (Mojang packaging schema 3.0.0).
# Devices below a subpack's tier can't select it; the highest allowed tier is the default.
SUBPACKS = [
    {'folder_name': 'lite', 'name': 'Lite 32x - older phones', 'memory_performance_tier': 0},
    {'folder_name': 'balanced', 'name': 'Balanced 64x - most phones', 'memory_performance_tier': 2},
    {'folder_name': 'ultra', 'name': 'Ultra 128x - high-end devices', 'memory_performance_tier': 4},
]
FIXED_TIME = (2026, 10, 1, 0, 0, 0)


def manifest(version):
    return {
        'format_version': 3,
        'header': {
            'name': 'pack.name',
            'description': 'pack.description',
            'uuid': UUID_HEADER,
            'version': version,
            'min_engine_version': MIN_ENGINE,
        },
        'modules': [{'type': 'resources', 'uuid': UUID_MODULE, 'version': version}],
        'subpacks': SUBPACKS,
        'metadata': {'authors': ['Terra Lucida contributors']},
    }


def write_pack_meta(pack_dir, version):
    def wj(rel, data):
        p = os.path.join(pack_dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')
    wj('manifest.json', manifest(version))
    wj('texts/languages.json', ['en_US'])
    with open(os.path.join(pack_dir, 'texts', 'en_US.lang'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'pack.name={NAME}\npack.description={DESCRIPTION}\n')
    keep = os.path.join(pack_dir, 'subpacks', 'balanced', 'balanced.txt')
    os.makedirs(os.path.dirname(keep), exist_ok=True)
    with open(keep, 'w', encoding='utf-8', newline='\n') as f:
        f.write('Balanced uses the 64x textures in the pack root.\n')


def package(pack_dir, dist, version):
    os.makedirs(dist, exist_ok=True)
    out = os.path.join(dist, f'Terra_Lucida_v{version}.mcpack')
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for base, dirs, files in os.walk(pack_dir):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(base, name)
                rel = os.path.relpath(full, pack_dir).replace(os.sep, '/')
                info = zipfile.ZipInfo(rel, date_time=FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(full, 'rb') as fh:
                    zf.writestr(info, fh.read())
    print(f'[build] packaged {os.path.relpath(out, os.path.dirname(dist))} '
          f'({os.path.getsize(out) / 1e6:.1f} MB)')
    return out
