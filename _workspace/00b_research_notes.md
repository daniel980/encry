# 00b. 기술 리서치 노트 (WebSearch 기반, 2026-07 기준)

## NVIDIA DSX / DSX OS

- **NVIDIA DSX**: Vera Rubin 세대 AI Factory의 레퍼런스 디자인("AI Factory를 짓는 플레이북").
  기가와트급 AI Factory의 전력·냉각·컴퓨트·네트워크·스토리지 통합 설계 + Omniverse DSX
  디지털 트윈 블루프린트 포함. DDN, Supermicro 등 광범위한 산업 파트너 지원.
- **DSX OS** (GTC Taipei, 2026-05 발표): AI Factory 인프라를 **프로비저닝·운영·모니터링**하기 위한
  **오픈소스·모듈러** 소프트웨어. 구성 요소:
  - Lifecycle management (수명주기 관리)
  - Runtime consistency (런타임 일관성)
  - Health automation (헬스 자동화)
  - Resiliency (복원력/자동 복구)
  - Multi-tenant AI factory operations (멀티테넌트 운영)
  - AI platform services
- **MCP 서버 구조**: DSX OS 컴포넌트들은 프로비저닝/네트워킹/**Observability** 등 도메인별
  **MCP 서버**를 제공 → AI 에이전트가 팩토리 전체 운영 표면을 단일 툴 카탈로그로 발견,
  **크로스 도메인 상관분석** 수행 가능. (Agentic Operations 지향)
- **DSX Exchange**: MQTT 기반 **IT/OT 통신 허브**. 그리드 이벤트, 열(thermal) 데이터,
  전력 이상 등 **Facility 레벨 신호**를 상위 SW 스택에 노출.
- 설계 목표 3가지: 매출화 시간 단축(faster time to revenue), 효율, 신뢰성/복원력.
- 생태계: Mirantis, OpenNebula, Rafay, Red Hat, Spectro Cloud, Supermicro, Vultr, vCluster 등이
  컴포넌트 채택. Ian Buck: "새로운 서비스·에이전트·AI를 올릴 수 있는 안정적 기반".

## NVIDIA Mission Control (참고: DSX OS와 함께 쓰이는 상용 제어면)

- AI Factory의 **통합 컨트롤 플레인**: 워크로드 스케줄링/오케스트레이션 → 모니터링 →
  **자율 복구(autonomous recovery)** 까지 커버.
- 통합 요소: BCM(Base Command Manager), Run:ai 스케줄러, NeMo 마이크로서비스,
  **DCGM 텔레메트리**, UFM(Unified Fabric Manager), NMX Manager, 스토리지(MaxLPS).
- **Grafana 기반 통합 대시보드** + 상시 헬스체크, 시계열 DB에 핵심 메트릭 저장.
- 자율 복구 엔진: 이상 탐지 → 격리 → 잡 재시작 → HW 조치까지 E2E.

## CoreWeave (코어위브) — 업계 벤치마크

- **CoreWeave Mission Control**: "AI 클라우드의 운영 표준". GPU 플릿 모니터링,
  노드/플릿 **수명주기 컨트롤러**, CloudOps 모니터링, 이슈 탐지·트러블슈팅 가속.
- **CoreWeave Observe™**: 클러스터 메트릭·대시보드를 별도 설정 없이 기본 제공(out-of-the-box).
- **Telemetry Relay**: 암호화된 감사/보안 이벤트를 고객 SIEM으로 포워딩 (거버넌스/컴플라이언스).
- 대화형 AI 에이전트: Slack에서 클러스터 헬스/잡 동작/인시던트/변경사항 질의응답.
- 시사점: **관측 데이터 기본 제공 + 수명주기 자동화 + Agentic 운영**이 AI 클라우드 운영의
  사실상 표준으로 자리잡는 중 → SKT-NVIDIA 협력의 경쟁 맥락.

## Vera Rubin 플랫폼 (2026 양산 램프)

- Rubin GPU + Vera CPU + NVLink 차세대: **NVL72/NVL144** 랙스케일 시스템.
  NVL144 CPX: 8 EFLOPS, 100TB 고속 메모리/랙 (대규모 컨텍스트 추론용).
- POD 스케일: Vera Rubin NVL72 + Vera CPU + BlueField-4 STX 스토리지 +
  Spectrum-6 SPX Ethernet 랙 등 5개 목적형 랙이 하나의 슈퍼컴퓨터로 동작.
- **BlueField-4 DPU**: 패킷 처리, 암복호화, vSwitch, 라우팅, **텔레메트리**, NVMe-oF 등
  스토리지 연산을 오프로드 → CPU/GPU 부하 없이 인프라 기능 수행.

## In-band vs Out-of-band 모니터링 (기술 배경)

- **In-band**: 호스트 OS/드라이버 경유 — nvidia-smi, **DCGM** 등. 풍부한 GPU 메트릭,
  단 호스트 다운 시 함께 소실, 워크로드에 (미미하나) 오버헤드.
- **Out-of-band**: **BMC + Redfish**(DMTF 표준, JSON over HTTPS) — 보드/흡기 센서, 전력,
  SEL, FRU, 원격 전원제어, OOB 펌웨어 업데이트. 호스트 다운 상태에서도 동작.
- **DPU 기반**: BlueField는 자체 BMC 포함, 별도 OOB 관리망에서 Redfish로 전체 수명주기 관리.
  DPU 오프로드 텔레메트리는 호스트 자원 소모 없이 네트워크/스토리지/보안 관측 제공.

## 출처
- https://developer.nvidia.com/blog/nvidia-dsx-os-delivers-open-modular-software-for-operating-ai-factories-at-scale/
- https://nvidianews.nvidia.com/news/dsx-infrastructure-ai-factory
- https://nvidianews.nvidia.com/news/nvidia-releases-vera-rubin-dsx-ai-factory-reference-design-and-omniverse-dsx-digital-twin-blueprint-with-broad-industry-support
- https://www.datacenterknowledge.com/data-center-chips/nvidia-says-vera-rubin-vera-cpu-on-track-launches-dsx-os-to-run-ai-factories
- https://www.nvidia.com/en-us/data-center/mission-control/
- https://developer.nvidia.com/blog/automating-ai-factory-operations-with-nvidia-mission-control
- https://www.coreweave.com/mission-control
- https://www.coreweave.com/observability
- https://www.tomshardware.com/pc-components/gpus/nvidias-vera-rubin-platform-in-depth-inside-nvidias-most-complex-ai-and-hpc-platform-to-date
- https://nvidianews.nvidia.com/news/rubin-platform-ai-supercomputer
- https://ai-infrastructure.net/oob-management-bmc/
- https://networking-docs.nvidia.com/bluefieldbmc/2404/bluefield-bmc-software-overview

> 주의: 세션 네트워크 정책상 원문 페이지 직접 열람은 차단되어 WebSearch 요약 기반으로 정리함.
> 수치·명칭은 슬라이드 확정 전 교차 확인 권장.
