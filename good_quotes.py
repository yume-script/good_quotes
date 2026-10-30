# 홈 화면에 좋은 글귀와 배경 이미지를 표시하는 위젯과 관리 액션을 제공합니다.
from flask import has_request_context, request, session
from plugins.metadata.base import BaseMetadataProvider

PLUGIN_VERSION = '1.5.0'
SESSIONS = ('general', 'adult', 'audiobook', 'video')

try:
    # 플러그인을 불러올 때 포함 글꼴을 코어 글꼴 목록에 넣는다(이미 있으면 건너뜀).
    from .quote_fonts import install_fonts
    install_fonts()
except Exception:
    pass


class GoodQuotesMetadataProvider(BaseMetadataProvider):
    id = 'good_quotes'
    name = '좋은 글귀 · 홈 위젯'
    version = PLUGIN_VERSION
    is_searchable = False
    config_schema = []
    dashboard_widget = None
    category_tab = None
    home_widget = {'title': '좋은 글귀', 'subtitle': '페이지 사이의 짧은 문장',
                   'icon': 'fa-solid fa-quote-left', 'order': 6, 'limit': 1,
                   'sessions': list(SESSIONS), 'layout': 'full', 'frame': 'none'}

    def search(self, db_type, query):
        return []

    def apply(self, db_type, book_id, item_data):
        return False, '좋은 글귀 플러그인은 메타데이터를 수정하지 않습니다.'

    @staticmethod
    def _allowed(db_type):
        return db_type in SESSIONS and (db_type != 'adult' or session.get('role') == 'admin'
                                        or session.get('has_adult_access') == 1)

    def _service(self, db_type):
        from .quotes import QuoteService
        return QuoteService(self.get_plugin_config(db_type, default={}) or {})

    def get_dashboard_data(self, db_type, limit=1):
        # 공용 데이터 라우트에 login_required가 없으므로 여기서 반드시 검사한다.
        if not has_request_context() or not session.get('user_id'):
            return {'success': False, 'error': '로그인이 필요합니다.'}
        if session.get('is_default_password') == 1:
            return {'success': False, 'error': '비밀번호를 먼저 변경해 주세요.'}
        db_type = str(db_type or 'general').strip().lower()
        if not self._allowed(db_type):
            return {'success': False, 'error': '접근할 수 없는 서재입니다.'}
        try:
            # 첫 화면은 외부 요청 없이 즉시 그리고, 글귀와 배경은 브라우저가 이어서 받는다.
            return {'success': True, 'items': [self._service(db_type).card([], initial=True)]}
        except (ValueError, OSError, RuntimeError):
            return {'success': False, 'error': '글귀 설정을 확인해 주세요.'}

    def run_context_menu_action(self, db_type, action_id, context):
        from urllib.parse import urlsplit
        if not has_request_context() or not session.get('user_id') or session.get('is_default_password') == 1:
            return {'success': False, 'error': '로그인이 필요합니다.'}
        if not isinstance(action_id, str) or not action_id.startswith('quotes_') or not isinstance(context, dict):
            return {'success': False, 'error': '올바르지 않은 글귀 요청입니다.'}
        if not self._allowed(db_type):
            return {'success': False, 'error': '접근할 수 없는 서재입니다.'}
        # 커스텀 헤더와 동일 출처 검사로 코어 공용 액션 라우트의 CSRF 경계를 보완한다.
        origin = request.headers.get('Origin')
        if request.headers.get('X-Good-Quotes') != '1' or request.headers.get('Sec-Fetch-Site') == 'cross-site' or (
            origin and urlsplit(origin).netloc != request.host
        ):
            return {'success': False, 'error': '같은 BookOasis 화면에서 다시 실행해 주세요.'}
        public_actions = ('quotes_next', 'quotes_background')
        if action_id not in public_actions and session.get('role') != 'admin':
            return {'success': False, 'error': '관리자만 글귀를 관리할 수 있습니다.'}
        try:
            service = self._service(db_type)
            from .quote_media import MediaService
            if action_id == 'quotes_next':
                return {'success': True, 'item': service.card(context.get('recent', []), include_background=False,
                                                            language=context.get('language'))}
            if action_id == 'quotes_background':
                tags = context.get('tags', [])
                if not isinstance(tags, list) or len(tags) > 10 or any(not isinstance(tag, str) or len(tag) > 80 for tag in tags):
                    raise ValueError('태그 형식을 확인해 주세요.')
                media = MediaService(service)
                background = media.background(tags, force=context.get('force') is True)
                from .quote_weather import WeatherService
                weather_service = WeatherService(service)
                weather = media.weather or (weather_service.current() if weather_service.display_enabled() else None)
                if weather and (weather_service.display_enabled() or media.selected() == 'weather'):
                    # 날씨는 30분마다 다시 확인한다. 바뀌면 날씨 연동 배경도 그때 새로 고른다.
                    background['refresh_after'] = min(background.get('refresh_after') or 1800, 1800)
                return {'success': True, 'background': background,
                        'weather': weather if weather_service.display_enabled() else None}
            if action_id == 'quotes_manage':
                from .quote_weather import WeatherService
                return {'success': True, 'providers': service.status(), 'backgrounds': MediaService(service).status(),
                        'weather': WeatherService(service).current()}
            return {'success': False, 'error': '지원하지 않는 글귀 작업입니다.'}
        except (ValueError, OSError, TypeError, RuntimeError):
            return {'success': False, 'error': '글귀 작업에 실패했습니다. 입력 형식·외부 서비스 상태를 확인해 주세요.'}
