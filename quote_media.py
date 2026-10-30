# 키 없이 쓸 수 있는 공개 이미지 공급원에서 글귀 카드의 배경을 고릅니다.
from math import ceil
import html
import re
import threading
import time
from urllib.parse import urlencode

from .quote_http import public_url
from .quotes import _lock, number
from .quote_weather import QUERIES, WeatherService

GRADIENT = {'provider': 'gradient', 'url': '', 'creator': '', 'source_url': '', 'license': '', 'license_url': ''}
PROVIDERS = ('korea', 'bing', 'wikimedia', 'artic', 'nasa', 'picsum')
# 한국 풍경: Wikimedia Commons 품질 사진에서 한국 명소·계절 풍경을 검색한다.
KOREA_QUERIES = ('South Korea landscape', 'Seoraksan', 'Jeju landscape', 'Gyeongbokgung', 'hanok village',
                 'Korea autumn', 'Korea temple', 'Bukhansan', 'Mudeungsan', 'Korea coast', 'Korea cherry blossom', 'Seoul night')
# 날씨 연동은 검색이 되는 두 곳에서 날씨에 맞는 사진을 찾는다.
WEATHER_PROVIDERS = ('commons_weather', 'artic_weather')
LABELS = {'korea': 'Wikimedia Commons · 한국 풍경', 'bing': 'Bing', 'wikimedia': 'Wikimedia Commons', 'artic': 'Art Institute of Chicago',
          'nasa': 'NASA APOD', 'picsum': 'Lorem Picsum', 'commons_weather': 'Wikimedia Commons · 날씨',
          'artic_weather': 'Art Institute of Chicago · 날씨', 'weather': 'Open-Meteo 날씨'}


class MediaService:
    def __init__(self, service):
        self.service, self.config = service, service.config
        self.weather = None

    def selected(self):
        # 1.0.x의 photo_provider(기본값 그라데이션)는 읽지 않는다. 남아 있으면 배경이 계속 꺼져 보였다.
        provider = self.config.get('background_source', 'weather')
        return provider if provider in PROVIDERS + ('weather', 'random', 'gradient') else 'weather'

    def status(self):
        now = self.service.clock()
        result = []
        for provider in PROVIDERS + WEATHER_PROVIDERS + ('weather',):
            state = self.service.state(provider)
            result.append({'id': provider, 'name': LABELS[provider], 'calls': state['calls'],
                           'displayed': state['displayed'], 'failures': state['failures'], 'last_code': state['last_code'],
                           'status': 'cooldown' if state['until'] > now else 'healthy' if state['displayed'] else 'unknown'})
        return {'selected': self.selected(), 'providers': result}

    def bing_background(self):
        host = 'www.bing.com'
        data = self.service.cached('bing:archive', 3600, lambda: self.service.fetch(
            'https://' + host + '/HPImageArchive.aspx?' + urlencode({'format': 'js', 'idx': 0, 'n': 8, 'mkt': 'ko-KR'}),
            hosts={host}))
        images = [item for item in data.get('images', []) if isinstance(item, dict)
                  and isinstance(item.get('urlbase'), str) and item['urlbase'].startswith('/th?id=')]
        photo = self.service.rng.choice(images)
        image = public_url('https://' + host + photo['urlbase'] + '_1920x1080.jpg', {host})
        source = public_url(photo.get('copyrightlink'), {host}) or 'https://www.bing.com/'
        # copyright는 "설명 (© 작가/에이전시)" 형식이다.
        notice = str(photo.get('copyright') or '')
        match = re.search(r'\(©\s*([^)]+)\)\s*$', notice)
        if not image:
            return {**GRADIENT, 'reason': 'invalid-photo'}
        return {'provider': 'bing', 'provider_name': 'Bing 오늘의 이미지', 'url': image, 'source_url': source,
                'title': str(photo.get('title') or notice.split(' (©')[0])[:500],
                'creator': (match.group(1) if match else 'Microsoft Bing')[:200],
                'license': '© 각 저작권자 · Bing 배경화면 개인 이용', 'license_url': 'https://www.bing.com/'}

    def wikimedia_background(self):
        host = 'commons.wikimedia.org'
        now = self.service.clock()
        # 오늘의 사진은 하루 한 장이라 최근 7일 중에서 고른다. 세로 사진은 건너뛴다.
        for days in self.service.rng.sample(range(7), 3):
            day = time.strftime('%Y-%m-%d', time.gmtime(now - days * 86400))
            params = urlencode({'action': 'query', 'format': 'json', 'formatversion': 2, 'generator': 'images',
                                'titles': 'Template:Potd/' + day, 'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata',
                                'iiurlwidth': 1920, 'iiextmetadatafilter': 'Artist|LicenseShortName|LicenseUrl|ObjectName'})
            data = self.service.cached('wikimedia:' + day, 86400, lambda: self.service.fetch(
                f'https://{host}/w/api.php?' + params, hosts={host}, timeout=8))
            pages = ((data.get('query') or {}).get('pages') or []) if isinstance(data, dict) else []
            photo = self._commons_photo(pages, 'Wikimedia Commons 오늘의 사진')
            if photo:
                return photo
        return {**GRADIENT, 'reason': 'invalid-photo'}

    def _commons_photo(self, pages, provider_name):
        host = 'commons.wikimedia.org'
        for page in pages:
            info = (page.get('imageinfo') or [None])[0] if isinstance(page, dict) else None
            if not isinstance(info, dict) or info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
                continue
            width, height = info.get('width'), info.get('height')
            if type(width) is not int or type(height) is not int or width < height:
                continue
            image = public_url(info.get('thumburl') or info.get('url'), {'upload.wikimedia.org'})
            source = public_url(info.get('descriptionurl'), {host})
            if not image or not source:
                continue
            meta = info.get('extmetadata') if isinstance(info.get('extmetadata'), dict) else {}
            value = lambda key: ' '.join(html.unescape(re.sub(r'<[^>]*>', ' ', str((meta.get(key) or {}).get('value') or ''))).split())
            return {'provider': 'wikimedia', 'provider_name': provider_name, 'url': image,
                    'source_url': source, 'title': (value('ObjectName') or str(page.get('title') or ''))[:500],
                    'creator': (value('Artist') or '작가 미상')[:200],
                    'license': (value('LicenseShortName') or 'Wikimedia Commons')[:100],
                    'license_url': public_url(value('LicenseUrl')) or source}
        return None

    def _commons_search(self, query, offsets=(0, 30, 60)):
        host = 'commons.wikimedia.org'
        offset = self.service.rng.choice(offsets)
        # 품질 사진(Quality images) 중 가로 1600px 넘는 사진만 검색한다.
        params = urlencode({'action': 'query', 'format': 'json', 'formatversion': 2, 'generator': 'search',
                            'gsrsearch': f'{query} filetype:bitmap filew:>1600 incategory:"Quality images"',
                            'gsrnamespace': 6, 'gsrlimit': 30, 'gsroffset': offset,
                            'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': 1920,
                            'iiextmetadatafilter': 'Artist|LicenseShortName|LicenseUrl|ObjectName'})
        data = self.service.cached(f'commons_search:{query}:{offset}', 6 * 3600, lambda: self.service.fetch(
            f'https://{host}/w/api.php?' + params, hosts={host}, timeout=8))
        pages = list(((data.get('query') or {}).get('pages') or []) if isinstance(data, dict) else [])
        self.service.rng.shuffle(pages)
        return pages

    def korea_first(self):
        return self.config.get('korea_first', True) in (True, 1, '1', 'true', 'on')

    def commons_weather_background(self):
        query = QUERIES[self.weather['key']][0]
        label = self.weather['label']
        if self.korea_first():
            # 한국 사진을 먼저 찾고, 해당 날씨의 한국 사진이 없으면 전 세계 사진으로 넓힌다.
            photo = self._commons_photo(self._commons_search(query + ' Korea', (0,)), f'Wikimedia Commons · 한국 {label} 사진')
            if photo:
                return photo
        return self._commons_photo(self._commons_search(query), f'Wikimedia Commons · {label} 사진') or {**GRADIENT, 'reason': 'invalid-photo'}

    def korea_background(self):
        for query in self.service.rng.sample(KOREA_QUERIES, 2):
            photo = self._commons_photo(self._commons_search(query, (0, 30)), 'Wikimedia Commons · 한국 풍경')
            if photo:
                return photo
        return {**GRADIENT, 'reason': 'invalid-photo'}

    def artic_weather_background(self):
        photo = self.artic_background(QUERIES[self.weather['key']][1], 'artic_weather')
        return {**photo, 'provider_name': f"Art Institute of Chicago · {self.weather['label']} 명화"}

    def artic_background(self, query='landscape', cache='artic'):
        host = 'api.artic.edu'
        page = self.service.rng.randint(1, 5 if query == 'landscape' else 2)
        params = urlencode({'q': query, 'query[term][is_public_domain]': 'true', 'limit': 50, 'page': page,
                            'fields': 'id,title,artist_display,image_id,thumbnail'})
        data = self.service.cached(f'{cache}:{query}:{page}', 3600, lambda: self.service.fetch(
            f'https://{host}/api/v1/artworks/search?' + params, hosts={host}, timeout=8))
        iiif = public_url((data.get('config') or {}).get('iiif_url'), {'www.artic.edu'}) or 'https://www.artic.edu/iiif/2'
        works = [item for item in data.get('data', []) if isinstance(item, dict) and type(item.get('id')) is int
                 and isinstance(item.get('image_id'), str) and re.fullmatch(r'[0-9a-f-]{36}', item['image_id'])
                 and isinstance(item.get('thumbnail'), dict)
                 and (item['thumbnail'].get('width') or 0) > (item['thumbnail'].get('height') or 0)]
        work = self.service.rng.choice(works)
        return {'provider': 'artic', 'provider_name': 'Art Institute of Chicago', 'creator_label': '작품 작가',
                'url': f"{iiif}/{work['image_id']}/full/1686,/0/default.jpg",
                'source_url': f"https://www.artic.edu/artworks/{work['id']}",
                'title': str(work.get('title') or '')[:500],
                'creator': ' '.join(str(work.get('artist_display') or '작가 미상').split())[:200],
                'license': 'CC0', 'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/'}

    def nasa_background(self):
        host = 'api.nasa.gov'
        # DEMO_KEY는 가입 없이 쓰는 공용 키라 IP당 시간 30회 한도가 있어 묶음으로 받아 재사용한다.
        data = self.service.cached('nasa:random', 3600, lambda: self.service.fetch(
            f'https://{host}/planetary/apod?' + urlencode({'api_key': 'DEMO_KEY', 'count': 10, 'thumbs': 'false'}),
            hosts={host}, timeout=10))
        pool = [item for item in data if isinstance(item, dict) and item.get('media_type') == 'image'
                and public_url(item.get('url'), {'apod.nasa.gov'})] if isinstance(data, list) else []
        photo = self.service.rng.choice(pool)
        day = str(photo.get('date') or '')
        source = f'https://apod.nasa.gov/apod/ap{day[2:4]}{day[5:7]}{day[8:10]}.html' if re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) else 'https://apod.nasa.gov/'
        owner = ' '.join(str(photo.get('copyright') or '').split())
        return {'provider': 'nasa', 'provider_name': 'NASA 오늘의 천체사진(APOD)', 'url': photo['url'],
                'source_url': source, 'title': str(photo.get('title') or '')[:500],
                'creator': (owner or 'NASA')[:200],
                'license': ('© ' + owner) if owner else 'Public Domain (NASA)',
                'license_url': 'https://apod.nasa.gov/apod/lib/about_apod.html'}

    def picsum_background(self):
        host = 'picsum.photos'
        page = self.service.rng.randint(1, 10)
        data = self.service.cached(f'picsum:{page}', 86400, lambda: self.service.fetch(
            f'https://{host}/v2/list?' + urlencode({'page': page, 'limit': 100}), hosts={host}))
        pool = [item for item in data if isinstance(item, dict) and str(item.get('id', '')).isdigit()
                and (item.get('width') or 0) > (item.get('height') or 0)] if isinstance(data, list) else []
        photo = self.service.rng.choice(pool)
        return {'provider': 'picsum', 'provider_name': 'Lorem Picsum (Unsplash 사진)',
                'url': f"https://{host}/id/{photo['id']}/1920/1080",
                'source_url': public_url(photo.get('url'), {'unsplash.com'}) or 'https://picsum.photos/',
                'creator': str(photo.get('author') or 'Unsplash 작가')[:200],
                'license': 'Unsplash License', 'license_url': 'https://unsplash.com/license'}

    def background(self, tags, *, force=False):
        selected = self.selected()
        if selected == 'gradient':
            return {**GRADIENT, 'reason': 'selected-gradient', 'refresh_after': 0}
        with _lock:
            selection_lock = self.service.runtime['cache_locks'].setdefault('photo-selection', threading.RLock())
        with selection_lock:
            now = self.service.clock()
            current = self.service.runtime.get('selected_background')
            weather_key = ''
            if selected == 'weather':
                self.weather = WeatherService(self.service).current()
                weather_key = self.weather['key'] if self.weather else 'unavailable'
            # 날씨가 바뀌면 변경 주기를 기다리지 않고 새 사진을 고른다.
            if current and (current['selected'] != selected or current.get('weather_key', '') != weather_key):
                current = None
            previous = current['photo'] if current else GRADIENT
            if not force and current and current['expires'] > now:
                return {**previous, 'refresh_after': max(1, ceil(current['expires'] - now))}
            ready = [provider for provider in PROVIDERS if self.service.state(provider)['until'] <= now]
            self.service.rng.shuffle(ready)
            if selected == 'weather' and self.weather:
                # Wikimedia 사진을 먼저 찾고, 없으면 명화, 그래도 없으면 일반 무작위 배경으로 넘어간다.
                candidates = [*WEATHER_PROVIDERS, *ready[:2]]
            elif selected in ('weather', 'random'):
                candidates = ready[:3]
            else:
                candidates = [selected]
            if not candidates:
                return {**previous, 'reason': 'cooldown', 'refresh_after': 60}
            photo = {**GRADIENT, 'reason': 'cooldown'}
            # 실패한 공급원을 건너뛰고 다음 공급원을 시도한다.
            for provider in candidates:
                photo = self._select(provider)
                if photo.get('url'):
                    break
            now = self.service.clock()
            if photo.get('url'):
                expires = now + number(self.config.get('photo_refresh_hours'), 3, 1, 24) * 3600
            else:
                expires = now + 60
                photo = {**previous, 'reason': photo.get('reason', 'request-failed')}
            self.service.runtime['selected_background'] = {'selected': selected, 'photo': dict(photo), 'expires': expires,
                                                           'weather_key': weather_key}
            return {**photo, 'refresh_after': max(1, ceil(expires - now))}

    def _select(self, provider):
        state = self.service.state(provider)
        if state['until'] > self.service.clock():
            return {**GRADIENT, 'reason': 'cooldown'}
        try:
            state['calls'] += 1
            photo = getattr(self, provider + '_background')()
            if photo.get('url'):
                state['failures'] = 0
                state['displayed'] += 1
            return photo
        except (ValueError, OSError, TypeError, AttributeError, KeyError, IndexError) as error:
            state['failures'] += 1
            state['until'] = self.service.clock() + max(60 if state['failures'] < 3 else 600, getattr(error, 'retry_after', 0))
            state['last_code'] = getattr(error, 'status', 0)
            return {**GRADIENT, 'reason': 'request-failed'}
