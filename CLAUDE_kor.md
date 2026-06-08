# Open Sesame — Claude Code용 AI 투자 자문 시스템

## 프로젝트 개요
AI 분석 기능이 탑재된 개인 투자 대시보드.  
한국/미국 주식 포트폴리오 추적 + Claude Code 투자 자문.  
사용법: `README.md`

## 파일 구조
```text
open-sesame/
├── app.py                        # Flask 서버 (API + HTML 서빙)
├── ADVISOR.md                    # 투자 자문 프롬프트 (CLI 사용법 포함)
├── history/
│   ├── portfolio.toml            # 포트폴리오 데이터 (직접 편집)
│   ├── events.toml               # 이벤트 캘린더 데이터 (직접 편집)
│   ├── api_cache.json            # 주간 브리핑 API 캐시 (자동 생성)
│   └── YYYY-MM-DD.json           # 마이페이지 스냅샷 출력 (자동 생성, gitignored)
├── data/
│   ├── db.py                     # SQLite 스키마 & 쿼리 함수
│   ├── fetcher.py                # pykrx / yfinance 시세 조회
│   └── opensesame.db             # gitignored
├── briefing/
│   ├── briefing.py               # Slack 브리핑 콘텐츠 생성기
│   └── slack.py                  # Slack Webhook 전송
├── static/                       # 프론트엔드 에셋
├── templates/                    # Jinja2 HTML 템플릿 (4개 탭)
├── report/                       # 투자 자문 분석 로그 (gitignored)
├── schedule/                     # 원격 에이전트 자동 생성 보고서 (gitignored)
├── .github/workflows/
│   └── briefing.yml              # 브리핑 자동화 (GitHub Actions)
└── formats/                      # 자문 리포트 포맷 템플릿
```

## 실행
```bash
python3 app.py   # → http://localhost:5000
```

## Git 워크플로
- **커밋 단위**: 의미 있는 변경마다 즉시 커밋
- **커밋 메시지**: 영어, 간결하게  
  (prefix: `feat:`, `fix:`, `refactor:`, `docs:`, `data:` 등)
- **Push**: main 브랜치로 자동 push (`git push origin HEAD:main`)  
  *(메인 브랜치 보호를 원할 시 수정할 것)*
- **Force push 금지**: `--force` 사용 불가
