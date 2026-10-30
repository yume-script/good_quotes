# 좋은 글귀 (Good Quotes)

BookOasis 홈 화면에 **좋은 글귀**와 **배경 이미지**를 보여주는 위젯 플러그인입니다.
[colaiuta77/detail_studio](https://github.com/colaiuta77/detail_studio) 1.0.1의 "홈 좋은 글귀" 기능만 따로 떼어 만들었습니다. 상세페이지와 데일리 픽은 포함하지 않습니다.

| 항목 | 내용 |
| --- | --- |
| 플러그인 ID | `good_quotes` |
| 버전 | 1.4.0 |
| 지원 세션 | 일반·성인 도서, 오디오북, 비디오 |
| 외부 의존성 | 없음 (표준 라이브러리 + 코어 Flask) |
| API 키 | 필요 없음 |
| 라이선스 | GNU AGPL v3 (`LICENSE`) |

## 기능

- **글귀** — 한국어는 [Korean Advice API](https://github.com/gwongibeom/korean-advice-open-api), 영어는 ZenQuotes(기본 켜짐)·PositiveQuotation에서 받습니다. 모두 키가 필요 없습니다. 둘 다 표시할 때는 가중치(기본 60:35:5)로 섞습니다. 공급원이 모두 실패하면 내장 문구를 표시합니다.
- **날씨 연동 배경 (기본)** — [Open-Meteo](https://open-meteo.com/)(키 불필요, CC BY 4.0)로 설정한 지역(기본 **광주광역시**)의 현재 날씨를 30분마다 확인합니다. 맑음·흐림·비·눈·안개·뇌우와 낮·밤에 맞는 사진을 Wikimedia Commons 품질 사진과 시카고 미술관 명화에서 찾고, 날씨가 바뀌면 변경 주기와 상관없이 바로 배경을 바꿉니다. 날씨를 받지 못하면 일반 배경으로 넘어갑니다.
- **날씨 표시** — 위젯 왼쪽 아래에 `🌧️ 광주 14° · 비`처럼 현재 날씨와 기온을 표시합니다. 설정에서 끌 수 있습니다.
- **배경 이미지** — API 키가 필요 없는 5곳(Bing 오늘의 이미지, Wikimedia Commons 오늘의 사진, Art Institute of Chicago, NASA APOD, Lorem Picsum) 중 하나를 고르거나 **5곳 무작위**(기본)로 섞어 씁니다. 그라데이션만 쓸 수도 있습니다. 배경은 1~24시간(기본 3시간)마다 바뀌고, 무작위 모드에서는 응답하지 않는 곳을 건너뜁니다.
- **위젯 도구** — 다른 글귀, 언어 전환(`En`은 영어 글귀, `한`은 한국어 글귀, `En.한`은 둘을 섞어 받음), 배경 변경, 출처 보기 버튼이 있습니다. 배경을 그라데이션으로 두면 배경 변경 버튼은 숨겨집니다.
- **글꼴** — 한국어·영어·저자의 글꼴과 크기를 각각 고릅니다. 고운바탕·고운돋움·나눔명조·나눔손글씨 펜 4종이 포함되어 있고, 코어에 넣은 다른 글꼴도 고를 수 있습니다. 긴 문구는 카드 높이에 맞게 자동으로 줄입니다.

## 설치

플러그인 게시판의 **저장소 URL 설치**에 `https://github.com/yume-script/good_quotes`를 입력하고 **저장소 설치**를 누릅니다. 직접 설치하려면 이 저장소의 파일을 BookOasis의 다음 위치에 복사합니다.

```text
plugins/metadata/good_quotes/
  __init__.py
  good_quotes.py
  quotes.py
  quote_http.py
  quote_media.py
  quote_fonts.py
  quote_weather.py
  fonts/
  VERSION
  dashboard.html
  dashboard.css
  dashboard.js
  settings.html
  settings.css
  settings.js
```

1. 플러그인 관리에서 플러그인을 다시 불러온 뒤 **좋은 글귀 · 홈 위젯**을 활성화합니다.
2. **내 설정 → 홈 화면 플러그인 배치 모드**를 켭니다.
3. 홈 화면의 **위젯 추가 → 좋은 글귀**를 선택합니다.
4. 필요하면 **플러그인 관리 → 좋은 글귀 · 홈 위젯** 설정에서 공급원·배경·글꼴을 바꾸고 저장합니다. 설정은 세션(일반·성인 등)마다 따로 저장됩니다.

배경이 보이지 않으면 설정의 **공급원 상태 확인**을 눌러 보세요. 배경 공급원마다 정상·실패 횟수·HTTP 코드를 보여줍니다. 위젯 아래쪽에도 실패 안내가 표시됩니다.

Detail Studio와 함께 설치해도 됩니다. 두 플러그인은 설정과 저장 파일이 서로 겹치지 않습니다.

## 포함 글꼴

플러그인을 불러올 때 `fonts/`의 글꼴을 코어 사용자 글꼴 폴더(`static/fonts/custom/`, Docker는 `custom_fonts/`)에 복사합니다. 같은 이름의 파일이 이미 있으면 덮어쓰지 않습니다. 복사된 글꼴은 플러그인 설정의 글꼴 목록과 코어 뷰어의 글꼴 목록에 함께 나타납니다.

| 목록 이름 | 글꼴 | 라이선스 |
| --- | --- | --- |
| `GowunBatang` | 고운바탕 | SIL OFL 1.1 (`fonts/OFL-GowunBatang.txt`) |
| `GowunDodum` | 고운돋움 | SIL OFL 1.1 (`fonts/OFL-GowunDodum.txt`) |
| `NanumMyeongjo` | 나눔명조 | SIL OFL 1.1 (`fonts/OFL-NanumMyeongjo.txt`) |
| `NanumPenScript` | 나눔손글씨 펜 | SIL OFL 1.1 (`fonts/OFL-NanumPenScript.txt`) |

[google/fonts](https://github.com/google/fonts)의 TTF를 글리프 손실 없이 woff2로 변환했습니다.

## 저장 위치

- 포함 글꼴 복사 외에는 디스크에 아무것도 저장하지 않습니다. 받은 글귀·배경 URL·출처는 서버 메모리에만 잠시 보관하며, 코어를 다시 시작하면 새로 받습니다.
- 코어 DB에는 공급원·배경·글꼴 같은 표시 설정만 저장합니다.

## 공급원과 이용 조건

| 공급원 | 용도 | 조건 |
| --- | --- | --- |
| Korean Advice API | 한국어 글귀·저자 | [LICENSE](https://github.com/gwongibeom/korean-advice-open-api/blob/main/LICENSE): 비상업적 무료 사용, 출처 표기 |
| ZenQuotes | 영문 글귀 | [이용 조건](https://docs.zenquotes.io/terms-and-conditions/) |
| PositiveQuotation | 영문 속담 | [API 문서](https://positivequotation.com/developers/public-domain-quotes-api) |
| Bing 오늘의 이미지 | 풍경 사진 배경 | 각 사진의 저작권자 소유 · 개인 배경화면 용도 |
| Wikimedia Commons 오늘의 사진 | 엄선 사진 배경 | 사진마다 다른 자유 라이선스(CC BY-SA 등) · 출처 표시 |
| Art Institute of Chicago | 공개 영역 명화 배경 | [CC0](https://www.artic.edu/open-access/open-access-images) · [API](https://api.artic.edu/docs/) |
| NASA APOD | 천체 사진 배경 (공용 `DEMO_KEY`) | NASA 사진은 공개 영역, 일부는 저작권자 표기 · [APOD](https://apod.nasa.gov/) |
| Open-Meteo | 현재 날씨·지역 검색 | [CC BY 4.0](https://open-meteo.com/en/license) · 비상업적 무료 |
| Lorem Picsum | 무작위 사진 배경 | Unsplash 사진 · [Unsplash License](https://unsplash.com/license) |

ZenQuotes·PositiveQuotation은 설정에서 이용 조건 확인 스위치를 켜야 동작합니다.

## 출처

[Detail Studio](https://github.com/colaiuta77/detail_studio)(AGPL-3.0)의 글귀 코드(`quotes.py`, `quote_*.py`)와 위젯·설정 UI를 가져와 다음을 바꿨습니다.

- 단독 플러그인 `good_quotes`로 분리하고, 데일리 픽 선택 로직은 뺐습니다.
- API 키가 필요한 기능(DeepL 사전 번역, Unsplash·Pexels 배경)과 전용 SQLite 저장소를 없앴습니다. 영문 글귀는 원문 그대로 표시합니다.
- 배경을 키가 필요 없는 5곳(Bing·Wikimedia Commons·Art Institute of Chicago·NASA APOD·Lorem Picsum)으로 바꿨습니다.
- 요청 헤더(`X-Good-Quotes`), CSS 클래스(`gq-`), 저장 키 이름을 바꿔 Detail Studio와 겹치지 않게 했습니다.
