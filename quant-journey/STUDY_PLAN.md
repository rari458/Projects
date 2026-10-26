# Quantitative Developer (QD) 학습 로드맵

> 출처: QuantFinanceWiki.com — *Quantitative Developer (QD) Career Roadmap* 의 Recommended Reading 기반
> 목표 역할: **C++로 빠른 시스템(트레이딩 엔진·시뮬레이션)을 만드는 소프트웨어 엔지니어** (Jump Trading, HRT 류 HFT)
> 원칙: **"읽지 말고 만들어라"** — 모든 책은 GitHub 산출물(코드/노트/PR)로 연결한다.

---

## 0. 무게중심 (우선순위)

QD 실력은 **C++ + 시스템**에서 갈린다. Python·SQL·pandas는 보조 도구이며 여기에 시간을 많이 쓰면 함정이다.

| 그룹 | 책 | 투자 비중 |
|---|---|---|
| **① 메인: C++ + 시스템** | CS:APP, Accelerated C++, Effective C++, Effective Modern C++, C++ Concurrency in Action | **60~70%** |
| **② 엔지니어링 장인정신** | Code Complete, Clean Code, Design Patterns(GoF), Pro Git | **15%** |
| **③ 보조: 연구/데이터** | Python for Data Analysis, Learning Python, Learning SQL | **15~20%** |

**함정 3가지**
1. Python/SQL이 편해서 먼저 판다 → QD 실력은 C++/시스템에서 갈린다.
2. 책을 직렬로 완독하려 한다 → 알고리즘 감각이 죽고, 배운 게 휘발된다. **병렬 + 산출물**이 답.
3. CS:APP를 "읽기"만 한다 → Lab을 풀어야 진짜 자산이 된다.

---

## 1. 세 트랙을 매일 병렬로

- **트랙 A — 코어 학습** (매일 대부분): 현재 Phase의 책 + 그 자리에서 코드로 확인
- **트랙 B — 보조 도구** (주 2~3시간, 얕게): pandas / SQL / Python 참조
- **트랙 C — 알고리즘** (매일 30~45분, 첫날~마지막날 끊지 않기): LeetCode / HackerRank in C++

### 주간 리듬 예시
```
평일:
  ├─ 아침 30~45분 : LeetCode/HackerRank 1문제 (C++)        ← 트랙 C
  ├─ 코어 1.5~2h  : 현재 Phase 책 + 코드로 확인             ← 트랙 A
  └─ 주 2~3회 짧게 : pandas/SQL 노트북 or Python 참조        ← 트랙 B
주말:
  └─ 통합 블록    : CS:APP Lab / QuantLib 빌드·소스읽기 / 미니 프로젝트
```

---

## ⚙️ 환경 세팅 (시작 전 1회) — WSL2 / Ubuntu 기준

> **실제 검증 완료** (2026-07-23): Ubuntu 26.04 (WSL2, x86_64) · git 2.53 · gcc/g++ 15.2 · cmake 4.2 · gdb 17.1 · Boost 1.90.0 · valgrind 3.26 · flex/bison ✅
> **RAM 7.6GB / 16 코어** — 코어는 넉넉하지만 RAM이 병목. 무거운 빌드(QuantLib)는 `-j4`로 제한할 것 (`-j$(nproc)`로 16 잡 다 돌리면 OOM 위험).
> **실제 사용 경로**: CS:APP Labs `~/Projects/csapp-labs/`, QuantLib `~/QuantLib/`(독립 레포), 학습 monorepo `~/Projects/quant-journey/`. `~/Projects`는 기존 GitHub 레포(`rari458/Projects`)라 다른 진행 중인 프로젝트(`Financial_OS` 등)와 함께 있음 — **커밋 시 그쪽 변경사항과 섞이지 않게 주의**.

### ⚠️ 성능 규칙: 빌드는 리눅스 홈(`~/`)에서
`/mnt/c/...`(윈도우 파일시스템)에서 빌드/컴파일하면 WSL2 I/O가 5~10배 느리다.
- 활발히 빌드하는 레포(CSAPP·QuantLib·연습 코드)는 **리눅스 홈(`~/`) 아래**에 둘 것.
- PDF 자료는 `/mnt/c/quantdev`에 그대로 둬도 무방(읽기 전용).

### 1) 공통 도구 설치 (한 줄)
```bash
sudo apt update && sudo apt install -y build-essential gdb gcc-multilib \
  libboost-all-dev git-lfs valgrind flex bison
# (선택) clang 계열: sudo apt install -y clang clang-format
```
- `gdb` → bomb/attack lab 필수 · `gcc-multilib` → datalab `-m32` 대비
- `libboost-all-dev` → QuantLib 필수(가볍게: `libboost-dev libboost-test-dev`)
- `valgrind` → malloc lab / lock-free 디버깅
- `flex`/`bison` → **Architecture Lab 빌드에 필수** (아래 참고, 안 깔면 `yas`/`hcl2c` 빌드 실패)

### 2) CSAPP Labs 받기 — `http://csapp.cs.cmu.edu/3e/labs.html` 의 **Self-Study Handout**
```bash
mkdir -p ~/Projects/csapp-labs && cd ~/Projects/csapp-labs
wget http://csapp.cs.cmu.edu/3e/datalab-handout.tar
tar xvf datalab-handout.tar && cd datalab-handout
make && ./btest        # bits.c 채우며 진행
```
**3판 기준 전체 9개** (Buffer Lab/Architecture Lab Y86 32비트 버전은 2판용 legacy라 제외):

| Lab | 핸드아웃 | 대응 챕터 | 도구 | QD 관련성 |
|---|---|---|---|---|
| Data Lab | `datalab-handout.tar` | Ch2 정수/부동소수 | `./btest`, `./dlc bits.c` | 기본 |
| Bomb Lab | `bomb.tar` | Ch3 어셈블리 | `gdb`, `objdump -d bomb` | 기본 |
| Attack Lab | `target1.tar` | Ch3 버퍼오버플로우 | `gdb`, `objdump` | 기본 |
| Architecture Lab (Y86-64) | `archlab-handout.tar` | Ch4 프로세서 구조 | `ssim`, `yas` | CPU 파이프라인 → 속도의 근원 |
| Cache Lab | `cachelab-handout.tar` | Ch6 메모리 계층 | `./test-csim`, `./test-trans` | 필수, cache-friendly 코드 |
| **Performance Lab** | `perflab-handout.tar` | Ch5 성능 최적화 | `./driver.py` | **HFT 최적화 마인드셋 직결** |
| Shell Lab | `shlab-handout.tar` | Ch8 프로세스/시그널 | `./sdriver.pl` | 시스템 프로그래밍 |
| Malloc Lab | `malloclab-handout.tar` | Ch9 가상메모리 | `./mdriver`, `valgrind` | 필수, 할당자 직접 구현 |
| **Proxy Lab** | `proxylab-handout.tar` | Ch11-12 네트워크·동시성 | `telnet`/`curl`, 멀티스레드 서버 | **동시성 네트워크 서버 = 트레이딩 엔진과 직결** |

Bomb Lab 시작: `objdump -d bomb > bomb.asm` → `gdb bomb`에서 `break phase_1`.
Proxy Lab은 완료 후 `concurrency/`의 스레드풀 실습과 바로 이어서 복습하면 좋다(둘 다 멀티스레드 동시성).

#### ⚠️ Architecture Lab 빌드 특이사항 (2015년 코드 vs GCC 15)
`archlab-handout/sim/{misc,seq,pipe}`는 오래된 C 코드라 최신 GCC 기본 동작 변화로 빌드가 깨진다. 이미 검증된 수정 방법:

| 증상 | 원인 | 해결 |
|---|---|---|
| `make`가 아무 것도 안 함 | 최상위 `Makefile`의 `sim:` 타겟명이 기존 `sim/` 디렉토리와 이름 충돌 → make가 "이미 최신"으로 오판 | `misc → seq → pipe` 순서로 각 디렉토리에서 직접 `make` |
| `free_reg` 인자 개수 에러 | GCC 15 기본 표준이 **C23**으로 바뀜 → 옛 K&R 스타일 `void f();` 선언 깨짐 | `CFLAGS`에 `-std=gnu17` 추가 |
| `lineno` 중복 정의 링크 에러 | GCC 10부터 `-fcommon`이 기본 아님(과거엔 기본) | `CFLAGS`/`LCFLAGS`에 `-fcommon` 추가 |
| `tk.h` 없음 (GUI 빌드) | Tcl/Tk 미설치, WSL엔 불필요 | Makefile 원래 "주석 처리해도 됨"이라 명시 — GUI 안 쓰면 무시 |

**세 Makefile에 한 번만 고쳐두면 이후 `make`만 쳐도 됨:**
- `sim/misc/Makefile` 2, 3행: `CFLAGS=-Wall -O1 -g -std=gnu17 -fcommon` / `LCFLAGS=-O1 -fcommon`
- `sim/seq/Makefile`, `sim/pipe/Makefile` 공통 (7, 14, 20, 26행):
  `GUIMODE=` / `TKLIBS=` / `TKINC=` (빈 값, 원래 "comment out"과 동일 효과) / `CFLAGS=-Wall -O2 -std=gnu17 -fcommon`

검증: `../misc/yas asum.ys && ./ssim -t asum.yo` → `ISA Check Succeeds` 나오면 정상.

### 3) QuantLib 빌드 → 예제 → 테스트
**`~/Projects`(기존 GitHub 레포) 밖, 독립 위치에 clone.** 대용량 `build/`가 학습 레포 히스토리에 안 딸려오게, 나중에 fork로 바꾸기도 쉽게.
```bash
cd ~
git clone https://github.com/lballabio/QuantLib.git ~/QuantLib && cd ~/QuantLib
cmake -B build -DCMAKE_BUILD_TYPE=Release \
      -DQL_BUILD_EXAMPLES=ON -DQL_BUILD_TEST_SUITE=ON
cmake --build build -j4                # RAM 7~8GB급이면 -j4 권장 (코어 다 쓰면 OOM 위험)

find build/Examples -maxdepth 2 -type f -executable   # 예제 위치 확인
./build/Examples/BermudanSwaption/BermudanSwaption
ctest --test-dir build --output-on-failure            # 테스트
```
> 처음엔 `-DQL_BUILD_TEST_SUITE=OFF`로 예제만 빨리 보고, 나중에 켜기. 전체 빌드는 RAM 제약 시 코어 많아도 오래(수십 분) 걸릴 수 있음 — 백그라운드로 돌리고 다른 작업 진행.

GoF 패턴 실물 찾기(→ Phase 3 산출물):
```bash
cd ~/QuantLib
grep -rl "Observer" ql/ | head            # Observer (가격 전파)
grep -rl "acceptVisitor" ql/ | head       # Visitor
grep -rln "public.*Engine" ql/pricingengines | head   # Strategy
```
기여는 GitHub에서 **fork → clone → 브랜치 → PR** (학습 monorepo와 별도 레포로 관리).

### 4) 학습 monorepo 스캐폴딩 — `~/Projects/quant-journey/`
`~/Projects`가 이미 GitHub에 push되는 기존 레포(`rari458/Projects`)라면, `git init` 새로 하지 말고 그 안에 하위 폴더로 넣는다. **CS:APP Labs는 이미 `~/Projects/csapp-labs/`에 별도로 있으니 중복 생성하지 않는다.**
```bash
mkdir -p ~/Projects/quant-journey && cd ~/Projects/quant-journey
mkdir -p effective-cpp/{effective-cpp,effective-modern-cpp}
mkdir -p concurrency/{thread-pool,lockfree-queue}
mkdir -p design-patterns/notes data-analysis/notebooks sql
mkdir -p leetcode/{arrays-hashing,two-pointers,sliding-window,stack,binary-search,linked-list,trees,heap,backtracking,graphs,dp}

cat > .gitignore <<'EOF'
build/
*.o
*.exe
*.out
a.out
cmake-build-*/
__pycache__/
.ipynb_checkpoints/
*.pyc
.venv/
.vscode/
.idea/
.DS_Store
EOF

cat > CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.20)
project(quant_journey CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_compile_options(-Wall -Wextra -O2)
find_package(Threads REQUIRED)
EOF

cp /mnt/c/quantdev/STUDY_PLAN.md .   # 이 파일을 레포 안으로 복사 (경로는 상황에 맞게)
```
**⚠️ 커밋은 신중하게.** `~/Projects`에 다른 진행 중인 프로젝트(예: `Financial_OS`)의 커밋 안 된 변경사항이 같이 있을 수 있다. `git add -A`로 한 번에 올리지 말고, `git status`로 확인 후 `quant-journey/`와 `csapp-labs/`만 명시적으로 `git add`할 것:
```bash
git status                              # 전체 변경사항 확인 (다른 작업과 섞이지 않았는지)
git add quant-journey/ csapp-labs/
git commit -m "chore: add QD study materials (csapp-labs, quant-journey)"
git push
```

### ✅ 진행 상황 체크
1. ~~`sudo apt install`로 **gdb·Boost·flex·bison** 채우기~~ ✅
2. ~~**CS:APP 9개 Lab** 전부 빌드 + 실행 검증~~ ✅ (`~/Projects/csapp-labs/`)
3. **QuantLib** 빌드 (`~/QuantLib/`, 진행 중/완료 여부 확인)
4. **quant-journey** 스캐폴드 (`~/Projects/quant-journey/`) — 커밋은 `Financial_OS` 변경사항과 분리해서

> QuantLib(포크 예정)과 캡스톤 오더북 엔진은 각각 별도 레포, 나머지 학습 산출물은 `~/Projects/quant-journey/` 하나로 관리.

---

## 2. 단계별 계획 (의존성 순서)

각 Phase의 체크박스를 채우며 진행. 기간은 유연하게(전체 6~9개월), 중요한 건 **산출물이 쌓이는가**.

### Phase 0 · 온램프 (2~4주) — *C++가 아직 편하지 않다면*
- [ ] **Accelerated C++** (Koenig & Moo) — STL을 처음부터 쓰는 최단 진입로. 이미 C++가 편하면 건너뛰고 Phase 2로.
  - 산출물: 각 장 예제 타이핑 + 연습문제 GitHub 커밋
- [ ] **Pro Git** — 정독 X. branch / rebase / 좋은 커밋 메시지만 뽑아 **오늘부터 습관으로**. 참조서로 상시 비치.
  - 산출물: 학습용 GitHub 레포 생성, 커밋 규칙 정착
- [ ] 개발 환경 세팅: 컴파일러(gcc/clang), CMake, 디버거(gdb), 에디터/IDE

### Phase 1 · 시스템의 뿌리 (6~8주) — **QD의 심장**
- [ ] **CS:APP** (Computer Systems: A Programmer's Perspective, 3rd) — 로드맵 전체에서 가장 중요한 책. 메모리 계층·캐시·어셈블리·링킹·동시성.
- [ ] **CMU 공개 Lab 전부 풀기 (9개, 읽기보다 이게 본체)** — `csapp.cs.cmu.edu/3e/labs.html`
  - [ ] Data Lab (Ch2)
  - [ ] Bomb Lab (Ch3)
  - [ ] Attack Lab (Ch3)
  - [ ] Architecture Lab, Y86-64 (Ch4) — 파이프라인 구조
  - [ ] **Cache Lab** (Ch6, cache-friendly code 감각)
  - [ ] **Performance Lab** (Ch5, 최적화 마인드셋 — HFT 직결)
  - [ ] Shell Lab (Ch8, 프로세스/시그널)
  - [ ] **Malloc Lab** (Ch9, 메모리 할당자 직접 구현)
  - [ ] **Proxy Lab** (Ch11-12, 동시성 네트워크 서버 — 트레이딩 엔진과 직결)
  - 산출물: Lab 풀이 레포 + "왜 빨라지는가" 짧은 노트
  - 진행 순서는 책 챕터 순서(Ch2→Ch12)를 따르면 자연스럽다.

### Phase 2 · 모던 C++ 숙련 (8~10주) — **순서 준수**
- [ ] **Effective C++** (Meyers, 3rd) — C++의 함정과 관용구
  - 산출물: Item별 `잘못된 코드 → 고친 코드` 스니펫 레포
- [ ] **Effective Modern C++** (Meyers) — C++11/14, 스마트 포인터, move semantics, 우측값 (HFT의 복사 제거 핵심)
  - 산출물: Item별 스니펫 레포에 이어서 정리
- [ ] **C++ Concurrency in Action** (Williams) — 스레딩, 메모리 모델, lock-free (트레이딩 엔진 = 동시성)
  - 산출물: 스레드풀 / lock-free 큐 미니 구현

### Phase 3 · 엔지니어링 장인정신 (4주, Phase 2와 겹쳐도 됨)
- [ ] **Design Patterns (GoF)** — 전부 외우지 말고 QuantLib에서 실물 확인(4번 연계)
  - 산출물: QuantLib 소스에서 패턴 찾아 주석 단 노트
- [ ] **Clean Code** (Martin) — 통독 1회 후 본인 코드에 상시 적용
  - 산출물: 옛 코드 하나 before/after 리팩터링
- [ ] **Code Complete** (McConnell) — 방대함. **정독 대상이 아니라 레퍼런스**. 아래 핵심 장 우선.
  - [ ] Ch.5~9 설계·클래스·루틴·방어적 프로그래밍
  - [ ] Ch.20~23 품질·리팩터링·디버깅
  - 산출물: 자기 코드 리뷰 체크리스트 1장으로 요약

### Phase 4 · 도메인 통합 — QuantLib (Phase 2 중반부터 병렬로 계속)
아래 4번 참조. 이 단계는 끝이 없고 프로젝트로 계속 이어진다.

### 트랙 B · 보조 도구 (전 기간 얕게)
- [ ] **Python for Data Analysis** (McKinney, pandas 저자) — Learning Python보다 **먼저**. 실무형.
  - 산출물: 실제 시장 데이터(yfinance 등) 분석 노트북 1개
- [ ] **Learning SQL** (Beaulieu) — 앞 6~7장(SELECT/JOIN/group by/서브쿼리)만으로 충분. 뒤는 참조.
  - 산출물: 트레이드 히스토리 스키마에 쿼리 실습
- [ ] **Learning Python** (Lutz) — 통독 X. **사전처럼** 필요할 때만 검색.

---

## 3. 트랙 C — LeetCode / HackerRank

**첫날부터 매일.** 학습이 끝난 뒤 시작하는 게 아니다.

- [ ] **반드시 C++로 풀기** — 알고리즘 + C++ 언어 숙련 1석2조 (STL·iterator·custom comparator)
- [ ] **패턴별 진행** (가이드: NeetCode 150 순서)
  - [ ] Arrays / Hashing
  - [ ] Two Pointers
  - [ ] Sliding Window
  - [ ] Stack
  - [ ] Binary Search
  - [ ] Linked List
  - [ ] Trees
  - [ ] Heap / Priority Queue
  - [ ] Backtracking
  - [ ] Graphs
  - [ ] Dynamic Programming
- [ ] **플랫폼 역할 분담**
  - LeetCode = 알고리즘/자료구조 면접 메인
  - HackerRank = ① C++ 도메인 트랙(문법·STL) ② SQL 도메인 트랙(트랙 B 복습). HFT 온라인 라운드가 HackerRank인 곳 많음.
- [ ] **규칙**: 25~30분 막히면 해설 → 며칠 뒤 **백지에서 재풀이**. 못 푼 문제만 따로 모음(진짜 자산).

---

## 4. QuantLib — 모든 걸 묶는 캡스톤

책의 모던 C++ + Design Patterns + 금융 도메인이 프로덕션급 코드로 만나는 유일한 지점.

- [ ] **1단계 · 빌드하고 굴리기** (Phase 2 중반)
  - [ ] 소스 받아 CMake로 직접 빌드 (링킹·빌드 지식 실전)
  - [ ] `Examples/` (BermudanSwaption, EquityOption 등) 실행·결과 해석
- [ ] **2단계 · 소스를 교재처럼 읽기** (가치 최고)
  - [ ] GoF 패턴 실물 확인: Observer(가격 전파), Visitor, Strategy, Factory, Template Method
  - [ ] Effective Modern C++의 스마트 포인터·RAII·템플릿이 실코드에 어떻게 쓰이는지 확인
  - 산출물: Design Patterns 노트 = QuantLib grep 결과 주석
- [ ] **3단계 · 작게 확장/기여** (포트폴리오)
  - [ ] 작은 기여: payoff 추가 / 테스트 케이스 추가 / 문서 오타 PR
  - [ ] 자작 미니 프로젝트: **간단한 오더북 + 매칭 엔진 in C++** (C++ Concurrency 연계) → 별도 레포. QD 포트폴리오의 꽃.

---

## 5. 진행 트래커

| Phase | 상태 | 시작일 | 완료일 | 핵심 산출물 링크 |
|---|---|---|---|---|
| 0 온램프 | ☐ | | | |
| 1 CS:APP + Labs | ☐ | | | |
| 2 모던 C++ | ☐ | | | |
| 3 엔지니어링 | ☐ | | | |
| 4 QuantLib | ☐ | | | |
| B 보조 도구 | ☐ | | | |
| C 알고리즘 | ☐ (매일) | | | |

**GitHub 포트폴리오 목표** (면접에서 실제로 작동하는 것들)
- [ ] CS:APP Labs 레포
- [ ] Effective C++/Modern C++ 스니펫 레포
- [ ] lock-free 자료구조 미니 구현
- [ ] pandas 시장 데이터 분석 노트북
- [ ] QuantLib 기여 PR 1건 이상
- [ ] 자작 오더북/매칭 엔진 프로젝트

---

*이 파일은 살아있는 문서. 매주 체크박스를 채우고, 각 산출물 링크를 표에 기록할 것.*
