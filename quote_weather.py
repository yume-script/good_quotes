# Open-Meteo(키 불필요)로 설정한 지역의 현재 날씨를 받아 배경 검색어와 카드 표시에 씁니다.
from urllib.parse import urlencode

# (WMO 코드, 상태, 이름, 낮 아이콘, 밤 아이콘)
CONDITIONS = (
    ((0, 1), 'clear', '맑음', '☀️', '🌙'),
    ((2, 3), 'cloudy', '흐림', '☁️', '☁️'),
    ((45, 48), 'fog', '안개', '🌫️', '🌫️'),
    ((51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82), 'rain', '비', '🌧️', '🌧️'),
    ((71, 73, 75, 77, 85, 86), 'snow', '눈', '❄️', '❄️'),
    ((95, 96, 99), 'thunder', '뇌우', '⛈️', '⛈️'),
)
# 같은 이름의 경기도 광주시와 헷갈리지 않도록 기본 지역은 광주광역시 좌표를 고정해 둔다.
BUILTIN = {'광주': (35.1595, 126.8526, '광주'), '광주광역시': (35.1595, 126.8526, '광주')}
# 배경 검색어: Wikimedia Commons(사진)와 시카고 미술관(명화)은 검색이 되는 키 없는 공급원이다.
QUERIES = {
    'clear-day': ('sunny landscape blue sky', 'sunny landscape'),
    'clear-night': ('night sky stars landscape', 'night'),
    'cloudy-day': ('cloudy sky landscape', 'clouds'),
    'cloudy-night': ('night clouds moon', 'night'),
    'fog-day': ('fog landscape', 'fog'),
    'fog-night': ('fog night', 'fog'),
    'rain-day': ('rain landscape', 'rain'),
    'rain-night': ('rain night city lights', 'rain'),
    'snow-day': ('snow landscape', 'snow'),
    'snow-night': ('snow night', 'snow'),
    'thunder-day': ('thunderstorm clouds', 'storm'),
    'thunder-night': ('lightning night', 'storm'),
}


def enabled(config, key, default):
    return config.get(key, default) in (True, 1, '1', 'true', 'on')


class WeatherService:
    def __init__(self, service):
        self.service, self.config = service, service.config

    def display_enabled(self):
        return enabled(self.config, 'weather_display', True)

    def city(self):
        value = self.config.get('weather_city', '광주')
        value = ' '.join(value.split())[:60] if isinstance(value, str) else ''
        return value or '광주'

    def location(self):
        city = self.city()
        if city in BUILTIN:
            return BUILTIN[city]
        host = 'geocoding-api.open-meteo.com'
        data = self.service.cached('weather:geo:' + city, 7 * 86400, lambda: self.service.fetch(
            f'https://{host}/v1/search?' + urlencode({'name': city, 'count': 1, 'language': 'ko', 'format': 'json'}),
            hosts={host}))
        place = (data.get('results') or [None])[0] if isinstance(data, dict) else None
        if not isinstance(place, dict) or type(place.get('latitude')) not in (int, float) or type(place.get('longitude')) not in (int, float):
            raise ValueError('지역을 찾지 못했습니다.')
        return place['latitude'], place['longitude'], str(place.get('name') or city)[:60]

    def current(self):
        state = self.service.state('weather')
        if state['until'] > self.service.clock():
            return None
        try:
            latitude, longitude, name = self.location()
            host = 'api.open-meteo.com'
            data = self.service.cached(f'weather:now:{latitude:.2f},{longitude:.2f}', 1800, lambda: self.service.fetch(
                f'https://{host}/v1/forecast?' + urlencode({'latitude': latitude, 'longitude': longitude, 'timezone': 'auto',
                                                           'current': 'temperature_2m,weather_code,is_day'}),
                hosts={host}))
            now = data.get('current') if isinstance(data, dict) else None
            code, temperature = now.get('weather_code'), now.get('temperature_2m')
            if type(code) is not int or type(temperature) not in (int, float):
                raise ValueError('날씨 응답 형식을 확인해 주세요.')
            day = now.get('is_day') != 0
            condition, label, icon = 'cloudy', '흐림', '☁️'
            for codes, key, name_ko, day_icon, night_icon in CONDITIONS:
                if code in codes:
                    condition, label, icon = key, name_ko, day_icon if day else night_icon
                    break
            state['calls'] += 1
            state['displayed'] += 1
            state['failures'] = 0
            return {'city': name, 'condition': condition, 'label': label, 'icon': icon, 'is_day': day,
                    'temperature': round(temperature), 'key': f"{condition}-{'day' if day else 'night'}",
                    'source_url': 'https://open-meteo.com/', 'license': 'CC BY 4.0'}
        except (ValueError, OSError, TypeError, AttributeError, KeyError, IndexError) as error:
            state['failures'] += 1
            state['last_code'] = getattr(error, 'status', 0)
            state['until'] = self.service.clock() + max(300, getattr(error, 'retry_after', 0))
            return None
