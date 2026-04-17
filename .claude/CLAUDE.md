# 기술 문서 & 보고서 작성 Harness

기술 문서 작성(81)과 업무 보고서 생성(82) 하네스를 통합한 구성.

## 구조

```
.claude/
├── agents/
│   ├── [기술 문서] info-architect.md      — 정보 설계 (구조 설계, 목차, 독자 분석)
│   ├── [기술 문서] doc-writer.md          — 집필자 (본문 작성, 코드 예제, 튜토리얼)
│   ├── [기술 문서] diagram-maker.md       — 다이어그램 (Mermaid, 시각 자료)
│   ├── [기술 문서] tech-reviewer.md       — 기술 리뷰어 (정확성, 완전성, 일관성)
│   ├── [기술 문서] version-controller.md  — 버전 관리 (변경 이력, 메타데이터)
│   ├── [보고서] data-collector.md         — 데이터 수집 (소스 탐색, 수치 추출)
│   ├── [보고서] analyst.md               — 데이터 분석 (통계, 트렌드, 인사이트)
│   ├── [보고서] visualizer.md            — 시각화 설계 (차트, 테이블, 인포그래픽)
│   ├── [보고서] report-writer.md         — 보고서 집필 (구조화된 보고서 작성)
│   └── [보고서] executive-summarizer.md  — 요약 및 교차 검증
├── skills/
│   ├── technical-writer/      — 기술 문서 오케스트레이터
│   ├── report-generator/      — 보고서 오케스트레이터
│   ├── diagram-patterns/      — Mermaid 다이어그램 패턴 라이브러리
│   ├── api-doc-standards/     — API 문서 작성 표준
│   ├── code-example-patterns/ — 코드 예제 패턴 라이브러리
│   ├── data-visualization-guide/ — 데이터 시각화 가이드
│   └── kpi-dashboard-patterns/   — KPI 대시보드 설계 패턴
└── CLAUDE.md                  — 이 파일
```

## 사용법

| 목적 | 스킬 | 자연어 예시 |
|------|------|------------|
| 기술 문서 작성 | `/technical-writer` | "기술 문서 작성해줘" |
| 업무 보고서 생성 | `/report-generator` | "업무 보고서 만들어줘" |

## 산출물

모든 산출물은 `_workspace/` 디렉토리에 저장된다.

**기술 문서** (`/technical-writer`)
- `01_doc_structure.md` — 문서 구조 설계서
- `02_doc_draft.md` — 문서 본문 초안
- `03_diagrams.md` — 다이어그램 모음
- `04_review_report.md` — 기술 리뷰 보고서
- `05_version_meta.md` — 버전 관리 메타데이터

**보고서** (`/report-generator`)
- `01_data_collection.md` — 수집된 데이터 정리
- `02_analysis_report.md` — 분석 결과
- `03_visualization_spec.md` — 시각화 명세
- `04_full_report.md` — 최종 보고서
- `05_executive_summary.md` — 경영진 요약
