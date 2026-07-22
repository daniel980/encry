/* CTO 보고 덱 생성 — 03_slide_deck.md v2 명세 기반 (960x540pt = 13.33x7.5in) */
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";

const IN = (pt) => pt / 72;
const F = "Malgun Gothic";

// palette
const NAVY = "17375E", NAVY_T = "DEE5EF", NAVY_L = "8FA6C4", NAVY_SUB = "C7D3E2";
const DSX = "76B900", DSX_T = "E8F4D4";
const AMB = "D97E00", AMB_T = "FCEBD2";
const GRAY = "6B7280", GRAY_T = "F1F3F5", GRAY_D = "4B5563", G374 = "374151";
const WARN = "C0392B", WARN_T = "FBE9E7";
const T900 = "1A1A1A", LINE = "C9D2DE", PGC = "9CA3AF";

function box(s, x, y, w, h, o = {}) {
  s.addShape(o.round ? "roundRect" : "rect", Object.assign({
    x: IN(x), y: IN(y), w: IN(w), h: IN(h),
    fill: o.fill ? { color: o.fill } : { color: "FFFFFF" },
    line: o.lineColor ? { color: o.lineColor, width: o.lineW || 0.75, dashType: o.dash || "solid" } : { type: "none" },
  }, o.round ? { rectRadius: IN(o.rad || 6) } : {}));
}
function txt(s, t, x, y, w, h, o = {}) {
  s.addText(t, Object.assign({
    x: IN(x), y: IN(y), w: IN(w), h: IN(h), fontFace: F,
    fontSize: o.size || 12, color: o.color || T900, bold: !!o.bold, italic: !!o.italic,
    align: o.align || "left", valign: o.valign || "top", margin: 0,
    lineSpacingMultiple: o.lsp || 1.15,
  }, o.extra || {}));
}
function header(s, title, o = {}) {
  const c = o.gray ? GRAY : NAVY;
  box(s, 40, 22, 5, 26, { fill: c });
  box(s, 48, 22, 2.5, 26, { fill: o.gray ? "B9BFC7" : NAVY_L });
  let tx = 58;
  if (o.refBadge) { // (참고) pill
    box(s, 58, 24, 44, 22, { round: true, rad: 10, fill: "FFFFFF", lineColor: GRAY });
    txt(s, "참고", 58, 24, 44, 22, { size: 11, color: GRAY, align: "center", valign: "middle" });
    tx = 110;
  }
  txt(s, title, tx, 20, 640, 30, { size: 18, bold: true, color: c, valign: "middle" });
  if (o.badge) {
    box(s, 846, 22, 74, 24, { round: true, rad: 5, fill: NAVY });
    txt(s, o.badge, 846, 22, 74, 24, { size: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
  }
  if (o.grayBadge) {
    box(s, 850, 22, 70, 22, { fill: GRAY_T, lineColor: LINE });
    txt(s, o.grayBadge, 850, 22, 70, 22, { size: 10.5, color: GRAY, align: "center", valign: "middle" });
  }
  if (o.wideBadge) {
    box(s, 790, 22, 130, 24, { round: true, rad: 5, fill: NAVY });
    txt(s, o.wideBadge, 790, 22, 130, 24, { size: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
  }
}
function gov(s, t, o = {}) {
  txt(s, t, 60, 56, 840, 48, { size: o.size || 17.5, bold: true, color: o.color || T900, align: "center", valign: "middle", lsp: 1.15 });
}
function pageNo(s, n, white) {
  txt(s, String(n), 892, 514, 38, 16, { size: 10, color: white ? "FFFFFF" : PGC, align: "right", extra: white ? { transparency: 40 } : {} });
}
function chipRect(s, x, y, w, h, t, o = {}) {
  box(s, x, y, w, h, { round: true, rad: Math.min(10, h / 2), fill: o.fill || GRAY_T, lineColor: o.lineColor });
  txt(s, t, x + 2, y, w - 4, h, { size: o.size || 10.5, bold: !!o.bold, color: o.color || GRAY_D, align: "center", valign: "middle" });
}
function navyTab(s, x, y, w, t) {
  box(s, x, y, w, 20, { round: true, rad: 4, fill: NAVY });
  txt(s, t, x, y, w, 20, { size: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
}
function arrow(s, x1, y1, x2, y2, o = {}) {
  s.addShape("line", {
    x: IN(Math.min(x1, x2)), y: IN(Math.min(y1, y2)),
    w: IN(Math.abs(x2 - x1)), h: IN(Math.abs(y2 - y1)),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color: o.color || "9CA3AF", width: o.w || 1.5, dashType: o.dash || "solid",
      endArrowType: o.noHead ? "none" : "triangle", beginArrowType: o.both ? "triangle" : "none" },
  });
}
function shot(s, x, y, w, h, caption) {
  box(s, x, y, w, h, { fill: GRAY_T, lineColor: GRAY, lineW: 1.5, dash: "dash" });
  txt(s, "대시보드 스크린샷", x, y + h / 2 - 22, w, 18, { size: 12, color: GRAY, align: "center" });
  const pw = 92;
  box(s, x + w / 2 - pw / 2, y + h / 2, pw, 20, { round: true, rad: 10, fill: "FFFFFF", lineColor: GRAY });
  txt(s, "SKT 제공 예정", x + w / 2 - pw / 2, y + h / 2, pw, 20, { size: 10.5, bold: true, color: GRAY_D, align: "center", valign: "middle" });
  if (caption) txt(s, caption, x, y + h + 3, w, 14, { size: 10, color: GRAY, align: "center" });
}
function legend3(s, x, y) {
  const items = [[DSX, DSX_T, "DSX OS 기본 제공"], [NAVY, NAVY_T, "SKT 개발"], [AMB, AMB_T, "공동 개발"]];
  let cx = x;
  items.forEach(([c, t, lab]) => {
    box(s, cx, y + 2, 11, 11, { fill: t, lineColor: c, lineW: 1 });
    txt(s, lab, cx + 15, y, 118, 16, { size: 10.5, color: GRAY_D });
    cx += 140;
  });
}
function decisionCard(s, x, y, w, h, dTitle, desc, basis) {
  box(s, x, y, w, h, { round: true, rad: 6, fill: NAVY });
  box(s, x + 12, y + 12, 15, 15, { fill: NAVY, lineColor: "FFFFFF", lineW: 1.25 });
  txt(s, dTitle, x + 36, y + 8, w - 44, 22, { size: 12.5, bold: true, color: "FFFFFF" });
  txt(s, desc, x + 36, y + 30, w - 44, h - (basis ? 52 : 36), { size: 10.5, color: NAVY_SUB, lsp: 1.2 });
  if (basis) txt(s, basis, x + 36, y + h - 20, w - 44, 14, { size: 10, color: NAVY_L });
}
function hdrRow(cells, colW) {
  return cells.map((c) => ({ text: c, options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, fontSize: 11.5, fontFace: F, align: "center", valign: "middle" } }));
}
function cell(t, o = {}) {
  return { text: t, options: Object.assign({ fontSize: o.size || 11, fontFace: F, color: o.color || T900, bold: !!o.bold, italic: !!o.italic, align: o.align || "left", valign: "middle", fill: { color: o.fill || "FFFFFF" } }, o.extra || {}) };
}
function chipCell(t, o = {}) {
  return cell(t, Object.assign({ fill: GRAY_T, color: GRAY_D, bold: true, size: o.size || 10.5 }, o));
}

/* ============ 슬라이드 1: 표지 ============ */
{
  const s = pres.addSlide();
  txt(s, "NVIDIA – SKT 협력 논의", 0, 170, 960, 22, { size: 13, bold: true, color: NAVY, align: "center", extra: { charSpacing: 4 } });
  txt(s, "NVIDIA DSX OS 기반\nEnd-to-end Observability 개발 논의", 0, 198, 960, 92, { size: 32, bold: true, color: T900, align: "center" });
  s.addShape("line", { x: IN(280), y: IN(300), w: IN(400), h: 0, line: { color: "C9CED6", width: 0.75 } });
  s.addShape("line", { x: IN(430), y: IN(299), w: IN(100), h: 0, line: { color: GRAY, width: 3 } });
  txt(s, "아키텍처 방향과 개발·연동 범위의 확정을 위한 논의 보고", 0, 316, 960, 22, { size: 14, color: GRAY, align: "center" });
  txt(s, "'26년 7월", 0, 426, 960, 20, { size: 13, bold: true, color: NAVY, align: "center" });
  s.addText([
    { text: "SKT ", options: { fontFace: F, fontSize: 12, color: GRAY_D } },
    { text: "[보고 조직명 플레이스홀더: SKT 제공 필요]", options: { fontFace: F, fontSize: 12, color: GRAY, italic: true } },
  ], { x: IN(0), y: IN(448), w: IN(960), h: IN(20), align: "center", margin: 0 });
  box(s, 315, 492, 330, 26, { lineColor: PGC, lineW: 1, dash: "dash" });
  txt(s, "[ For Discussion Purpose Only ]", 315, 492, 330, 26, { size: 10, color: GRAY, align: "center", valign: "middle" });
  s.addNotes("[표지 0:00~0:30]\n\"안녕하십니까. 오늘은 NVIDIA DSX OS를 기반으로 한 End-to-end Observability 개발 방향을 보고드리고, 논의를 통해 확정까지 부탁드리고자 자리를 마련했습니다. 정보 공유가 아니라, 오늘 이 자리에서 세 가지를 결정해 주시는 것이 목적입니다. 발표는 20분, 이후 10~15분 정도 논의 시간을 갖겠습니다.\"\n\n강조: 부제의 \"확정\"에 힘 준다.\n전환: \"먼저, 오늘 결정해 주실 세 가지가 무엇인지부터 말씀드리겠습니다.\"");
}

/* ============ 슬라이드 2: Executive Summary ============ */
{
  const s = pres.addSlide();
  header(s, "Executive Summary");
  gov(s, "SKT 개발 경험 + DSX OS 운영 기능을 결합해 Vera Rubin AI Factory의 E2E 관제를 공동 설계·개발하며, 오늘 3가지를 확정하고자 한다");
  const rows = [["①", "협력 목표"], ["②", "협력 구도"], ["③", "오늘의\n결정 사항"]];
  const ys = [112, 234, 356];
  rows.forEach(([n, t], i) => {
    box(s, 40, ys[i], 140, 108, { fill: NAVY });
    txt(s, n, 40, ys[i] + 16, 140, 30, { size: 20, bold: true, color: "FFFFFF", align: "center" });
    txt(s, t, 40, ys[i] + 48, 140, 50, { size: 13, bold: true, color: "FFFFFF", align: "center" });
    box(s, 196, ys[i], 724, 108, { fill: "FFFFFF", lineColor: NAVY, lineW: 0.75 });
  });
  // 행 1 불릿 (2개 문단 — 각 문단 첫 런에만 bullet, 마지막 런에만 breakLine)
  s.addText([
    { text: "[목표] ", options: { bold: true, bullet: { characterCode: "2022", indent: 12 } } },
    { text: "Vera Rubin AI Factory의 Compute·Network·Storage·Facility " },
    { text: "E2E 통합 관제·분석", options: { bold: true } },
    { text: " 환경 확보", options: { breakLine: true, paraSpaceAfter: 10 } },
    { text: "[수준] ", options: { bold: true, bullet: { characterCode: "2022", indent: 12 } } },
    { text: "CoreWeave 유사 수준의 모니터링/분석 환경", options: { bold: true } },
    { text: " 확보 — 업계 최고 수준을 목표선으로 설정" },
  ].map(r => ({ text: r.text, options: Object.assign({ fontFace: F, fontSize: 12.5, color: T900 }, r.options || {}) })),
    { x: IN(214), y: IN(124), w: IN(692), h: IN(88), margin: 0, valign: "middle" });
  // 행 2 미니 결합 다이어그램
  box(s, 214, 244, 216, 42, { fill: NAVY_T, lineColor: NAVY });
  txt(s, "SKT Observability 개발 역량 — GPU 클러스터 운영·자체 대시보드", 220, 254, 204, 30, { size: 9.5, bold: true, color: NAVY, valign: "middle" });
  chipRect(s, 220, 238, 34, 13, "SKT", { fill: NAVY, color: "FFFFFF", size: 8.5, bold: true });
  box(s, 214, 294, 216, 42, { fill: DSX_T, lineColor: DSX });
  txt(s, "NVIDIA DSX OS 운영 프레임워크 — Lifecycle·Health Automation·MCP·DSX Exchange", 220, 304, 204, 30, { size: 9.5, bold: true, color: "3E6300", valign: "middle" });
  chipRect(s, 220, 288, 34, 13, "DSX", { fill: DSX, color: "FFFFFF", size: 8.5, bold: true });
  txt(s, "＋", 436, 276, 24, 24, { size: 16, bold: true, color: GRAY, align: "center", valign: "middle" });
  arrow(s, 434, 264, 480, 282, {}); arrow(s, 434, 312, 480, 296, {});
  box(s, 486, 242, 230, 82, { fill: AMB_T, lineColor: AMB, lineW: 2 });
  txt(s, "Vera Rubin AI Factory\nE2E 통합 관제·분석", 492, 250, 218, 44, { size: 12, bold: true, color: "8A5000", align: "center", valign: "middle" });
  s.addText([{ text: "목표 수준: ", options: { fontFace: F, fontSize: 10, color: "8A5000" } }, { text: "CoreWeave 유사", options: { fontFace: F, fontSize: 10, bold: true, color: "8A5000" } }],
    { x: IN(492), y: IN(296), w: IN(218), h: IN(18), align: "center", margin: 0 });
  chipRect(s, 486, 236, 34, 13, "공동", { fill: AMB, color: "FFFFFF", size: 8.5, bold: true });
  txt(s, "SKT 역량 × DSX OS 결합 → AI Factory 통합 관제 (상세: 슬라이드 6)", 730, 250, 176, 70, { size: 10, color: GRAY, valign: "middle" });
  // 행 3 결정 카드
  decisionCard(s, 210, 368, 228, 84, "D1. 아키텍처 방향", "DSX OS 골격 E2E 레이어드 구조 채택");
  decisionCard(s, 446, 368, 228, 84, "D2. 개발·연동 범위", "DSX OS 제공 / SKT 개발 / 공동 개발 경계 확정");
  decisionCard(s, 682, 368, 228, 84, "D3. 수집 전략·단계화", "In-band+OOB+DPU 하이브리드, 도메인 Phase 순서");
  txt(s, "필요 산출물: 아키텍처 설계서 · 범위 정의서 · PoC 계획", 40, 474, 500, 14, { size: 10, color: GRAY });
  txt(s, "Observability(옵저버빌리티): 인프라·워크로드 상태를 지표·로그·이벤트로 관측·분석하는 체계  ·  MCP(Model Context Protocol): AI 에이전트가 시스템 기능을 표준 방식으로 호출하는 개방형 인터페이스", 40, 492, 880, 26, { size: 9.5, color: GRAY });
  pageNo(s, 2);
  s.addNotes("[Executive Summary 0:30~2:30 — 절대 스킵 불가]\n\"핵심은 이 한 장에 다 있습니다. 저희 SKT는 이미 GPU 클러스터를 운영하며 Observability 솔루션을 직접 개발해 온 경험이 있습니다. 여기에 NVIDIA가 새로 공개한 DSX OS의 운영 프레임워크를 결합하면, Vera Rubin 기반 AI Factory의 Compute·Network·Storage·Facility를 관통하는 End-to-end 통합 관제를 가장 빠르고 확실하게 확보할 수 있습니다. 개발 목표는 명확합니다. 업계 최고 수준으로 평가받는 CoreWeave와 유사한 수준의 모니터링·분석 환경을 확보하는 것입니다.\n이를 위해 오늘 세 가지 확정을 요청드립니다. 첫째, 아키텍처 방향 — DSX OS를 골격으로 한 E2E 레이어드 구조. 둘째, 개발·연동 범위 — DSX OS가 제공하는 것, 저희가 개발하는 것, 공동으로 개발하는 것의 경계. 셋째, 수집 전략과 단계화입니다. 각각 뒤에서 근거를 말씀드리고, 마지막 장에서 다시 이 세 가지로 돌아오겠습니다.\"\n\n강조: 결정 카드 3개를 하나씩 짚는다. \"CoreWeave 유사 수준\" 또렷하게.\n전환: \"먼저 '저희가 이걸 할 수 있는 조직인가'부터 보여드리겠습니다.\"");
}

/* ============ 슬라이드 3: 개발 경험 ============ */
{
  const s = pres.addSlide();
  header(s, "1-1. SKT Observability 개발 경험");
  gov(s, "SKT는 해외(해인) GPU 클러스터 운영을 통해 Observability 솔루션 개발·운영 역량을 이미 축적했다");
  // 타임라인
  s.addShape("line", { x: IN(80), y: IN(180), w: IN(800), h: 0, line: { color: NAVY, width: 2 } });
  const nodes = [
    ["[YYYY]", "GPU 클러스터(해외·해인)\n운영 개시", NAVY, false],
    ["[YYYY]", "Observability 솔루션\n자체 개발 착수", NAVY, false],
    ["[YYYY]", "통합 대시보드\n서비스 개시", NAVY, false],
    ["2026 (현재)", "AI Factory 대응\n고도화 논의", AMB, true],
  ];
  nodes.forEach(([yr, de, c, big], i) => {
    const cx = 140 + i * 220, r = big ? 9 : 6;
    s.addShape("ellipse", { x: IN(cx - r), y: IN(180 - r), w: IN(r * 2), h: IN(r * 2), fill: { color: c }, line: { type: "none" } });
    const up = i % 2 === 0;
    txt(s, yr, cx - 70, up ? 128 : 194, 140, 16, { size: 12, bold: true, color: big ? AMB : NAVY, align: "center", italic: yr.startsWith("[") });
    txt(s, de, cx - 70, up ? 144 : 210, 140, 30, { size: 10.5, color: big ? "8A5000" : GRAY_D, align: "center" });
  });
  // 좌측 콜아웃
  box(s, 40, 256, 430, 224, { round: true, rad: 8, fill: "FFFFFF", lineColor: LINE });
  navyTab(s, 56, 246, 86, "축적 역량");
  const caps = [
    [["[수집] ", true], ["메트릭 수집 파이프라인", false]],
    [["[헬스] ", true], ["GPU 헬스 관리", false]],
    [["[시각화] ", true], ["통합 대시보드", false]],
    [["[탐지] ", true], ["알림·이상 탐지", false]],
  ];
  s.addText(caps.map((row, i) => row.map(([t, b], j) => ({
    text: t, options: { fontFace: F, fontSize: 13, color: T900, bold: b, bullet: j === 0 ? { characterCode: "25B8", indent: 14 } : false, breakLine: j === row.length - 1, paraSpaceAfter: 10 },
  }))).flat(), { x: IN(64), y: IN(280), w: IN(390), h: IN(140), margin: 0 });
  txt(s, "클러스터 규모(GPU/노드 수)·운영 기간·일 수집량: [플레이스홀더: SKT 제공 필요]", 64, 442, 390, 28, { size: 10.5, italic: true, color: GRAY });
  // 우측 스크린샷
  shot(s, 500, 256, 420, 216, "대표 대시보드 화면 — SKT 제공 예정");
  pageNo(s, 3);
  s.addNotes("[1-1 개발 경험 2:30~4:00]\n\"저희는 [YYYY]년부터 해외·해인 GPU 클러스터를 운영해 왔고, [YYYY]년부터는 Observability 솔루션을 자체 개발해 [YYYY]년부터 통합 대시보드로 서비스하고 있습니다. ← 여기서 실제 수치(연도 3건)로 교체 후 발표. 현재 [GPU ○○장, 노드 ○○대] 규모 클러스터에서 [일 ○○건]의 메트릭을 수집·분석하고 있습니다. ← 실제 수치로 교체. 미확보 시 이 문장 통째로 생략 — 임의 언급 금지.\n축적된 역량은 네 가지입니다. 메트릭 수집 파이프라인, GPU 헬스 관리, 통합 대시보드, 그리고 알림·이상 탐지까지 — 우측 실제 운영 화면에서 보시는 그대로입니다.\"\n\n강조: 타임라인 마지막 앰버 노드를 짚으며 \"그리고 지금, 네 번째 변곡점에 와 있습니다\" (5번 복선).\n전환: \"구체적으로 어떤 기능들이 돌아가고 있는지 잠깐 보시겠습니다.\"");
}

/* ============ 슬라이드 4: 주요 기능 ============ */
{
  const s = pres.addSlide();
  header(s, "1-2. SKT Observability 주요 기능");
  gov(s, "수집–분석–시각화–알림에 이르는 핵심 기능을 자체 개발 대시보드로 이미 서비스 중이다");
  shot(s, 40, 118, 560, 210, "① 클러스터 개요 — SKT 제공 예정");
  shot(s, 40, 356, 272, 118, "② GPU 헬스");
  shot(s, 328, 356, 272, 118, "③ 알림 콘솔");
  const colW4 = [92, 140, 68].map(IN);
  const rows4 = [
    hdrRow(["기능 카테고리", "세부 기능", "상태"]),
    [chipCell("메트릭 수집"), cell("GPU·노드 메트릭 파이프라인 (DCGM 기반)", { size: 10.5 }), cell("운영 중 [확인: SKT]", { size: 9.5, fill: NAVY_T, italic: true })],
    [chipCell("GPU 헬스"), cell("온도·ECC·XID 이벤트 추적, 헬스 스코어", { size: 10.5 }), cell("운영 중 [확인: SKT]", { size: 9.5, fill: NAVY_T, italic: true })],
    [chipCell("시각화"), cell("클러스터/노드/잡 단위 통합 대시보드", { size: 10.5 }), cell("운영 중 [확인: SKT]", { size: 9.5, fill: NAVY_T, italic: true })],
    [chipCell("알림·이상 탐지"), cell("임계치·패턴 기반 알림", { size: 10.5 }), cell("운영 중 [확인: SKT]", { size: 9.5, fill: NAVY_T, italic: true })],
    [chipCell("MRM /\nFacility-aware", { size: 10 }), cell("상세는 백업 장표 → 백업 슬라이드 A(14p) 참조", { size: 10, fill: GRAY_T, italic: true }), cell("백업 참조", { size: 10, fill: GRAY_T, italic: true, align: "center" })],
  ];
  s.addTable(rows4, { x: IN(620), y: IN(118), w: IN(300), colW: colW4, border: { color: LINE, pt: 0.75 }, margin: 0.04, rowH: IN(58), valign: "middle" });
  txt(s, "기능별 정량 지표(알림 건수·탐지 정확도 등): [플레이스홀더: SKT 제공 필요]", 40, 500, 600, 16, { size: 10, italic: true, color: GRAY });
  pageNo(s, 4);
  s.addNotes("[1-2 주요 기능 4:00~5:30 — 스킵 후보 2순위]\n\"보시는 화면이 실제 운영 중인 대시보드입니다. 클러스터 개요, GPU 헬스, 알림 콘솔 — DCGM 기반 메트릭 수집부터 온도·ECC·XID 이벤트 추적, 클러스터·노드·잡 단위 시각화, 임계치와 패턴 기반 알림까지, 수집–분석–시각화–알림의 전 단계가 이미 서비스 중입니다. MRM과 Facility 연계 기능 등 세부는 백업 장표에 준비해 두었으니 논의 시간에 필요하시면 보여드리겠습니다.\"\n\n강조: 우측 테이블은 읽지 않는다. 스크린샷은 발표 전 반드시 실물 교체.\n\n★전환(4→5, 핵심 브릿지 ① 자랑→위기감 — 대본 암기):\n\"이렇게만 보면 '잘 하고 있는데 왜 새로 하자는 건가' 하실 수 있습니다. 문제는, 지금까지 잘 해온 이 방식이 앞으로 갈 환경에서는 통하지 않는다는 점입니다.\" — 한 박자 멈추고 넘긴다. 톤을 낮추고 속도를 늦춘다.");
}

/* ============ 슬라이드 5: AI Factory 전환 ============ */
{
  const s = pres.addSlide();
  header(s, "2-1. AI Factory 환경 전환");
  gov(s, "단일 클러스터·VM 중심 관제로는 Multi-DC·Baremetal 기반 AI Factory를 감당할 수 없다 — 업계는 이미 통합 운영이 표준이다", { size: 16 });
  const colW5 = [120, 380, 380].map(IN);
  const t1 = [
    hdrRow(["항목", "As-Is (현행)", "To-Be (AI Factory)"]),
    [chipCell("클러스터 범위"), cell("단일 클러스터 (해외·해인)", { fill: WARN_T }), cell("Multi-DC / Multi-Site 통합 관제", { fill: NAVY_T, bold: true })],
    [chipCell("인프라 형태"), cell("VM 중심", { fill: WARN_T }), cell("Baremetal / Reserved Cloud 혼합", { fill: NAVY_T, bold: true })],
    [chipCell("관제 대상"), cell("Compute(GPU) 중심", { fill: WARN_T }), cell("Compute + Network + Storage + Facility E2E", { fill: NAVY_T, bold: true })],
    [chipCell("운영 모델"), cell("대시보드 기반 수동 운영", { fill: WARN_T }), cell("헬스 자동화·자율 복구·Agentic 운영", { fill: NAVY_T, bold: true })],
  ];
  s.addTable(t1, { x: IN(40), y: IN(110), w: IN(880), colW: colW5, border: { color: LINE, pt: 0.75 }, margin: 0.04, rowH: IN(27), valign: "middle", fontSize: 11 });
  txt(s, "→", 528, 112, 24, 22, { size: 14, bold: true, color: "FFFFFF", align: "center" });
  txt(s, "⚠ Vera Rubin NVL144 CPX 랙 1대 = 8 EFLOPS·고속 메모리 100TB, POD는 5종 목적형 랙이 한 대의 슈퍼컴퓨터로 동작 — 단일 도메인 관제로는 불가", 40, 254, 880, 18, { size: 11, bold: true, color: NAVY });
  txt(s, "업계 벤치마크 — CoreWeave는 이 4개 축을 이미 상품으로 제공 중", 40, 280, 560, 16, { size: 12, bold: true, color: NAVY });
  s.addText([
    { text: "● 완비  ", options: { color: DSX } }, { text: "○ 부분·계획  ", options: { color: AMB } },
    { text: "△ 제한적  ", options: { color: GRAY } }, { text: "✕ 미보유", options: { color: WARN } },
  ].map(r => ({ text: r.text, options: Object.assign({ fontFace: F, fontSize: 10 }, r.options) })), { x: IN(620), y: IN(280), w: IN(300), h: IN(16), align: "right", margin: 0 });
  const colW5b = [186, 260, 148, 286].map(IN);
  function sym(mark, rest, o = {}) {
    const cmap = { "●": DSX, "○": AMB, "△": GRAY, "✕": WARN };
    return { text: [{ text: mark + " ", options: { color: cmap[mark], bold: true, fontFace: F, fontSize: o.size || 10.5 } }, { text: rest, options: { color: T900, fontFace: F, fontSize: o.size || 10.5 } }], options: { valign: "middle", fill: { color: o.fill || "FFFFFF" }, margin: 0.04 } };
  }
  const t2 = [
    [ { text: "벤치마크 축", options: t1[0][0].options }, { text: "CoreWeave 제공 수준", options: t1[0][0].options },
      { text: "SKT 현재", options: t1[0][0].options },
      { text: [{ text: "목표 (DSX OS 협력 후)", options: { color: "FFFFFF", bold: true, fontFace: F, fontSize: 11.5 } }, { text: "\n= 슬라이드 12 로드맵 도달점", options: { color: NAVY_SUB, fontFace: F, fontSize: 9 } }], options: { fill: { color: NAVY }, align: "center", valign: "middle" } } ],
    [chipCell("Observe: 기본 메트릭·대시보드", { size: 10 }), sym("●", "설정 없이 기본 제공 (out-of-the-box)"), sym("△", "클러스터별 자체 구축"), sym("●", "프로비저닝 시 자동 탑재")],
    [chipCell("노드·플릿 수명주기 자동화", { size: 10 }), sym("●", "Mission Control 수명주기 컨트롤러"), sym("✕", "수동 운영 중심"), sym("●", "DSX OS Lifecycle·Resiliency 연동")],
    [chipCell("Telemetry Relay (SIEM 포워딩)", { size: 10 }), sym("●", "암호화 감사·보안 이벤트 포워딩"), sym("✕", "미보유"), sym("●", "Phase 2 도입 완료 (거버넌스 협의 선행)")],
    [chipCell("대화형 AI 에이전트 (운영 질의응답)", { size: 10 }), sym("●", "Slack에서 헬스·인시던트 질의"), sym("✕", "미보유"), sym("●", "MCP 서버 기반 Agentic 운영 (공동)")],
  ];
  s.addTable(t2, { x: IN(40), y: IN(300), w: IN(880), colW: colW5b, border: { color: LINE, pt: 0.75 }, margin: 0.04, rowH: IN(33), valign: "middle" });
  txt(s, "출처: coreweave.com/mission-control, /observability · 'SKT 현재' 판정 [확인: SKT]", 40, 482, 880, 14, { size: 10, color: GRAY, italic: true });
  pageNo(s, 5);
  s.addNotes("[2-1 환경 전환 5:30~7:30 — 절대 스킵 불가]\n\"위 표가 환경의 변화입니다. 지금까지는 단일 클러스터, VM 중심, GPU 중심 관제, 대시보드 보고 사람이 대응하는 운영이었습니다. 앞으로는 Multi-DC 통합 관제, Baremetal 혼합, Compute부터 Facility까지 End-to-end, 그리고 자동 복구까지 가야 합니다.\n규모 감각을 하나만 — Vera Rubin은 랙 하나가 8 엑사플롭스, 고속 메모리 100테라바이트입니다. 다섯 종류의 랙이 묶여 한 대의 슈퍼컴퓨터처럼 동작합니다. 관제 대상의 밀도가 자릿수 단위로 커지는 것이라, GPU만 봐서는 절반도 못 봅니다. (여기까지 15초 이내)\n그리고 업계는 이미 이 수준을 상품으로 제공하고 있습니다. CoreWeave는 기본 메트릭 대시보드, 수명주기 자동화, 보안 텔레메트리 포워딩, 대화형 AI 에이전트 — 이 네 축을 전부 갖추고 있습니다. 저희 현재는 보시는 대로입니다. 오늘 논의드리는 협력의 도달점이 바로 이 네 축을 전부 채우는 것이고, 마지막 로드맵에서 다시 보여드리겠습니다.\"\n\n청중 참여(선택 10초): ✕ 열 짚고 \"이 격차, 체감되시지요?\" — 답변 대기 없음.\n주의: 'SKT 현재' 열 판정은 발표 전 내부 확인 필수.\n전환: \"그럼 그 격차를 무엇으로 채울 것인가 — 저희가 제안하는 전체 그림입니다.\"");
}

/* ============ 슬라이드 6: 목표 아키텍처 (D1) ============ */
{
  const s = pres.addSlide();
  header(s, "2-2. 목표 아키텍처 (안)", { badge: "D1" });
  gov(s, "DSX OS의 Health Automation·MCP 서버·DSX Exchange를 골격으로 Compute–Network–Storage–Facility를 관통하는 E2E 구조를 제안한다", { size: 15.5 });
  const SC = { DSX: [DSX_T, DSX, "3E6300"], SKT: [NAVY_T, NAVY, NAVY], JOINT: [AMB_T, AMB, "8A5000"] };
  function node(x, y, w, h, label, kind, size) {
    const [f, l, tc] = SC[kind];
    box(s, x, y, w, h, { fill: f, lineColor: l, lineW: 1.25 });
    txt(s, label, x + 4, y + 2, w - 8, h - 4, { size: size || 10, bold: true, color: tc, align: "center", valign: "middle", lsp: 1.05 });
  }
  function band(y, h, n, label) {
    box(s, 60, y, 800, h, { fill: "FFFFFF", lineColor: LINE });
    s.addShape("ellipse", { x: IN(68), y: IN(y + h / 2 - 9), w: IN(18), h: IN(18), fill: { color: NAVY }, line: { type: "none" } });
    txt(s, String(n), 68, y + h / 2 - 9, 18, 18, { size: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
    txt(s, label, 92, y + 3, 130, h - 6, { size: 10.5, bold: true, color: NAVY, valign: "middle", lsp: 1.05 });
  }
  band(116, 52, 5, "시각화·Agentic\n운영");
  node(232, 124, 300, 36, "E2E 통합 대시보드", "SKT", 11);
  node(560, 124, 288, 36, "대화형 운영 AI 에이전트", "JOINT", 11);
  arrow(s, 532, 142, 560, 142, { dash: "dash" });
  band(178, 52, 4, "분석");
  node(232, 186, 152, 36, "Health Automation\nResiliency", "DSX", 9);
  node(390, 186, 152, 36, "이상 탐지·성능\n저하 분석", "SKT", 9);
  node(548, 186, 120, 36, "장애 예측", "SKT", 9.5);
  node(674, 186, 174, 36, "크로스 도메인 상관분석\n(MCP 서버 카탈로그)", "JOINT", 8.5);
  band(240, 42, 3, "저장");
  node(232, 246, 616, 30, "시계열 DB · 메트릭/이벤트 저장소", "SKT", 10.5);
  band(292, 42, 2, "수집 파이프라인");
  node(232, 298, 616, 30, "OpenTelemetry Collector 기반 통합 파이프라인", "JOINT", 10.5);
  band(344, 62, 1, "수집 소스\n(4개 도메인)");
  node(232, 352, 118, 46, "DCGM\n(GPU In-band)", "DSX", 9);
  node(356, 352, 124, 46, "BMC + Redfish\n수집기 (OOB)", "SKT", 9);
  node(486, 352, 122, 46, "BlueField DPU\n텔레메트리 오프로드", "JOINT", 8.5);
  node(614, 352, 116, 46, "UFM / Spectrum\n패브릭 텔레메트리", "DSX", 8.5);
  node(736, 352, 112, 46, "DSX Exchange\n(MQTT 전력·열)", "DSX", 8.5);
  [291, 418, 547, 672, 792].forEach((x) => arrow(s, x, 352, x, 328, {}));
  arrow(s, 540, 298, 540, 276, {});
  [308, 466, 608, 761].forEach((x) => arrow(s, x, 246, x, 222, {}));
  [308, 466, 608].forEach((x) => arrow(s, x, 186, x, 160, {}));
  arrow(s, 761, 186, 704, 160, {});
  txt(s, "Compute · Network · Storage · Facility", 862, 344, 58, 66, { size: 8, color: GRAY, lsp: 1.2 });
  legend3(s, 60, 418);
  txt(s, "DSX OS: 2026-05 GTC Taipei 발표, 오픈소스·모듈러 — Lifecycle·Runtime Consistency·Health Automation·Resiliency·Multi-tenant·AI Platform Services 6개 모듈 (상세: 백업 B, 15p)", 60, 440, 800, 28, { size: 9.5, color: GRAY });
  pageNo(s, 6);
  s.addNotes("[2-2 목표 아키텍처 D1 7:30~10:00 — 절정 1, 절대 스킵 불가]\n\"이것이 제안드리는 전체 구조입니다. 다섯 개 층인데, 아래에서 위로 보시면 됩니다.\n비유로 먼저 — 종합병원의 환자 모니터링과 같습니다. 맨 아래 1층이 환자 몸에 붙는 각종 센서, 2층이 그 신호를 한데 모으는 배선, 3층이 진료 기록 보관, 4층이 의사의 진단, 맨 위 5층이 간호사 스테이션의 통합 모니터와 응급 호출 시스템입니다. 지금까지는 장비마다 따로 봤다면, 이제 병원 전체를 한 화면에서 보자는 것입니다.\n(1층) 수집층에는 GPU를 보는 DCGM, 서버가 죽어도 동작하는 BMC 수집기, DPU 오프로드, 네트워크의 UFM, 전력·냉각의 DSX Exchange까지 — 네 도메인이 전부 들어옵니다. (2~3층) OpenTelemetry 표준 파이프라인으로 모아 시계열 저장소에 쌓고, (4층) DSX OS의 Health Automation과 저희가 개발하는 이상 탐지·장애 예측·상관분석이 돌아가며, (5층) 통합 대시보드와 대화형 운영 AI 에이전트로 올라갑니다.\n색을 봐 주십시오. 초록은 DSX OS 기본 제공, 파랑은 SKT 개발, 주황은 공동 개발입니다. 골격은 DSX OS가 제공하고, 저희는 잘하는 분석과 시각화에 집중한다 — 이것이 오늘 첫 번째 결정 D1입니다.\"\n\n강조: 우상단 D1 배지 짚기. DSX OS 6모듈 캡션은 질문 시만 활용.\n전환: \"구조를 채택한다면, 다음 질문은 '그 안에서 누가 어디까지 만드나'입니다.\"");
}

/* ============ 슬라이드 7: 범위 매트릭스 (D2) ============ */
{
  const s = pres.addSlide();
  header(s, "2-3. 개발·연동 범위 및 역할 분담 (안)", { badge: "D2" });
  gov(s, "DSX OS 제공 영역과 SKT 개발 영역의 경계를 이렇게 나누는 것을 제안한다 — 이 경계 확정이 오늘의 첫 번째 결정이다", { size: 16 });
  const colW7 = [128, 168, 150, 168, 120, 146].map(IN);
  function mc(kind, label, body, o = {}) { // matrix cell
    const map = { DSX: [DSX_T, "3E6300", "DSX"], SKT: [NAVY_T, NAVY, "SKT"], JOINT: [AMB_T, "8A5000", "공동"], NONE: [GRAY_T, GRAY, ""] };
    const [f, tc, tag] = map[kind];
    const runs = [];
    if (tag) runs.push({ text: tag + " · ", options: { bold: true, color: tc, fontFace: F, fontSize: o.size || 9.5 } });
    runs.push({ text: body, options: { color: kind === "NONE" ? GRAY : T900, italic: kind === "NONE", fontFace: F, fontSize: o.size || 9.5 } });
    if (o.star) runs.push({ text: " ★", options: { bold: true, color: AMB, fontFace: F, fontSize: 10.5 } });
    return { text: runs, options: { fill: { color: f }, valign: "middle", margin: 0.03 } };
  }
  const t7 = [
    hdrRow(["도메인 \\ 기능", "수집", "파이프라인·저장", "분석", "시각화", "자동 복구"]),
    [chipCell("Compute (GPU·노드)", { size: 10 }), mc("DSX", 0, "DCGM·Health Automation 통합"), mc("JOINT", 0, "OTel 파이프라인 / SKT 시계열 DB"), mc("SKT", 0, "이상 탐지·장애 예측·잡 상관", { star: true }), mc("SKT", 0, "통합 대시보드"), mc("DSX", 0, "Resiliency 모듈", { star: true })],
    [chipCell("Network (패브릭)", { size: 10 }), mc("DSX", 0, "UFM·Spectrum 텔레메트리"), mc("NONE", 0, "(공통 파이프라인 공용)"), mc("JOINT", 0, "패브릭-잡 상관분석"), mc("SKT", 0, "통합 대시보드"), mc("DSX", 0, "Resiliency")],
    [chipCell("Storage", { size: 10 }), mc("JOINT", 0, "BlueField STX·NVMe-oF 텔레메트리"), mc("NONE", 0, "(공통 파이프라인 공용)"), mc("SKT", 0, "I/O 병목·용량 분석"), mc("SKT", 0, "통합 대시보드"), mc("DSX", 0, "Resiliency", { star: true })],
    [chipCell("Facility (전력·냉각)", { size: 10 }), mc("DSX", 0, "DSX Exchange (MQTT)"), mc("NONE", 0, "(공통 파이프라인 공용)"), mc("JOINT", 0, "Facility-aware 상관 (SKT 경험 접목)"), mc("SKT", 0, "통합 대시보드"), mc("JOINT", 0, "공동 운영 절차", { star: true })],
    [chipCell("OOB 관측면 (횡단)", { size: 10 }), mc("SKT", 0, "BMC+Redfish 수집기"), mc("NONE", 0, "(공통 파이프라인 공용)"), mc("SKT", 0, "HW 장애 분석"), mc("SKT", 0, "통합 대시보드"), mc("NONE", 0, "— (수동 절차 유지)")],
  ];
  s.addTable(t7, { x: IN(40), y: IN(110), w: IN(880), colW: colW7, border: { color: LINE, pt: 0.75 }, margin: 0.03, rowH: IN(48), valign: "middle" });
  s.addText([
    { text: "★ 오늘 논의 필요 4건 — ", options: { bold: true, color: AMB, fontSize: 11.5 } },
    { text: "① Compute 분석: 기존 분석 모델 재활용 범위  ② Compute 자동 복구: Resiliency 개입 수준(잡 재시작 허용선)\n③ Storage 자동 복구: STX 랙 복구 권한 경계  ④ Facility 자동 복구: IT/OT 경계의 책임 소재(안전 규제)", options: { color: T900, fontSize: 10 } },
  ].map(r => ({ text: r.text, options: Object.assign({ fontFace: F }, r.options) })), { x: IN(40), y: IN(408), w: IN(560), h: IN(56), margin: 0, valign: "top" });
  box(s, 620, 406, 300, 62, { round: true, rad: 8, fill: "FFFFFF", lineColor: LINE });
  navyTab(s, 634, 398, 50, "요약");
  s.addText([
    { text: "주체 지정 20셀 중 SKT 단독 9 · DSX 6 · 공동 5(분할 포함) · 논의 필요 ★4", options: { bold: true, fontSize: 10 } },
    { text: " → 개발 총량의 절반 이상(11/20)을 DSX OS·공동 영역이 흡수", options: { fontSize: 10 } },
  ].map(r => ({ text: r.text, options: Object.assign({ fontFace: F, color: T900 }, r.options) })), { x: IN(634), y: IN(416), w: IN(274), h: IN(48), margin: 0 });
  legend3(s, 40, 476);
  txt(s, "총 25셀 = 주체 지정 20 + 공용 4 + 해당 없음 1 (★는 오버레이)", 620, 476, 300, 14, { size: 9, color: GRAY });
  pageNo(s, 7);
  s.addNotes("[2-3 범위·역할 분담 D2 10:00~12:30 — 첫 결정 요청, 절대 스킵 불가]\n\"표가 복잡해 보이지만 읽는 법은 간단합니다. 색만 봐 주십시오. 수집과 자동 복구는 대부분 초록 — DSX OS가 제공합니다. 분석과 시각화는 대부분 파랑 — 저희가 개발합니다. 그 접점이 주황 — 공동 개발입니다. 주체가 지정된 20개 영역 중 SKT 단독 개발은 9개입니다. 개발 총량의 절반 이상을 DSX OS와 공동 영역이 흡수하는 구조라, 전면 자체 개발 대비 공수와 리스크가 크게 줄어듭니다.\n다만 별표 네 곳은 오늘 여러분의 의견이 필요합니다. 첫째, 기존 분석 모델을 어디까지 재활용할지. 둘째, 자동 복구가 잡을 자동 재시작하는 것을 어디까지 허용할지. 셋째, 스토리지 랙 복구 권한을 어디까지 NVIDIA 쪽 모듈에 줄지. 넷째, 전력·냉각처럼 안전 규제가 걸리는 IT/OT 경계의 책임 소재입니다.\"\n\n★청중 참여(30초, 필수): \"이 네 가지 중 지금 바로 방향을 주실 수 있는 항목이 있으십니까? 특히 자동 복구 허용 수준은 운영 철학의 문제라 임원분들 판단이 중요합니다.\" 의견이 나오면 12페이지에서 확정 문구로 정리. 5분 이상 길어지면 Discussion으로 커트.\n전환: \"예상 질문 — 'Mission Control이 이미 있는데 우리가 뭘 만드나, 종속되는 것 아니냐.' 그 답이 다음 장입니다.\"");
}

/* ============ 슬라이드 8: (참고) Open Architecture ============ */
{
  const s = pres.addSlide();
  s.background = { color: "F7F8FA" };
  header(s, "2-4. NVIDIA Open Architecture", { gray: true, refBadge: true });
  gov(s, "DSX OS는 오픈·모듈러 구조로, Mission Control·OpenTelemetry와 표준 인터페이스로 연동된다 — 락인 리스크가 낮다", { color: G374, size: 16 });
  function nbox(x, y, w, h, t) {
    box(s, x, y, w, h, { fill: "FFFFFF", lineColor: "B9BFC7" });
    txt(s, t, x + 6, y + 2, w - 12, h - 4, { size: 10, color: G374, align: "center", valign: "middle", lsp: 1.1 });
  }
  box(s, 50, 130, 280, 250, { fill: "FFFFFF", lineColor: GRAY });
  txt(s, "NVIDIA Mission Control (상용 제어면)", 58, 138, 264, 18, { size: 12.5, bold: true, color: G374 });
  nbox(66, 168, 248, 56, "BCM · Run:ai 스케줄러");
  nbox(66, 234, 248, 56, "DCGM 텔레메트리 · UFM · NMX");
  nbox(66, 300, 248, 62, "Grafana 통합 대시보드 · 자율 복구 엔진");
  box(s, 380, 130, 280, 250, { fill: "FFFFFF", lineColor: GRAY });
  txt(s, "DSX OS (오픈소스 · 모듈러)", 388, 138, 264, 18, { size: 12.5, bold: true, color: G374 });
  nbox(396, 168, 248, 56, "도메인별 MCP 서버\n(프로비저닝·네트워킹·Observability)");
  nbox(396, 234, 248, 56, "DSX Exchange (MQTT IT/OT 허브)");
  nbox(396, 300, 248, 62, "Health Automation · Lifecycle");
  box(s, 710, 200, 200, 100, { fill: NAVY_T, lineColor: NAVY, lineW: 2 });
  txt(s, "SKT 개발 레이어\n파이프라인·분석·대시보드", 716, 210, 188, 80, { size: 12, bold: true, color: NAVY, align: "center", valign: "middle" });
  arrow(s, 330, 250, 380, 250, { dash: "dash", both: true, color: GRAY });
  txt(s, "표준 텔레메트리 (DCGM·UFM)", 230, 384, 250, 16, { size: 9.5, color: GRAY, align: "center" });
  arrow(s, 660, 250, 710, 250, { dash: "dash", both: true, color: GRAY });
  s.addText([
    { text: "OpenTelemetry · MCP · Redfish ", options: { fontFace: F, fontSize: 9.5, color: GRAY } },
    { text: "표준", options: { fontFace: F, fontSize: 9.5, bold: true, color: G374 } },
  ], { x: IN(570), y: IN(384), w: IN(230), h: IN(16), align: "center", margin: 0 });
  txt(s, "Mirantis, OpenNebula, Rafay, Red Hat, Spectro Cloud, Supermicro, Vultr, vCluster 등 8개 이상 벤더가 이미 DSX OS 컴포넌트 채택 — NVIDIA 단독 기술이 아닌 산업 생태계\nRedfish = DMTF 산업 표준 (JSON over HTTPS) · OpenTelemetry = CNCF 표준", 50, 412, 860, 44, { size: 10, color: GRAY, lsp: 1.3 });
  txt(s, "본 장표는 참고용입니다", 50, 470, 300, 14, { size: 10, italic: true, color: GRAY });
  pageNo(s, 8);
  s.addNotes("[2-4 (참고) Open Architecture 12:30~13:30 — 스킵 후보 1순위 (30초 통과 가능)]\n\"이 장은 참고입니다. 왼쪽이 NVIDIA의 상용 제어면인 Mission Control, 가운데가 오픈소스인 DSX OS, 오른쪽 파란 박스가 저희가 만드는 레이어입니다. 화면에서 색이 있는 건 저 파란 박스 하나뿐입니다 — 저희가 만드는 것은 딱 이 부분이고, 나머지는 이미 있는 것을 표준 인터페이스로 연동합니다. 연결 고리는 전부 표준입니다. Redfish는 DMTF 산업 표준이고 OpenTelemetry는 CNCF 표준입니다. DSX OS는 Red Hat, Supermicro를 포함해 8개 이상 벤더가 채택한 생태계라, 특정 벤더에 갇히는 구조가 아닙니다.\"\n\n강조: SKT 파란 박스를 마지막에 짚는다. BCM·Run:ai 등 세부는 읽지 않는다.\n\n★전환(8→9, 핵심 브릿지 ② 참고→실행 — 대본 암기):\n\"배경 설명은 여기까지입니다. 이제부터는 '그래서 실제로 무엇을, 어떻게 개발하느냐' — 도메인별 실행 방안으로 들어가겠습니다. 가장 핵심인 Compute부터입니다.\" — 톤을 다시 올리고 속도감 있게.");
}

/* ============ 슬라이드 9: Compute 개발 방안 ============ */
{
  const s = pres.addSlide();
  header(s, "3-1. Compute Observability");
  gov(s, "GPU·노드 레벨 텔레메트리를 DCGM 기반으로 수집하고, 장애 예측·잡 상관분석까지 확장한다");
  const SC = { DSX: [DSX_T, DSX, "3E6300"], SKT: [NAVY_T, NAVY, NAVY], JOINT: [AMB_T, AMB, "8A5000"] };
  function card(x, y, w, h, title, body, kind, o = {}) {
    const [f, l, tc] = SC[kind];
    box(s, x, y, w, h, { round: true, rad: 6, fill: f, lineColor: l, lineW: 1.25 });
    txt(s, title, x + 10, y + 6, w - 20, 18, { size: o.ts || 11, bold: true, color: tc });
    txt(s, body, x + 10, y + 24, w - 20, h - 30, { size: o.bs || 9.5, color: T900, lsp: 1.15 });
  }
  box(s, 40, 118, 330, 292, { fill: "FFFFFF", lineColor: LINE });
  chipRect(s, 54, 110, 76, 18, "수집 영역", { bold: true });
  card(56, 140, 298, 80, "GPU 텔레메트리 (DCGM)", "사용률·메모리·온도·전력·ECC·XID 이벤트·클럭", "DSX");
  card(56, 228, 298, 80, "노드 헬스", "CPU·메모리·NVLink·PCIe·NIC 상태", "DSX");
  card(56, 316, 298, 80, "잡/워크로드 메타", "스케줄러 잡 ID·큐·테넌트·자원 할당", "JOINT");
  box(s, 420, 118, 500, 292, { fill: "FFFFFF", lineColor: LINE });
  txt(s, "분석 파이프라인 (SKT 개발)", 436, 126, 300, 18, { size: 12.5, bold: true, color: NAVY });
  card(440, 152, 220, 76, "A1. 이상 탐지", "임계치+패턴 기반", "SKT");
  card(682, 152, 220, 76, "A2. 성능 저하 진단", "스트래글러·스로틀링", "SKT");
  card(682, 252, 220, 76, "A3. 장애 예측", "ECC/XID 선행 신호", "SKT");
  card(440, 252, 220, 76, "A4. 잡-인프라 상관분석", "잡 실패 원인 자동 추적", "SKT");
  arrow(s, 660, 190, 682, 190, { color: NAVY, w: 2 });
  arrow(s, 792, 228, 792, 252, { color: NAVY, w: 2 });
  arrow(s, 682, 290, 660, 290, { color: NAVY, w: 2 });
  arrow(s, 370, 190, 440, 190, {});
  arrow(s, 370, 356, 550, 328, {});
  box(s, 40, 422, 880, 30, { round: true, rad: 6, fill: "FFFFFF", lineColor: LINE });
  s.addText([
    { text: " SKT ", options: { color: "FFFFFF", bold: true, highlight: NAVY } }, { text: " 분석 모델 4종 — 기존 자산 재활용 [확인: SKT]    ", options: {} },
    { text: " 공동 ", options: { color: "FFFFFF", bold: true, highlight: AMB } }, { text: " 잡 메타 연계 커넥터    ", options: {} },
    { text: " DSX ", options: { color: "FFFFFF", bold: true, highlight: DSX } }, { text: " DCGM·Health Automation은 DSX OS 통합분 활용", options: {} },
  ].map(r => ({ text: r.text, options: Object.assign({ fontFace: F, fontSize: 10.5, color: T900 }, r.options) })), { x: IN(56), y: IN(422), w: IN(850), h: IN(30), valign: "middle", margin: 0 });
  txt(s, "XID·ECC 이벤트는 GPU 장애의 대표 선행 신호 — In-band(DCGM)로만 수집 가능한 깊이 → 다음 장: 수집 전략 ▶", 40, 458, 700, 16, { size: 11, bold: true, color: NAVY });
  txt(s, "분석 정확도·기존 모델 성능: [플레이스홀더: SKT 제공 필요]", 40, 478, 500, 14, { size: 10, italic: true, color: GRAY });
  pageNo(s, 9);
  s.addNotes("[3-1 Compute 13:30~15:00]\n\"Compute는 세 영역에서 수집합니다. DCGM으로 GPU의 사용률·메모리·온도·전력, 그리고 ECC 오류와 XID 이벤트까지. 노드 레벨에서는 CPU·NVLink·PCIe 상태. 그리고 스케줄러에서 잡 메타데이터를 받아옵니다. 분석은 네 단계 — 이상 탐지, 성능 저하 진단, 장애 예측, 그리고 잡이 실패했을 때 인프라 원인을 자동 추적하는 상관분석까지 갑니다. 이 분석 네 가지는 전부 파란색, 즉 저희 개발 영역인데, 상당 부분 기존 운영에서 쓰던 분석 모델을 재활용합니다. 기존 모델의 성능은 [탐지 정확도 ○○% 등]입니다. ← 실제 수치로 교체. 미확보 시 '재활용합니다'에서 문장 종료.\n한 가지 짚을 점 — 장애 예측의 핵심 선행 신호인 XID·ECC 이벤트는 GPU 내부 정보라서, 호스트를 경유하는 In-band 방식으로만 깊게 수집할 수 있습니다.\"\n\n전환: \"그런데 In-band에는 치명적인 약점이 하나 있습니다. 호스트가 죽으면 관측도 같이 죽는다는 것입니다. 그래서 수집 전략이 필요합니다.\"");
}

/* ============ 슬라이드 10: 수집 전략 (D3) ============ */
{
  const s = pres.addSlide();
  header(s, "3-2. 수집 전략 (In-band·OOB·DPU)", { badge: "D3" });
  gov(s, "In-band와 Out-of-band를 병행하되, BlueField DPU 오프로드로 무부하 관측면을 확보하는 하이브리드 전략을 제안한다", { size: 16 });
  const colW10 = [90, 263, 263, 264].map(IN);
  const S10 = (t, o = {}) => cell(t, Object.assign({ size: 9.5 }, o));
  function hz(mark, rest) {
    const cmap = { "○": DSX, "✕": WARN };
    return { text: [{ text: mark + " ", options: { color: cmap[mark], bold: true, fontFace: F, fontSize: 9.5 } }, { text: rest, options: { color: T900, fontFace: F, fontSize: 9.5 } }], options: { valign: "middle", fill: { color: "FFFFFF" }, margin: 0.03 } };
  }
  const navyCell = (t) => cell(t, { fill: NAVY, color: "FFFFFF", bold: true, size: 10 });
  const t10 = [
    hdrRow(["구분", "In-band", "Out-of-band (OOB)", "DPU 오프로드"]),
    [chipCell("수집 경로", { size: 9.5 }), S10("호스트 OS·드라이버 경유"), S10("BMC 경유, 별도 관리망 (호스트 미경유)"), S10("BlueField DPU 자체 (자체 BMC 포함, 별도 OOB 관리망)")],
    [chipCell("대표 기술", { size: 9.5 }), S10("nvidia-smi, DCGM"), S10("BMC + Redfish (DMTF 표준, JSON/HTTPS), IPMI SEL"), S10("BlueField-4 텔레메트리, DOCA")],
    [chipCell("수집 데이터", { size: 9.5 }), S10("GPU 사용률·메모리·ECC·XID·클럭 등 세밀 메트릭"), S10("보드·흡기 센서, 전력, SEL 로그, FRU, 원격 전원 제어"), S10("네트워크 플로·스토리지(NVMe-oF)·보안 텔레메트리")],
    [chipCell("강점", { size: 9.5 }), S10("메트릭 가장 풍부, 잡 상관분석 용이"), S10("호스트 다운 상태에서도 동작, OOB 펌웨어 업데이트", { bold: true }), S10("호스트 자원 소모 없음 (무부하 관측면)", { bold: true })],
    [chipCell("한계", { size: 9.5 }), S10("호스트 다운 시 함께 소실, 워크로드에 (미미한) 오버헤드"), S10("메트릭 깊이 제한 (GPU 내부 상태 불가)"), S10("DPU 탑재 노드 전제 (Vera Rubin POD 구성 포함 — 탑재 범위 NVIDIA 확인 필요)")],
    [chipCell("호스트 장애 시", { size: 9.5 }), hz("✕", "관측 불가"), hz("○", "관측·원격 복구 지원"), hz("○", "독립 동작")],
    [navyCell("적용 (안)"), navyCell("성능·잡 분석의 주 수집면"), navyCell("장애·전원·펌웨어 관리 관측면"), navyCell("네트워크·스토리지·보안 무부하 관측면")],
  ];
  s.addTable(t10, { x: IN(40), y: IN(110), w: IN(880), colW: colW10, border: { color: LINE, pt: 0.75 }, margin: 0.03, rowH: IN(33), valign: "middle" });
  // 하단 개념도
  box(s, 40, 388, 400, 96, { fill: "FFFFFF", lineColor: LINE });
  txt(s, "호스트 노드", 48, 390, 100, 14, { size: 9.5, bold: true, color: GRAY_D });
  box(s, 52, 408, 180, 66, { fill: GRAY_T, lineColor: "B9BFC7" });
  txt(s, "GPU·CPU\n(워크로드 전용 — 관측 부하 0)", 56, 412, 172, 58, { size: 9.5, color: GRAY_D, align: "center", valign: "middle" });
  box(s, 244, 408, 186, 66, { fill: AMB_T, lineColor: AMB, lineW: 1.25 });
  txt(s, "BlueField-4 DPU\n패킷·암복호화·NVMe-oF·텔레메트리 오프로드", 248, 410, 178, 62, { size: 9, bold: true, color: "8A5000", align: "center", valign: "middle" });
  box(s, 500, 392, 170, 40, { fill: NAVY_T, lineColor: NAVY });
  txt(s, "OOB 관리망 (Redfish)", 504, 392, 162, 40, { size: 9.5, bold: true, color: NAVY, align: "center", valign: "middle" });
  box(s, 500, 442, 170, 40, { fill: NAVY_T, lineColor: NAVY });
  txt(s, "수집 파이프라인 (6p ②층)", 504, 442, 162, 40, { size: 9.5, bold: true, color: NAVY, align: "center", valign: "middle" });
  arrow(s, 434, 462, 500, 462, { color: NAVY, w: 2 });
  txt(s, "인프라 텔레메트리", 436, 470, 90, 14, { size: 8.5, color: GRAY });
  arrow(s, 430, 412, 500, 412, { dash: "dash", both: true, color: GRAY });
  txt(s, "수명주기 관리", 434, 396, 70, 14, { size: 8.5, color: GRAY });
  box(s, 700, 388, 220, 96, { round: true, rad: 8, fill: "FFFFFF", lineColor: LINE });
  navyTab(s, 714, 380, 44, "비유");
  txt(s, "In-band = 차량 계기판\nOOB = 외부 블랙박스\nDPU = 차에 탑재된 독립 진단 컴퓨터", 714, 404, 194, 72, { size: 10.5, italic: true, color: GRAY_D, lsp: 1.3 });
  txt(s, "BlueField-4는 패킷 처리·암복호화·vSwitch·NVMe-oF까지 오프로드 — 관측이 워크로드 성능을 갉아먹지 않는 구조", 40, 492, 640, 14, { size: 9.5, color: GRAY });
  pageNo(s, 10);
  s.addNotes("[3-2 수집 전략 D3 15:00~17:00 — 비유 필수 사용]\n\"수집 경로는 세 가지가 있고, 결론부터 말씀드리면 셋 다 씁니다. (맨 아래 네이비 행 먼저 포인팅)\n비유로 설명드리겠습니다. In-band는 자동차의 계기판입니다. 속도·연료·엔진 상태까지 가장 풍부하게 보여주지만, 차 시동이 꺼지면 계기판도 같이 꺼집니다. Out-of-band는 외부에 달린 블랙박스입니다. 계기판만큼 세밀하진 않지만, 차가 완전히 멈춘 상태에서도 무슨 일이 있었는지 기록하고, 원격으로 시동을 다시 걸 수도 있습니다. 그리고 DPU는 차에 탑재된 독립 진단 컴퓨터입니다. 워크로드의 성능을 전혀 갉아먹지 않으면서 별도 전원으로 차량 상태를 계속 진단합니다.\n(호스트 장애 시 행 포인팅) 실제로 호스트가 죽었을 때 In-band는 관측 불가, OOB와 DPU는 살아 있습니다. 고가의 GPU 서버가 죽은 순간이 가장 봐야 하는 순간입니다. 그래서 제안은 — In-band를 성능·잡 분석의 주 수집면으로, OOB를 장애·전원 관리 관측면으로, Vera Rubin POD 구성에 포함되는 BlueField DPU를 무부하 관측면으로 병행하는 하이브리드입니다. 이것이 세 번째 결정 D3의 전반부입니다.\"\n\n강조: 비유 3문장은 비기술 임원 쪽을 보며. 테이블 세부 행은 읽지 않는다.\n전환: \"Compute의 수집 전략이 이렇다면, 나머지 세 도메인은 어떻게 하느냐 — 다음 장입니다.\"");
}

/* ============ 슬라이드 11: Network·Storage·Facility (D3) ============ */
{
  const s = pres.addSlide();
  header(s, "3-3. Network·Storage·Facility 통합", { badge: "D3" });
  gov(s, "나머지 3개 도메인은 DSX Exchange·UFM 등 기존 소스를 연동하는 방식으로 단계적으로 통합한다");
  const cards = [
    ["Network", "1", DSX, DSX_T, [
      ["연동 소스", "UFM(Unified Fabric Manager), Spectrum-6 SPX 텔레메트리 · BlueField DPU 플로 데이터"],
      ["수집 항목", "패브릭 토폴로지·링크 상태, 혼잡/오류 카운터, 플로 단위 트래픽"],
      ["개발 항목", "패브릭-잡 상관분석 (잡 성능 저하 ↔ 네트워크 혼잡 매핑) — 공동"],
    ], "잡 성능 직결 + UFM 텔레메트리 표준화로 연동 리스크 낮음"],
    ["Storage", "2", AMB, AMB_T, [
      ["연동 소스", "BlueField-4 STX 스토리지 랙 텔레메트리, NVMe-oF 성능 카운터"],
      ["수집 항목", "I/O 지연·대역폭, 용량·내구성, 스토리지 패브릭 상태"],
      ["개발 항목", "I/O 병목 분석, 체크포인트 쓰기 패턴 분석 — SKT"],
    ], "STX 랙 인터페이스 성숙도 확인 필요 → Network 이후"],
    ["Facility", "3", GRAY, GRAY_T, [
      ["연동 소스", "DSX Exchange (MQTT 기반 IT/OT 허브)"],
      ["수집 항목", "전력 이상·그리드 이벤트, 열(thermal)·냉각 상태"],
      ["개발 항목", "Facility-aware 상관분석 (SKT 기존 경험 접목 [확인: SKT]), 전력-워크로드 연계 — 공동"],
    ], "IT/OT 경계의 안전·책임 이슈 협의 선행 (7p ★4 연동)"],
  ];
  cards.forEach(([name, ph, c, ct, secs, basis], i) => {
    const x = 40 + i * 300;
    box(s, x, 118, 278, 296, { round: true, rad: 8, fill: "FFFFFF", lineColor: c, lineW: 1.5 });
    box(s, x, 118, 278, 30, { round: true, rad: 8, fill: NAVY });
    txt(s, name, x + 14, 118, 180, 30, { size: 13, bold: true, color: "FFFFFF", valign: "middle" });
    s.addShape("ellipse", { x: IN(x + 234), y: IN(106), w: IN(36), h: IN(36), fill: { color: ct }, line: { color: c, width: 1.5 } });
    txt(s, ph, x + 234, 106, 36, 36, { size: 20, bold: true, color: c === GRAY ? GRAY_D : c, align: "center", valign: "middle" });
    let sy = 156;
    secs.forEach(([lab, body]) => {
      chipRect(s, x + 12, sy, 64, 16, lab, { size: 9.5 });
      txt(s, body, x + 12, sy + 19, 254, 46, { size: 9.5, color: T900, lsp: 1.12 });
      sy += 68;
    });
    txt(s, "Phase 근거: " + basis, x + 12, 372, 254, 38, { size: 9, italic: true, color: GRAY, lsp: 1.1 });
    if (i < 2) txt(s, "▶", x + 282, 250, 16, 20, { size: 12, color: PGC, align: "center" });
  });
  box(s, 40, 434, 880, 32, { round: true, rad: 6, fill: DSX_T });
  s.addText([
    { text: "3개 도메인 모두 DSX OS·Vera Rubin이 이미 노출하는 텔레메트리 소스를 연동하는 방식 → 신규 수집기 개발 최소화", options: { bold: true, fontSize: 11.5, color: "3E6300" } },
    { text: "   Phase별 기간: [플레이스홀더: 12p 로드맵 확정 후 기입]", options: { italic: true, fontSize: 9.5, color: GRAY } },
  ].map(r => ({ text: r.text, options: Object.assign({ fontFace: F }, r.options) })), { x: IN(56), y: IN(434), w: IN(850), h: IN(32), valign: "middle", margin: 0 });
  legend3(s, 40, 478);
  pageNo(s, 11);
  s.addNotes("[3-3 Network·Storage·Facility D3 17:00~18:30 — 시간 부족 시 Phase 1→2→3만]\n\"나머지 세 도메인은 새로 수집기를 만드는 게 아니라, DSX OS와 Vera Rubin이 이미 노출하는 텔레메트리 소스를 연동하는 방식입니다. 그래서 단계적으로 갑니다.\n1단계 네트워크 — 잡 성능에 가장 직결되고 UFM 텔레메트리가 이미 표준화되어 있어 리스크가 낮습니다. 2단계 스토리지 — BlueField 스토리지 랙의 인터페이스 성숙도를 확인하며 갑니다. 3단계 Facility — 전력·냉각은 안전과 책임 문제가 걸려 있어, 아까 별표에서 보신 IT/OT 경계 협의를 먼저 하고 들어갑니다. 이 순서 확정이 D3의 후반부입니다.\"\n\n강조: 카드 내부는 읽지 않는다 — Phase 배지 1→2→3과 근거 1줄씩만.\n\n★전환(11→12, 핵심 브릿지 ③ 기술→결정 — 대본 암기):\n\"여기까지가 기술적인 그림 전부입니다. 이제 남은 것은 여러분의 결정입니다.\" — 물리적으로도 모드 전환(리모컨 내려놓기 등). 한 박자 쉬고 넘긴다.");
}

/* ============ 슬라이드 12: 결정 요청 및 다음 단계 ============ */
{
  const s = pres.addSlide();
  header(s, "4-1. 결정 요청 사항 및 다음 단계", { wideBadge: "☐ → ☑ 오늘 확정" });
  gov(s, "오늘 3가지를 확정해 주시면, 즉시 NVIDIA와 공동 설계 협의에 착수하겠다");
  decisionCard(s, 40, 114, 283, 104, "D1. 아키텍처 방향", "DSX OS 골격 E2E 레이어드 아키텍처 채택", "근거: 슬라이드 6");
  decisionCard(s, 339, 114, 283, 104, "D2. 개발·연동 범위", "범위 매트릭스 기준 역할 분담 확정 — ★4개 항목 포함", "근거: 슬라이드 7");
  decisionCard(s, 638, 114, 283, 104, "D3. 수집 전략·단계화", "하이브리드 수집 전략 + Phase 순서 (Network→Storage→Facility) 확정", "근거: 슬라이드 10·11");
  const phases = [
    ["Phase 0", "NVIDIA 공동 설계 워크숍 — 아키텍처 상세화·인터페이스 정의", "확정 직후 착수 [분기 미정]", AMB_T, "8A5000"],
    ["Phase 1", "Compute PoC — In-band+OOB 수집, 기본 대시보드", "[플레이스홀더: 분기]", NAVY_T, NAVY],
    ["Phase 2", "Network·Storage 통합 + Telemetry Relay(SIEM) 도입", "[플레이스홀더: 분기]", NAVY_T, NAVY],
    ["Phase 3", "Facility 통합 + 대화형 AI 에이전트 (Agentic 운영)", "[플레이스홀더: 분기]", AMB_T, "8A5000"],
  ];
  phases.forEach(([name, body, when, fill, tc], i) => {
    const x = 40 + i * 172;
    s.addShape("chevron", { x: IN(x), y: IN(268), w: IN(178), h: IN(120), fill: { color: fill }, line: { color: tc === NAVY ? NAVY : AMB, width: 1 } });
    txt(s, name, x + 42, 278, 118, 20, { size: 12.5, bold: true, color: tc });
    txt(s, body, x + 42, 300, 116, 56, { size: 9, color: T900, lsp: 1.1 });
    txt(s, when, x + 42, 358, 116, 16, { size: 9, italic: true, color: GRAY });
  });
  box(s, 756, 252, 164, 168, { round: true, rad: 8, fill: DSX_T, lineColor: DSX, lineW: 2 });
  txt(s, "도달점", 768, 260, 140, 16, { size: 11, bold: true, color: "3E6300" });
  txt(s, "CoreWeave 동등 수준의\n모니터링/분석 환경", 768, 278, 140, 36, { size: 11.5, bold: true, color: T900, lsp: 1.1 });
  txt(s, "[플레이스홀더: 목표 분기]", 768, 316, 140, 14, { size: 9, italic: true, color: GRAY });
  s.addText(["Observe 기본 메트릭·대시보드", "노드·플릿 수명주기 자동화", "Telemetry Relay (SIEM)", "대화형 AI 에이전트"].map((t, i, a) => ([
    { text: "● ", options: { color: DSX, bold: true } }, { text: t, options: { color: T900, breakLine: true } },
  ])).flat().map(r => ({ text: r.text, options: Object.assign({ fontFace: F, fontSize: 9, paraSpaceAfter: 4 }, r.options) })),
    { x: IN(768), y: IN(334), w: IN(140), h: IN(80), margin: 0 });
  txt(s, "필요 지원 사항 (인력·예산): [플레이스홀더: SKT 제공 필요] · 일정 분기는 발표 전 SKT 확정 필요 — 임의 기입 금지", 40, 452, 880, 16, { size: 10, italic: true, color: GRAY });
  txt(s, "확정 시 이 자리에서 ☐ → ☑ 체크 (D1·D2·D3) — 슬라이드 2의 카드와 동일", 40, 474, 600, 14, { size: 10, color: NAVY_L });
  pageNo(s, 12);
  s.addNotes("[4-1 결정 요청 18:30~20:00 — 클라이맥스, 절대 스킵 불가]\n\"처음에 보여드린 세 장의 카드입니다. 다시 요청드립니다. 첫째, 슬라이드 6의 DSX OS 골격 E2E 레이어드 아키텍처 채택. 둘째, 슬라이드 7의 범위 매트릭스 기준 역할 분담 — 별표 4건 포함. 셋째, 하이브리드 수집 전략과 네트워크→스토리지→Facility 단계 순서입니다.\n오늘 이 세 가지를 확정해 주시면 즉시 NVIDIA와 공동 설계 워크숍에 착수하겠습니다. 워크숍에서 아키텍처를 상세화하고, Compute PoC, 네트워크·스토리지 통합, Facility와 AI 에이전트까지 — 각 단계 시점은 [Q○'2○]로 계획하고 있습니다. ← 실제 분기 일정으로 교체 후 발표. 미확정 시: \"구체 분기는 워크숍에서 NVIDIA와 확정해 다음 보고에서 말씀드리겠습니다\"로 대체. 도달점은 명확합니다. 아까 5페이지에서 △·✕였던 네 개 축이 전부 ●가 되는 것 — CoreWeave와 동등한 수준의 모니터링·분석 환경입니다.\n필요 지원은 [인력 ○명, 예산 ○○]입니다. ← 실제 수치로 교체 후 발표.\"\n\n강조: 마지막 문장은 도달점 배지를 짚은 채로 마무리.\n전환: \"발표는 여기까지입니다. 이제 결정을 위한 논의를 시작하겠습니다.\"");
}

/* ============ 슬라이드 13: Discussion / Q&A ============ */
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  txt(s, "Discussion / Q&A", 0, 148, 960, 44, { size: 32, bold: true, color: "FFFFFF", align: "center" });
  txt(s, "제기된 질문과 이견을 결정으로 수렴합니다", 0, 196, 960, 22, { size: 14, color: "B9C6D6", align: "center" });
  s.addShape("line", { x: IN(200), y: IN(252), w: 0, h: IN(136), line: { color: DSX, width: 3 } });
  txt(s, "Q1. 범위 매트릭스 ★4개 항목(분석 재활용·자동 복구 개입 수준·IT/OT 책임)의 경계를 어디에 둘 것인가?\nQ2. Phase 순서(Network→Storage→Facility)와 착수 시점에 이견이 있는가?\nQ3. NVIDIA 공동 설계 워크숍에 어느 조직까지 참여할 것인가?", 220, 252, 560, 140, { size: 14, color: "FFFFFF", lsp: 1.6 });
  box(s, 200, 420, 560, 36, { round: true, rad: 8, fill: "2A4A73" });
  txt(s, "심화 자료: 백업 A (MRM·Facility-aware 상세) · 백업 B (DSX OS 모듈 구성) · 백업 C (CoreWeave 상세 비교)", 214, 420, 532, 36, { size: 11.5, color: NAVY_SUB, valign: "middle", align: "center" });
  pageNo(s, 13, true);
  s.addNotes("[Discussion 20:00~ (10~15분)]\n오프닝: \"논의를 세 갈래로 나눠 진행하면 효율적일 것 같습니다. 화면의 순서대로 — 먼저 범위 매트릭스의 별표 4건, 다음으로 Phase 순서와 착수 시점, 마지막으로 워크숍 참여 조직 범위입니다. 그 외 질문도 언제든 주십시오. MRM 상세나 CoreWeave 상세 비교 등은 백업 장표로 준비되어 있습니다.\"\n\n진행 요령: 결정별 3상태(확정/조건부 확정/보류)로 수렴. 모르는 세부 수치는 즉석 추정 금지 — \"내부 확인 후 [기한]까지 회신\"으로 액션 아이템화. 답변 후 \"이 답변으로 D○ 결정에 지장이 없으신지요?\"로 결정 프레임 복귀.\n\n예상 Q&A 상위 3건: ① DSX OS 성숙도 → 8개+ 벤더 생태계, 초기 참여로 공동 설계 지분 확보, PoC로 리스크 관리 ② Mission Control과의 관계 → 보완 관계(제어면 vs 분석·시각화 레이어), 비용은 워크숍에서 확인 ③ 락인 → OTel(CNCF)·Redfish(DMTF) 표준 + DSX OS 오픈소스, 수집 어댑터만 교체 가능한 구조.");
}

/* ============ 백업 A ============ */
{
  const s = pres.addSlide();
  header(s, "Backup-1. SKT 특화 기능 상세 (MRM · Facility-aware)", { grayBadge: "Backup" });
  gov(s, "표준 메트릭을 넘어선 SKT 특화 분석 기능이 이미 운영 검증되어 있다");
  [["MRM", 40], ["Facility-aware", 490]].forEach(([name, x]) => {
    box(s, x, 130, 430, 340, { round: true, rad: 8, fill: "FFFFFF", lineColor: LINE });
    navyTab(s, x + 16, 120, name === "MRM" ? 60 : 110, name);
    txt(s, "기능 정의·활용 사례·정량 효과:\n[플레이스홀더: SKT 제공 필요]", x + 20, 150, 390, 50, { size: 11, italic: true, color: GRAY, lsp: 1.3 });
    shot(s, x + 20, 210, 390, 176, "운영 화면 — SKT 제공 예정");
  });
  txt(s, "본편 슬라이드 4·11 연계 — Facility-aware 경험은 DSX Exchange 연동(11p Phase 3)의 기반 자산", 40, 484, 880, 16, { size: 10, color: GRAY });
  pageNo(s, 14);
  s.addNotes("[백업 A — 본편 4p·13p에서 참조] MRM·Facility-aware 상세 설명용. 내용 전체가 SKT 내부 자료 플레이스홀더 상태 — 발표 전 실제 기능 정의·사례·화면으로 교체 필수. 미교체 시 이 장표는 덱에서 제외하고 본편 4p·13p의 백업 참조 문구도 함께 수정할 것.");
}

/* ============ 백업 B ============ */
{
  const s = pres.addSlide();
  header(s, "Backup-2. DSX OS 모듈 구성 상세", { grayBadge: "Backup" });
  gov(s, "DSX OS는 6개 모듈로 구성된 오픈소스·모듈러 스택이다 (GTC Taipei, 2026-05 발표)");
  const mods = [
    ["Lifecycle Management", "프로비저닝·수명주기 관리"],
    ["Runtime Consistency", "런타임 일관성 보장"],
    ["Health Automation", "상시 헬스체크·이상 탐지"],
    ["Resiliency", "자동 복구·복원력"],
    ["Multi-tenant Operations", "멀티테넌트 운영"],
    ["AI Platform Services", "플랫폼 서비스 (MCP 서버 카탈로그 포함)"],
  ];
  mods.forEach(([t, d], i) => {
    const x = 40 + (i % 3) * 300, y = 130 + Math.floor(i / 3) * 136;
    box(s, x, y, 278, 120, { round: true, rad: 8, fill: DSX_T, lineColor: DSX, lineW: 1.25 });
    txt(s, t, x + 16, y + 20, 246, 40, { size: 13.5, bold: true, color: "3E6300" });
    txt(s, d, x + 16, y + 62, 246, 40, { size: 11, color: T900 });
  });
  box(s, 40, 416, 880, 40, { round: true, rad: 6, fill: AMB_T, lineColor: AMB });
  txt(s, "DSX Exchange — MQTT 기반 IT/OT 허브: 전력·열·그리드 이벤트를 SW 스택에 노출", 56, 416, 848, 40, { size: 12, bold: true, color: "8A5000", valign: "middle" });
  txt(s, "생태계: Red Hat·Mirantis·OpenNebula·Supermicro 등 8개+ 벤더 컴포넌트 채택 — 본편 슬라이드 8 연계", 40, 470, 880, 16, { size: 10, color: GRAY });
  pageNo(s, 15);
  s.addNotes("[백업 B — 본편 6p·13p에서 참조] DSX OS 6모듈 구조 상세. Q&A 1번(성숙도)·2번(Mission Control 관계) 답변 시 활용. 출처: NVIDIA DSX OS 발표 (GTC Taipei 2026-05), developer.nvidia.com 블로그.");
}

/* ============ 백업 C ============ */
{
  const s = pres.addSlide();
  header(s, "Backup-3. CoreWeave 벤치마크 상세", { grayBadge: "Backup" });
  gov(s, "CoreWeave 4축의 기능 상세와 SKT 도달 경로 — 목표선의 구체 근거");
  const colWC = [180, 380, 320].map(IN);
  const tC = [
    hdrRow(["축", "CoreWeave 기능 상세", "SKT 도달 경로 (Phase)"]),
    [chipCell("Observe: 기본 메트릭·대시보드", { size: 10 }), cell("클러스터 메트릭·대시보드를 설정 없이 기본 제공 (out-of-the-box, 무추가 과금)", { size: 10.5 }), cell("프로비저닝 파이프라인에 대시보드 자동 탑재 (Phase 1)", { size: 10.5, fill: NAVY_T })],
    [chipCell("노드·플릿 수명주기 자동화", { size: 10 }), cell("수명주기 컨트롤러 + CloudOps 모니터링 + 전문가 직결 지원", { size: 10.5 }), cell("DSX OS Lifecycle·Resiliency 모듈 연동 (Phase 1~2)", { size: 10.5, fill: DSX_T })],
    [chipCell("Telemetry Relay", { size: 10 }), cell("암호화 감사·보안 이벤트의 고객 SIEM 포워딩 (거버넌스·컴플라이언스)", { size: 10.5 }), cell("사내 SIEM 연동 설계 — 거버넌스 요건 협의 선행 (Phase 2)", { size: 10.5, fill: NAVY_T })],
    [chipCell("대화형 AI 에이전트", { size: 10 }), cell("Slack에서 클러스터 헬스·잡·인시던트·변경사항 질의응답", { size: 10.5 }), cell("DSX OS MCP 서버 카탈로그 기반 Agentic 운영 (Phase 3, 공동)", { size: 10.5, fill: AMB_T })],
  ];
  s.addTable(tC, { x: IN(40), y: IN(120), w: IN(880), colW: colWC, border: { color: LINE, pt: 0.75 }, margin: 0.05, rowH: IN(64), valign: "middle" });
  legend3(s, 40, 452);
  txt(s, "출처: coreweave.com/mission-control, /observability (2026-07 조사) — 본편 슬라이드 5·12 연계", 40, 478, 880, 16, { size: 10, color: GRAY });
  pageNo(s, 16);
  s.addNotes("[백업 C — 본편 5p·13p에서 참조] CoreWeave 4축 상세와 도달 경로. Q&A 5번(차별점) 답변 시: 기능 수준은 CoreWeave가 목표선이나, 오픈 표준(OTel·Redfish·MCP) 기반 Multi-DC 확장성과 통신 인프라 Facility 연계 경험이 차별점.");
}

pres.writeFile({ fileName: "/home/user/encry/_workspace/NVIDIA_DSX_OS_E2E_Observability_논의.pptx" }).then(() => console.log("WRITTEN"));
