# 플러그인에 포함한 OFL 한글 글꼴을 코어의 사용자 글꼴 폴더에 복사해 글꼴 목록에 나타나게 합니다.
from pathlib import Path
import shutil

FONTS_DIR = Path(__file__).resolve().parent / 'fonts'
# plugins/metadata/good_quotes/ 기준으로 세 단계 위가 코어 루트이며 코어는 static/fonts/custom/을 스캔한다.
CORE_FONTS_DIR = Path(__file__).resolve().parents[3] / 'static' / 'fonts' / 'custom'


def install_fonts(target=CORE_FONTS_DIR):
    installed = []
    if not FONTS_DIR.is_dir() or not target.parent.parent.is_dir():
        return installed
    try:
        target.mkdir(parents=True, exist_ok=True)
        for font in sorted(FONTS_DIR.glob('*.woff2')):
            destination = target / font.name
            # 관리자가 같은 이름으로 넣은 다른 파일은 덮어쓰지 않는다.
            if not destination.exists():
                temporary = destination.with_name('.' + font.name + '.tmp')
                shutil.copyfile(font, temporary)
                temporary.replace(destination)
                installed.append(font.stem)
    except OSError:
        pass
    return installed
