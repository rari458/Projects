# Assignment 5 - Disk Based B+tree (Basic Database Management System)

디스크에서 관리되는 B+tree 를 구현해 간단한 Database Management System을 제작합니다.

1. PDF에 있는 페이지 설명을 바탕으로 `src/dbbpt/file_manager.c`를 완성합니다.
2. `src/inmembpt/inmembpt.c`를 참고하여 `src/dbbpt/dbbpt.c`를 완성합니다.

## 🗓️ 제출 기한
- <b style='background-color: #ffdce0'>2026년 11월 24일 (화) 23시 59분</b>

## 🗓️ 제출 방식

전체 소스 코드를 하나의 ZIP 파일로 압축하여 LMS 과제 제출란에 제출합니다.
파일명: assignment5_학번_이름.zip

## 🛠️ 빌드 및 실행

### 전체 빌드

`make` 또는 `make all` 명령어로 모든 실행 파일을 한 번에 빌드할 수 있습니다.

```bash
make all
```

### 부분 빌드

특정 목표만 빌드할 수도 있습니다.

- `make inmembpt`: 메모리 기반 B+ Tree 예제(`inmembpt`)를 빌드합니다.
- `make dbbpt`: 직접 구현한 `file_manager.c`와 `dbbpt.c`를 사용하여 `dbbpt`를 빌드합니다.
- `make file_manager_tester`: `file_manager.c`만 구현했을 때 테스트할 수 있도록, 완성된 `dbbpt.o`와 연결하여 `file_manager_tester`를 빌드합니다.

>빌드된 모든 실행 파일은 `bin/` 디렉토리에 생성됩니다.

### 실행 파일 안내

#### 1. `./bin/inmembpt`

- **설명:** 메모리에서 동작하는 B+ Tree 예제입니다.
- **실행:**
  ```bash
  # order 값을 지정하여 실행 (기본값: 4)
  ./bin/inmembpt [<order>]
  ```
- **명령어:** `?`를 입력하여 도움말을 확인하세요.

#### 2. `./bin/dbbpt`

- **설명:** 직접 구현한 디스크 기반 B+ Tree입니다.
- **실행:**
  ```bash
  ./bin/dbbpt
  ```
- **사용법:**
  1.  `o <path> [l_ord] [i_ord]` 명령어로 데이터베이스 파일을 엽니다. (없으면 새로 생성)
  2.  `i`, `f`, `d` 등의 명령어로 데이터를 조작합니다.
  3.  `c` 명령어로 현재 파일을 닫고, 다시 `o`를 이용해 다른 파일을 열 수 있습니다.
  4.  `e <path> [echo] [resp]` 명령어로 외부 파일에 있는 명령어를 한번에 실행할 수 있습니다.
- **명령어:** `?`를 입력하여 도움말을 확인하세요.
  > 채점은 이 실행 파일을 기준으로 진행됩니다.

#### 3. `./bin/file_manager_tester`

- **설명:** `file_manager.c`만 구현한 상태에서 테스트하기 위한 실행 파일입니다.
- **실행:** `dbbpt`와 동일하게 실행하고 사용합니다.
  > `./bin/dbbpt` 파일이 완전히 실행되지 않을 경우에는 감점 후 해당 파일로 채점 진행합니다

---

## ✅ 테스트

제공된 테스트 케이스(`tc.txt`, `tc_lg.txt`)를 통해 구현한 코드를 테스트할 수 있습니다.

### 테스트 환경 초기화

테스트 실행 전, `test_out` 디렉토리를 초기화해야 합니다.

```bash
make reset_test_env
```

### 테스트 케이스 실행

`dbbpt` 또는 `file_manager_tester`의 프롬프트에서 `e` 명령어를 사용하여 테스트 파일을 실행할 수 있습니다.

```bash
# 1. dbbpt 실행
./bin/dbbpt

# 2. 프롬프트에서 tc.txt 실행
> e tc.txt
```

> `e tc.txt 1 1` 처럼 `echo`와 `response`를 켜서 좀 더 자세한 실행 결과를 얻을 수도 있습니다.
> `tc_lg.txt`는 다량의 명령어를 실행하기 때문에 `echo`와 `response`를 켜지 마세요!

### 커스텀 테스트 케이스

`tc.txt` 파일과 같이 명령어 목록을 작성하여 자신만의 테스트 케이스를 만들 수 있습니다. `#`으로 시작하는 라인은 주석 대신 화면에 해당 텍스트를 출력하는 용도로 사용할 수 있습니다.

---

## 🧹 빌드 정리

빌드 과정에서 생성된 `bin` 디렉토리와 실행 파일들을 삭제합니다.

```bash
make clean
```
