# 글귀 카드의 배경을 고릅니다. 사진 공급원은 아직 없으며 그라데이션을 사용합니다.
GRADIENT = {'provider': 'gradient', 'url': '', 'creator': '', 'source_url': '', 'license': '', 'license_url': ''}


class MediaService:
    def __init__(self, service):
        self.service, self.config = service, service.config

    def background(self, tags, *, force=False):
        # 새 사진 공급원은 여기에서 선택해 url·출처·refresh_after를 채워 반환한다.
        return {**GRADIENT, 'reason': 'selected-gradient', 'refresh_after': 0}
