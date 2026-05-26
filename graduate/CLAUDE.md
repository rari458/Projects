# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ 작업 방식 (필수)

**Help only up to the point of displaying the code to the user, without directly implementing or modifying the code.**

코드는 사용자에게 보여주는 선까지만 돕는다. 파일을 직접 생성·수정하지 말 것. 제안하는 코드는 답변 안에 코드 블록으로 제시하고, 적용 여부는 사용자가 직접 결정한다.

**Code comments/annotations: English only. No Korean in code.** (설명 문장은 한국어로 하되, 코드 안 주석·docstring·식별자는 전부 영어로 작성한다.)

## ⚠️ 현재 상태: 구현 시작 전 (pre-implementation)

이 디렉토리에는 **아직 소스 코드가 없습니다.** git 저장소도 아니며, 졸업 프로젝트 기획 PDF 3개만 존재합니다. 빌드/테스트/실행 명령어와 코드 아키텍처는 코드가 작성되는 대로 이 파일에 추가해야 합니다. 아래 "구현 시작 시 채울 항목"을 참고하세요.

## 프로젝트 개요

한양대학교 컴퓨터소프트웨어학부 졸업 프로젝트 (9팀: 문상철, 박규현 / 지도교수: 이성윤). 산업체 수요과제(C형), 기간 2026.03.–2026.12.

**목표:** 학습 속도가 빠른 옵티마이저(**Muon** 등)와 일반화 성능이 좋은 옵티마이저(**SAM** 등)의 장점을 결합한 새로운 딥러닝 최적화 알고리즘(Optimizer)을 설계하고, **PyTorch와 TensorFlow 양쪽**에서 `import`하여 바로 쓸 수 있는 오픈소스 라이브러리로 구현·검증한다.

**해결하려는 트레이드오프:** Adam/Muon 계열은 빠르지만 과적합에 취약하고, SAM 계열은 일반화는 좋으나 파라미터 업데이트마다 순전파·역전파를 2회 요구해 연산량이 2배다. 동일 계산 예산(computational budget) 대비 속도와 일반화를 모두 확보하는 통합 옵티마이저를 만드는 것이 핵심.

## 설계 방향 (제안서 기준)

새 알고리즘 구현 시 다음 아이디어를 따른다:

- **동적 스케줄링(Dynamic Scheduling):** 학습 초기에는 빠른 수렴(Muon 특성)에 가중치를 두고, 후반부에는 일반화(SAM 특성)에 집중하도록 전환.
- **주기적 SAM 적용 (LookSAM 원리):** SAM 보정 방향이 인접 스텝 간 크게 변하지 않는다는 점을 활용해, 매 스텝이 아니라 주기적으로만 SAM perturbation을 계산하여 오버헤드 절감.
- 위 방식들을 결합/교차 검증하여 최적 파이프라인을 도출.

구현 시 PyTorch/TensorFlow의 **AutoGrad(자동 미분) 내부 구조**를 직접 다루게 되며, SAM 특유의 **2-step (perturb → restore → update)** 패턴과 Muon의 **행렬 직교화 기반 업데이트**를 정확히 반영해야 한다.

## 검증 / 평가 기준

지정 과제 공고문의 평가 항목:

1. 기존 최적화 알고리즘을 (재)구현하였는가.
2. 빠른 수렴 알고리즘의 일반화 성능을 개선한 **새로운** 알고리즘을 구현하였는가.

**벤치마크 계획:** 소규모는 CIFAR-10 (1차 프로토타입 디버깅), 본격 비교는 CIFAR-100 / ImageNet. 비교 대상 baseline은 **AdamW, SAM** 등. 측정 지표는 **수렴 속도와 검증 정확도(validation accuracy)**, 그리고 동일 계산 예산 대비 성능.

## 작업 분담 (참고)

- **문상철:** 알고리즘 수식 설계 + PyTorch 코어 로직 구현, 논문/수식 리서치.
- **박규현:** TensorFlow 포팅, GPU 분산 학습 벤치마킹 설계, 메모리/연산 속도 프로파일링 및 지표 분석.

## 일정 (제안서 기준, 명령어/구조 채워질 시점 참고)

- 3–4월: 논문 리뷰, 수학적 모델링, 평가 지표 설정.
- **5–6월: PyTorch 1차 프로토타입 구현 + CIFAR-10 디버깅.** ← 코드가 처음 생기는 시점.
- 7–8월: TensorFlow 포팅, 코드 최적화, 메모리 누수 점검.
- 9–10월: ImageNet 벤치마킹, baseline 대비 성능 비교.
- 11–12월: 패키징, 최종 보고서, 발표 준비.

## 핵심 참고 문헌

이 프로젝트의 알고리즘은 아래 논문/구현체에 기반한다. 관련 작업 시 우선 참고:

- **Muon** — Keller Jordan, https://github.com/KellerJordan/Muon · "Muon is Scalable for LLM Training" (arXiv:2502.16982) · Jeremy Bernstein, "Deriving Muon" (https://jeremybernste.in/writing/deriving-muon)
- **SAM** — Foret et al., *Sharpness-Aware Minimization for Efficiently Improving Generalization*, ICLR 2021
- **ASAM** — Kwon et al., ICML 2021 (scale-invariant SAM)
- **효율적 SAM** — Du et al. (ESAM), ICLR 2022 · Liu et al. (LookSAM), CVPR 2022 — *연산량 절감의 핵심 레퍼런스*
- **기반 이론** — AdamW (Loshchilov & Hutter, ICLR 2019) · Loss Landscape 시각화 (Li et al., NeurIPS 2018) · Flat/Sharp Minima (Keskar et al., ICLR 2017)

### 로컬 자료 (이 디렉토리에 존재 — 우선 이걸로 참고)

논문/구현 원문이 이미 디렉토리에 들어와 있다. 외부 검색보다 이 파일들을 먼저 읽을 것:

- `2010.01412v3.pdf` — **SAM** (Foret et al., ICLR 2021)
- `2102.11600v3.pdf` — **ASAM** (Kwon et al., ICML 2021)
- `2110.03141v2.pdf` — **ESAM** (Du et al., ICLR 2022)
- `2203.02714v1.pdf` — **LookSAM / Towards Efficient and Scalable SAM** (Liu et al., CVPR 2022)
- `2502.16982v1.pdf` — **Muon is Scalable for LLM Training**
- `2604.01472v1.pdf` — **The Newton–Muon Optimizer**
- `muon.py` — **Keller Jordan 공식 Muon 구현체** (`zeropower_via_newtonschulz5`, `Muon`, `SingleDeviceMuon`, `MuonWithAuxAdam`, `SingleDeviceMuonWithAuxAdam`). 이 프로젝트 코드가 아니라 **외부 레퍼런스 구현**임에 유의.
- `sam.py` — **davda54/sam 공식 SAM 구현체.** `base_optimizer`를 감싸는 래퍼이며 `first_step`(perturb→`w+e(w)`)/`second_step`(복원→base step)의 2-step 구조. `adaptive=True`면 ASAM. closure 기반 forward-backward 2회. **결합 시 `base_optimizer=Muon`이 자연스러운 출발점.** 역시 외부 레퍼런스 구현.
- `setup.py` — 위 Muon 패키지 설치 스크립트.
- `화면 캡처 2026-05-26 *.png` (10장) — Jeremy Bernstein **"Deriving Muon"** 블로그 전문 캡처 (제목→Step 1~4→PayOff→Conclusion 순). 수식 유도 참고용.

> 참고: `2502.16982`, `2604.01472`는 작성자 지식 컷오프 이후 자료이므로 반드시 위 PDF 원문을 근거로 다룰 것.

## 구현 시작 시 이 파일에 채울 항목

코드가 생기면 다음을 검증된 실제 값으로 추가할 것 (지어내지 말 것):

- **환경 설정 / 의존성** 설치 (PyTorch, TensorFlow 버전 포함).
- **테스트 실행** 명령 (단일 테스트 실행 방법 포함).
- **학습/벤치마크 실행** 명령 (데이터셋·옵티마이저·하이퍼파라미터 지정 방식).
- **디렉토리 구조 / 아키텍처** — 특히 PyTorch와 TensorFlow 구현 간 공유되는 알고리즘 코어를 어떻게 분리/공유하는지.
