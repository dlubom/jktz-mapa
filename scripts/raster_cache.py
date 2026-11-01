"""Optional, content-bound WebP cache. Metadata is always rebuilt by the importer."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def environment():
    from osgeo import _gdal, gdal, osr
    # Resolve the encoder through GDAL's loaded extension and its dependencies,
    # rather than a potentially different libwebp found on the search path.
    encoder = ctypes.CDLL(_gdal.__file__).WebPGetEncoderVersion
    encoder.restype = ctypes.c_int
    # apt security/build revisions can change native code without changing the
    # upstream version reported by GDAL or libwebp.
    packages = []
    if sys.platform == 'linux' and shutil.which('dpkg-query'):
        result = subprocess.run(['dpkg-query', '-W', '-f=${binary:Package}=${Version}\n',
                                 'libgdal*', 'libproj*', 'libwebp*', 'proj-data'],
                                capture_output=True, text=True, check=False)
        packages = sorted(result.stdout.splitlines())
    return {'python': sys.version, 'platform': platform.platform(), 'packages': packages,
            'gdal': gdal.VersionInfo('--version'), 'build': gdal.VersionInfo('BUILD_INFO'),
            'proj': [osr.GetPROJVersionMajor(), osr.GetPROJVersionMinor(), osr.GetPROJVersionMicro()],
            'webp': encoder(), 'image': os.environ.get('ImageVersion', ''), 'config': configuration(),
            'webpOptions': gdal.GetDriverByName('WEBP').GetMetadataItem('DMD_CREATIONOPTIONLIST')}


def configuration():
    from osgeo import gdal
    names = set(gdal.GetConfigOptions())
    prefixes = ('GDAL_', 'CPL_', 'PROJ_', 'VSI_', 'GTIFF_', 'GEOTIFF_', 'TIFF_', 'OSR_', 'OGR_')
    names.update(name for name in os.environ if name.startswith(prefixes))
    names.update(('GDAL_PAM_ENABLED', 'CHECK_WITH_INVERT_PROJ', 'USE_RRD', 'CENTER_LONG'))
    # GetConfigOptions alone excludes environment variables. GetConfigOption
    # resolves the effective global/thread-local/environment value and gdalrc.
    return {name: gdal.GetConfigOption(name) for name in sorted(names)
            if gdal.GetConfigOption(name) is not None}


def key(source, profile, renderer):
    identity = {'schema': 1, 'profile': profile,
                'assets': [{k: asset[k] for k in ('name', 'size', 'digest')} for asset in source['assets']],
                'code': [sha(Path(renderer)), sha(Path(__file__))], 'environment': environment()}
    raw = json.dumps(identity, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return 'rasters-v1-' + hashlib.sha256(raw).hexdigest()


def expected_files(plans):
    pam = configuration().get('GDAL_PAM_ENABLED', 'YES').upper() not in ('NO', 'FALSE', 'OFF', '0')
    names = set()
    for plan in plans:
        names.add(f'{plan["id"]}/preview.webp')
        # GDAL persists preview georeferencing in a PAM sidecar. Preserve it too.
        if pam:
            names.add(f'{plan["id"]}/preview.webp.aux.xml')
        for level in plan['levels']:
            names.update(f'{plan["id"]}/tiles/{level["level"]}/{x}-{y}.webp'
                         for y in range(level['rows']) for x in range(level['columns']))
    return names


def unique_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('Duplicate cache manifest key')
        result[name] = value
    return result


def inventory(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Invalid cache directory')
    result = {}
    for path in root.rglob('*'):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('Unsupported cache entry')
        if path.is_file():
            size = path.stat().st_size
            if size > 850_000_000:
                raise ValueError('Oversized cache entry')
            result[path.relative_to(root).as_posix()] = {'bytes': size, 'sha256': sha(path)}
    return result


def restore(directory, cache_key, expected, target):
    """Validate everything before copying; any cache defect is an ordinary miss."""
    try:
        if directory.is_symlink() or not directory.is_dir():
            return False
        if {p.name for p in directory.iterdir()} != {'manifest.json', 'images'}:
            return False
        manifest_path = directory / 'manifest.json'
        if manifest_path.is_symlink() or manifest_path.stat().st_size > 16_000_000:
            return False
        manifest = json.loads(manifest_path.read_bytes(), object_pairs_hook=unique_pairs)
        if not isinstance(manifest, dict) or manifest.get('schema') != 1 or manifest.get('key') != cache_key:
            return False
        files = manifest.get('files')
        if not isinstance(files, dict) or set(files) != expected:
            return False
        # Only paths independently derived from validated source geometry are used.
        if inventory(directory / 'images') != files:
            return False
    except (OSError, ValueError, TypeError, RecursionError):
        return False
    for name in sorted(expected):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(directory / 'images' / name, path)
    return True


def save(directory, cache_key, expected, source):
    """Replace a local disposable cache only after writing a complete new entry."""
    directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='raster-cache-', dir=directory.parent))
    try:
        (temporary / 'images').mkdir()
        for name in sorted(expected):
            target = temporary / 'images' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        manifest = {'schema': 1, 'key': cache_key, 'files': inventory(temporary / 'images')}
        if set(manifest['files']) != expected:
            raise ValueError('Incomplete raster cache')
        (temporary / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n')
        if directory.is_symlink() or directory.is_file():
            directory.unlink()
        elif directory.exists():
            shutil.rmtree(directory)
        temporary.replace(directory)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
