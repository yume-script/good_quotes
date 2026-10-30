# 키 없이 쓸 수 있는 공개 이미지 공급원에서 글귀 카드의 배경을 고릅니다.
from math import ceil
import re
import threading
import time
from urllib.parse import urlencode

from .quote_http import public_url
from .quotes import _lock, number

GRADIENT = {'provider': 'gradient', 'url': '', 'creator': '', 'source_url': '', 'license': '', 'license_url': ''}
PROVIDERS = ('bing', 'wikimedia', 'artic', 'nasa', 'picsum')


class MediaService:
    def __init__(self, service):
        self.service, self.config = service, service.config

    def selected(self):
        provider = self.config.get('photo_provider', 'random')
        return provider if provider in PROVIDERS + ('random',) else 'gradient'

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
        host = 'en.wikipedia.org'
        now = self.service.clock()
        # 오늘의 사진은 하루 한 장이라 최근 7일 중에서 고른다. 세로 사진은 건너뛴다.
        for days in self.service.rng.sample(range(7), 3):
            day = time.strftime('%Y/%m/%d', time.gmtime(now - days * 86400))
            data = self.service.cached('wikimedia:' + day, 86400, lambda: self.service.fetch(
                f'https://{host}/api/rest_v1/feed/featured/{day}', hosts={host}, timeout=8))
            item = data.get('image') if isinstance(data, dict) else None
            if not isinstance(item, dict):
                continue
            original, thumb = item.get('image') or {}, item.get('thumbnail') or {}
            width, height = original.get('width'), original.get('height')
            if type(width) is not int or type(height) is not int or width < height:
                continue
            image = original.get('source')
            if width > 1920 and isinstance(thumb.get('source'), str):
                image = re.sub(r'/\d+px-([^/]+)$', r'/1920px-\1', thumb['source'])
            image = public_url(image, {'upload.wikimedia.org'})
            source = public_url(item.get('file_page'), {'commons.wikimedia.org'})
            if not image or not source:
                continue
            license_info = item.get('license') if isinstance(item.get('license'), dict) else {}
            artist = item.get('artist') if isinstance(item.get('artist'), dict) else {}
            description = item.get('description') if isinstance(item.get('description'), dict) else {}
            return {'provider': 'wikimedia', 'provider_name': 'Wikimedia Commons 오늘의 사진', 'url': image,
                    'source_url': source, 'title': str(description.get('text') or item.get('title') or '')[:500],
                    'creator': ' '.join(str(artist.get('text') or '작가 미상').split())[:200],
                    'license': str(license_info.get('type') or 'Wikimedia Commons')[:100],
                    'license_url': public_url(license_info.get('url')) or source}
        return {**GRADIENT, 'reason': 'invalid-photo'}

    def artic_background(self):
        host = 'api.artic.edu'
        page = self.service.rng.randint(1, 5)
        params = urlencode({'q': 'landscape', 'query[term][is_public_domain]': 'true', 'limit': 50, 'page': page,
                            'fields': 'id,title,artist_display,image_id,thumbnail'})
        data = self.service.cached(f'artic:{page}', 3600, lambda: self.service.fetch(
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
            if current and current['selected'] != selected:
                current = None
            previous = current['photo'] if current else GRADIENT
            if not force and current and current['expires'] > now:
                return {**previous, 'refresh_after': max(1, ceil(current['expires'] - now))}
            candidates = [selected] if selected != 'random' else [
                provider for provider in PROVIDERS if self.service.state(provider)['until'] <= now]
            if not candidates:
                return {**previous, 'reason': 'cooldown', 'refresh_after': 60}
            self.service.rng.shuffle(candidates)
            photo = {**GRADIENT, 'reason': 'cooldown'}
            # 무작위 모드에서는 실패한 공급원을 건너뛰고 다음 공급원을 시도한다.
            for provider in candidates[:3]:
                photo = self._select(provider)
                if photo.get('url'):
                    break
            now = self.service.clock()
            if photo.get('url'):
                expires = now + number(self.config.get('photo_refresh_hours'), 3, 1, 24) * 3600
            else:
                expires = now + 60
                photo = {**previous, 'reason': photo.get('reason', 'request-failed')}
            self.service.runtime['selected_background'] = {'selected': selected, 'photo': dict(photo), 'expires': expires}
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
