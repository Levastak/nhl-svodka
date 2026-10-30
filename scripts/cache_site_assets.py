"""Bundle NHL logos and roster portraits with Pages; visitors need only our domain."""
import concurrent.futures
import json
from pathlib import Path
import re
import shutil
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache' / 'nhl-assets'
DEST = ROOT / 'site' / 'assets'
ORIGIN = 'https://assets.nhle.com/'


def asset_paths(data):
    core = (ROOT / 'site' / 'core.js').read_text(encoding='utf-8')
    teams = set(re.findall(r'\b([A-Z]{3}):\[', core.split('const COLORS=', 1)[1].split(';', 1)[0]))
    paths = {f'logos/nhl/svg/{team}_{theme}.svg' for team in teams for theme in ('light', 'dark')}
    for row in data.get('standings', []):
        url = urllib.parse.urlsplit(row.get('logo') or '')
        if url.netloc == 'assets.nhle.com' and re.fullmatch(r'/logos/nhl/svg/[A-Za-z0-9_]+\.svg', url.path):
            paths.add(url.path.lstrip('/'))
            paths.add(re.sub(r'_light\.svg$', '_dark.svg', url.path.lstrip('/')))
    # All roster entries, including players absent from today's leaderboard.
    paths.update(f'mugs/nhl/{head}.png' for head in data.get('heads', {}).values()
                 if re.fullmatch(r'\d{8}/[A-Z]{3}/\d+', str(head)))
    return sorted(paths)


def valid_image(data, suffix):
    return data.startswith(b'\x89PNG\r\n\x1a\n') if suffix == '.png' else b'<svg' in data[:2000]


def bundle_one(relative):
    cached = CACHE / relative
    target = DEST / relative
    if not cached.exists() or not valid_image(cached.read_bytes(), cached.suffix):
        urls = [ORIGIN + relative]
        if relative.startswith('mugs/'):
            urls.append(ORIGIN + 'mugs/nhl/latest/' + Path(relative).name)
        error = None
        for url in urls:
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (NHL-STATS.RU)'})
                with urllib.request.urlopen(request, timeout=20) as response:
                    data = response.read()
                if not valid_image(data, cached.suffix):
                    raise ValueError('not an image')
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(data)
                error = None
                break
            except Exception as ex:
                error = f'{relative}: {ex}'
        if error:
            return error
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cached, target)
    return None


def main():
    data = json.loads((ROOT / 'site' / 'data.json').read_text(encoding='utf-8'))
    paths = asset_paths(data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        errors = [error for error in pool.map(bundle_one, paths) if error]
    print(f'Site assets: {len(paths) - len(errors)}/{len(paths)} bundled')
    for error in errors:
        print('WARNING:', error)
    # A partial upstream outage must not publish a site stripped of all branding.
    if len(errors) > max(5, len(paths) // 20) or any(error.startswith('logos/') for error in errors):
        raise RuntimeError('NHL asset download incomplete; keeping the previous Pages deployment')


if __name__ == '__main__':
    main()
