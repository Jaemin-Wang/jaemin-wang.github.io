# AIM Lab website

GitHub Pages에서 제공하는 영문·국문 정적 사이트입니다.

## 콘텐츠 수정 및 배포

1. Node.js 24 이상을 설치합니다. HTML 생성용 외부 패키지 설치는 필요하지 않습니다.
2. `admin.py`에서 데이터를 수정하고 **Save JSON + HTML to disk**를 누르면 JSON을
   저장한 뒤 영문·국문 HTML 10개를 자동으로 갱신합니다. 뉴스·논문 변경은 홈의 미리보기에도
   반영됩니다. JSON 백업(`.json.bak`)은 기존처럼 생성됩니다.
   HTML 갱신에 실패하면 JSON 저장 여부와 오류를 따로 안내하므로, 원인을 해결한 뒤 다시 저장하세요.
   편집기로 JSON을 직접 수정했다면 다음 명령으로 HTML을 갱신합니다.

   ```sh
   node scripts/prerender.mjs
   node scripts/check-seo.mjs
   ```

3. JSON, 이미지와 **갱신된 HTML을 함께** 커밋하고 기존 GitHub Pages 배포 브랜치에 푸시합니다.
   관리자 프로그램은 로컬 파일을 저장하며 커밋·푸시는 자동으로 하지 않습니다.

HTML에는 JSON에서 생성한 실제 본문이 포함됩니다. 생성된 목록은 직접 편집하지 말고
JSON을 수정한 뒤 다시 생성하세요. 레이아웃·본문 생성 함수는 각 HTML에서 수정합니다.
생성기는 같은 함수를 실행하므로 영문·국문, 정렬, 링크, 스타일을 그대로 사용합니다.
브라우저에서는 기존처럼 최신 JSON을 읽으며, 실패하면 미리 생성한 본문을 보존합니다.
JavaScript가 꺼져 있을 때는 구성원·논문의 모든 탭을 펼쳐 보여줍니다.

`node scripts/prerender.mjs --check`는 파일을 변경하지 않고 최신 여부를 검사합니다.
GitHub Actions의 `Check static site`는 JSON과 HTML이 불일치하면 실패합니다.
이 검사는 기존 Pages 배포를 변경하거나 자동으로 차단하지 않으므로 푸시 전에도 실행하세요.

## 검색 노출 확인

- 사이트맵: https://aimlab.knu.ac.kr/sitemap.xml — 실제 웹페이지 10개만 포함합니다.
- 영문 홈의 대표 URL은 `/`입니다. `/index.html`은 같은 페이지이며 canonical로 통합합니다.
- JSON 파일은 공개 데이터이며 검색 노출 목표가 아닙니다. 사이트맵에서 제외하지만
  브라우저와 검색엔진의 렌더링에 필요하므로 robots.txt로 차단하지 않습니다.
- `robots.txt`에는 사이트맵 위치와 크롤링 허용을 명시합니다. 기존 파일 부재(404)가
  곧 차단을 뜻하는 것은 아닙니다.

배포 후 Search Console에서 사이트맵을 다시 제출하고, 주요 HTML URL의
**URL 검사 → 실제 URL 테스트**에서 응답, 렌더링된 본문, 사용자 선언 canonical 및
기존 색인 데이터의 Google 선택 canonical을 확인하세요. 수정된 주요 페이지에 색인 생성을
요청할 수 있습니다. JSON URL에는 색인 생성 요청이 필요하지 않습니다.

`발견됨 - 현재 색인이 생성되지 않음`은 발견 후 아직 크롤링하지 않았다는 뜻이며,
`크롤링됨 - 현재 색인이 생성되지 않음`은 크롤링 후 아직 색인에 포함되지 않았다는 뜻입니다.
유효성 검사 통과는 모든 URL의 색인 생성을 보장하지 않습니다. 이 저장소의 개선만으로
Google의 색인 선택, 반영 시점, 순위를 보장할 수는 없습니다.

참고: [Google JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics),
[사이트맵 작성](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap),
[페이지 색인 보고서](https://support.google.com/webmasters/answer/7440203?hl=ko).
