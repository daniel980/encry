# 00. 사용자 입력 정리

## 발표 주제
NVIDIA DSX OS 기반 End-to-end Observability 개발 논의 (NVIDIA–SKT 협력)

## 청중
- CTO 및 비기술 임원 포함
- 기술적 정확성은 유지하되, 임원이 이해할 수 있는 수준으로 스토리라인 단순화

## 발표 목표
1. SKT가 보유한 Observability 기술을 간략히 소개
2. NVIDIA DSX OS 기반 Observability 개발/구조를 논의하고 **확정**하기 위함 (의사결정 유도형 보고)

## 산출물 요구사항
- 실제 `.pptx` 파일 (한국어)
- 발표자 노트 포함
- 진행 방식: **스토리보드 먼저 사용자 승인 → 이후 슬라이드 콘텐츠·다이어그램 생성**

## 사용자 제공 초안 목차 (장표 구성 초안)
1. (1p) NVIDIA-SKT Observability 협력 시 목표
   - SKT의 기존 Observability 개발 경험 + NVIDIA DSX OS의 운영 기능 결합
   - Vera Rubin 기반 AI Factory의 E2E 통합 관제·분석 구조 공동 설계/개발 추진
   - 필요한 산출물 / 주요 논의 사항
2. (1p) SKT Observability 개발 경험
   - GPU 해외(해인) 클러스터 환경에서 Observability 솔루션 기반 역량 축적 + Dashboard
3. (1p) SKT Observability 주요 기능
   - 대표 대시보드/화면 스크린샷 위주
   - 필요 시 MRM, Facility-aware 등은 별도 장표 분리 가능
4. (1p) AI Factory 환경 전환에 따른 고도화 방안
   - 단일 Cluster 중심 → Multi-DC / Multi-Site
   - VM 환경 → Baremetal / Reserved Cloud 등 테이블 표기
5. (1~2p) DSX OS 기반 주요 Observability 구조 및 제공범위
   - 개발/연동 범위가 보이도록
6. (참고) NVIDIA의 Open Architecture (Mission Control 또는 OpenTelemetry 구조)
7. (1p) Compute Observability 개발 방안 — 수집 영역, 주요 분석 등
8. (1p) In-band vs Out-of-band 모니터링 방안, DPU 오프로드 기반 모니터링 방안
9. (1p) 네트워크·스토리지·Facility 개발 방안 (통합 1장 가능)
10. Discussion / Q&A

## 리서치 지시
- 인터넷에서 NVIDIA DSX OS, CoreWeave(코어위브) 등의 기술을 분석하여 내용 보강

## 기타 설정 (기본값 적용)
- 발표 시간: 미지정 → 논의형 보고 (10~12 슬라이드 수준)
- 데이터 미제공 항목(SKT 대시보드 스크린샷 등): 플레이스홀더 처리
