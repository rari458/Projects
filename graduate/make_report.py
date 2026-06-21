"""Generate the mid-term report as a .docx using the Python standard library
only (no python-docx / pandoc needed). Open the result in Word or LibreOffice
and "Save as PDF".

Usage:
  python make_report.py                      # -> 중간보고서_9팀.docx
  python make_report.py /path/out.docx       # custom output path
"""
import sys
import zipfile
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
FONT = "Malgun Gothic"  # has Korean glyphs on Windows; LibreOffice substitutes


def run(text, bold=False, size=None):
    props = (f'<w:rFonts w:ascii="{FONT}" w:eastAsia="{FONT}" w:hAnsi="{FONT}"/>')
    if bold:
        props += "<w:b/>"
    if size is not None:
        props += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def para(text="", bold=False, size=22, before=0, after=80, align=None):
    ppr = f'<w:spacing w:before="{before}" w:after="{after}"/>'
    if align:
        ppr += f'<w:jc w:val="{align}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{run(text, bold=bold, size=size)}</w:p>"


def heading(text, level=1):
    size = {1: 28, 2: 24}.get(level, 24)
    return para(text, bold=True, size=size, before=240, after=120)


def cell(text, bold=False):
    p = f"<w:p><w:pPr><w:spacing w:after='0'/></w:pPr>{run(text, bold=bold, size=20)}</w:p>"
    return f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>{p}</w:tc>'


def table(rows, header=True, bold_col0=False):
    borders = "".join(
        f'<w:{e} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        for e in ("top", "left", "bottom", "right", "insideH", "insideV"))
    tblpr = (f'<w:tblPr><w:tblW w:w="0" w:type="auto"/>'
             f'<w:tblBorders>{borders}</w:tblBorders></w:tblPr>')
    out = [f"<w:tbl>{tblpr}"]
    for i, r in enumerate(rows):
        cells = "".join(
            cell(c, bold=(header and i == 0) or (bold_col0 and j == 0))
            for j, c in enumerate(r))
        out.append(f"<w:tr>{cells}</w:tr>")
    out.append("</w:tbl><w:p/>")  # spacer paragraph required after a table
    return "".join(out)


body = []
body.append(para("졸업프로젝트 중간보고서 — 9팀", bold=True, size=36, after=60, align="center"))
body.append(table([
    ["프로젝트명", "더 좋은 성능을 위한 딥러닝 최적화 알고리즘 (Muon × SAM 융합 Optimizer)"],
    ["팀원", "문상철(2022065250), 박규현(2022000037)"],
    ["지도교수", "이성윤"],
    ["기간", "2026.03 – 2026.12"],
    ["작성일", "2026.06."],
], header=False, bold_col0=True))

body.append(heading("1. 프로젝트 개요 및 목표"))
body.append(para(
    "학습 속도가 빠른 Muon과 일반화 성능이 우수한 SAM의 장점을 결합하여, import만으로 "
    "기존 학습 코드에 적용 가능한 신규 Optimizer를 PyTorch(주력) 및 TensorFlow로 구현·검증한다. "
    "평가는 표준 비전 벤치마크(CIFAR-10 → CIFAR-100 → ImageNet)에서 AdamW·SAM 대비 동일 "
    "연산량(compute budget) 기준 수렴 속도 및 검증 정확도로 정량 비교한다."))

body.append(heading("2. 추진 현황 및 진척도 (계획 대비)"))
body.append(table([
    ["기간", "계획", "상태"],
    ["3–4월", "논문 리뷰, 수학적 모델링, 평가지표 설정", "완료"],
    ["5–6월", "PyTorch 1차 프로토타입 구현 + CIFAR-10 디버깅", "완료 (본 보고 시점)"],
    ["7–8월", "TensorFlow 포팅, 코드 최적화, 메모리 점검", "예정"],
    ["9–10월", "ImageNet 벤치마킹, 기존 Optimizer 대비 비교", "예정"],
    ["11–12월", "패키징, 최종 보고서·발표", "예정"],
]))
body.append(para("→ 일정 정상 진행. 현재 5–6월 마일스톤(프로토타입 + CIFAR-10 검증)을 달성하였다."))

body.append(heading("3. 수행 내용"))
body.append(heading("3.1 기초 기술 조사 (논문 리뷰)", level=2))
body.append(para(
    "SAM 계열의 핵심 한계는 파라미터 업데이트마다 순전파·역전파를 2회 수행해 연산량이 2배가 "
    "된다는 점이며, 이를 줄이는 변형들을 중점 조사하였다."))
body.append(table([
    ["알고리즘", "핵심 아이디어", "연산 오버헤드"],
    ["SAM (Foret, 2021)", "worst-case 이웃으로 weight 섭동 후 그 지점 gradient로 업데이트", "약 2배 (기준선)"],
    ["ASAM (Kwon, 2021)", "스케일 불변(adaptive) 섭동", "약 2배"],
    ["ESAM (Du, 2022)", "확률적 섭동 + 민감 샘플 선택으로 비용 절감", "2배 미만"],
    ["GSAM (Zhuang, 2022)", "surrogate gap 동시 최소화", "약 2배"],
    ["LookSAM (Liu, 2022)", "섭동 방향을 k스텝마다만 재계산·재사용", "약 1배 근접"],
    ["Muon (2025–26)", "2D hidden weight의 momentum을 Newton–Schulz로 orthogonalize", "약 1배"],
]))
body.append(heading("3.2 알고리즘 설계 (핵심 아이디어)", level=2))
body.append(para(
    "SAM은 gradient를 계산하는 위치(worst-case 이웃 w+e)를, Muon은 2D hidden weight의 업데이트 "
    "방향을 Newton–Schulz로 orthogonalize한다. 본 과제는 SAM의 섭동을 Muon의 spectral 기하로 "
    "끌어올려 한 스텝 안에서 융합한다: 섭동을 e = ρ·O(g)로 정의하며, 여기서 O(·)는 Newton–Schulz "
    "orthogonalization(≈ U V^T)이다. 연산 오버헤드는 LookSAM 원리로 줄인다."))
for b in [
    "• 주기적 SAM (LookSAM, 주기 k = sam_period): k 스텝마다 2-pass SAM을 수행하고, 그 사이에는 "
    "느리게 변하는 보정 방향을 재사용해 1-pass로 진행한다.",
    "• Frobenius-space 보정: SAM 스텝에서 직교 성분 u_v = u_s - (<u, u_s>/||u||^2)·u 를 저장하고, "
    "중간 스텝에서 d = u_t + α·(||u_t||/||u_v||)·u_v (필요시 재직교화)로 재사용한다.",
    "• 동적 ρ 스케줄: 학습 초반(rho_warmup_frac까지) ρ=0으로 Muon의 빠른 수렴에 집중하고, 이후 "
    "ρ를 ρ_max까지 선형 증가시켜 SAM의 sharpness 제어로 이동한다.",
    "• 파라미터 라우팅: 2D hidden weight는 Muon(spectral 섭동), embedding·head·scalar는 "
    "AdamW(L2/ASAM 섭동 + Euclidean LookSAM 보정).",
]:
    body.append(para(b, after=40))
body.append(heading("3.3 구현", level=2))
body.append(para(
    "공식 Muon 구현(SingleDeviceMuonWithAuxAdam: Newton–Schulz와 AdamW aux 포함)을 기반으로, 융합 "
    "알고리즘을 별도 클래스 MuonSAM(torch.optim.Optimizer)으로 구현하였다. 비교 기준선 SAM은 표준 "
    "2-pass 래퍼(first_step/second_step)를 사용한다. 모듈 구성: muon.py(Muon 코어), sam.py(SAM 래퍼), "
    "muon_sam.py(MuonSAM 융합), benchmark_cifar10.py(공정 비교 하니스), test_muon_sam.py. 공정성을 위해 "
    "4개 옵티마이저(AdamW/SAM/Muon/MuonSAM)에 동일한 가중치 초기화와 배치 순서를 적용하고, 32×32 CIFAR에 "
    "맞춘 ResNet-18(3×3 stem, maxpool 제거)을 사용한다. 본 프로토타입은 가독성을 위해 Muon group의 내부 "
    "momentum을 생략하였으며(문서화된 fork), GPU 단계에서 momentum 재도입 변형으로 평가할 예정이다."))

body.append(heading("4. 중간 결과 (CIFAR-10, ResNet-18)"))
body.append(para(
    "benchmark_cifar10.py로 AdamW·SAM·Muon·MuonSAM을 동일 조건에서 비교하였다. 수렴 속도와 일반화를 "
    "함께 보기 위해 정확도를 epoch 축과 누적 wall-clock(동일 연산량) 축 양쪽으로 측정한다."))
body.append(para("【그림 1: benchmark.png 삽입 — acc vs epoch / acc vs wall-clock (4개 옵티마이저)】",
                 bold=True))
body.append(para("【표 2: 최종 test 정확도 및 학습 시간】", bold=True, after=40))
body.append(table([
    ["Optimizer", "test acc (%)", "time (s)"],
    ["AdamW", "【 】", "【 】"],
    ["SAM", "【 】", "【 】"],
    ["Muon", "【 】", "【 】"],
    ["MuonSAM", "【 】", "【 】"],
]))
body.append(para(
    "【관찰 1–2문장】 (주의: 현 수치는 하이퍼파라미터 미튜닝 상태의 하니스 검증 결과이며, "
    "옵티마이저별 LR/ρ 튜닝을 거친 GPU 벤치마크는 9–10월 계획이다.)"))

body.append(heading("5. 향후 계획"))
for b in [
    "• 7–8월: TensorFlow 포팅 및 메모리/연산 프로파일링 (박규현)",
    "• 9–10월: CIFAR-100 → ImageNet 확장, config 축 스윕(주기 적용·동적 스케줄)으로 "
    "동일 연산량 대비 최적 파이프라인 탐색",
    "• 11–12월: 오픈소스 패키징, 최종 보고·발표",
]:
    body.append(para(b, after=40))

body.append(heading("6. 기대효과 및 리스크"))
body.append(para(
    "대규모 모델 학습의 컴퓨팅 비용 절감과 일반화 성능 확보를 동시에 노린다. 주요 리스크는 "
    "SAM의 2배 연산 오버헤드 상쇄 효과의 불확실성이며, LookSAM식 주기 적용과 동적 스케줄로 완화한다."))

document_xml = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<w:document xmlns:w="{W}"><w:body>'
    + "".join(body)
    + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
      '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
      'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
    + "</w:body></w:document>"
)

content_types = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

rels = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>'
)

out = sys.argv[1] if len(sys.argv) > 1 else "중간보고서_9팀.docx"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", content_types)
    z.writestr("_rels/.rels", rels)
    z.writestr("word/document.xml", document_xml)
print(f"wrote {out}")
