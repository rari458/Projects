# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A university assignment (Korean course, docs in Korean). The task is to turn the in-memory B+ tree in `src/inmembpt/inmembpt.c` (Amittai Aviram's `bpt`) into a disk-based one that stores the whole tree in a single file of fixed 4096-byte pages. The student implements two files:

1. `src/dbbpt/file_manager.c`: page I/O and free-page management (the `TODO`s).
2. `src/dbbpt/dbbpt.c`: `db_find` / `db_insert` / `db_delete`, ported from `inmembpt.c` to use page numbers instead of pointers. `db_destroy` is already done.

The full spec is `assignment5_disk_based_bpt.pdf` in the repo root. It is untracked and written in Korean, and you can read it with `pdftotext -layout`. Its page layouts are summarized below. Submission is a ZIP named `assignment5_학번_이름.zip`, due 2026-11-24 23:59.

## Build & test

```bash
make all                  # builds bin/inmembpt, bin/file_manager_tester, bin/dbbpt
make dbbpt                # main.c + your dbbpt.c + your file_manager.c  (graded binary)
make file_manager_tester  # main.c + your file_manager.c + TA's prebuilt B+ tree object
make inmembpt             # reference in-memory tree: ./bin/inmembpt [order]
make reset_test_env       # wipe and recreate test_out/ — run before every test run
make clean                # removes bin/
```

There is no linter or automated test runner. Tests are command scripts that you run through the REPL's `e` command. You can run them without the prompt because `main` reads stdin until EOF:

```bash
make reset_test_env && echo "e tc.txt" | ./bin/dbbpt
echo "e tc.txt 1 1" | ./bin/dbbpt        # echo commands + print tree after each i/d
make reset_test_env && echo "e tc_lg.txt" | ./bin/file_manager_tester   # never use echo/resp with tc_lg.txt (huge output)
```

- **Reading results:** in a script, a line starting with `#` is printed as text, not treated as a comment. Each test prints its expected leaf output as a `# (k, v) ...` line, followed by the real output of `l`. Compare the two lines by eye.
- **Why reset first:** `o <path>` reopens an existing file instead of recreating it, so files left in `test_out/` from an earlier run would carry stale tree state.
- **Running one scenario:** write a small command file with the same syntax (`o test_out/x.tree <l_ord> <i_ord>`, `i k [v]`, `d k`, `f k`, `l`, `t`, `c`) and run it with `e`.
- Grading uses `./bin/dbbpt`. If that binary doesn't work, grading falls back to `file_manager_tester` with a deduction. That makes `file_manager.c` the first thing to get correct.
- **Existing warnings:** `-Wformat` warnings in `main.c` (`%lld` used with `int64_t`) are already there in the provided code and do no harm.

## Architecture

**Linking and the ABI constraint.** `gift_from_ta/dbbpt_{linux,mac}.o` (the Makefile picks one by `uname`) is a complete compiled `dbbpt.c`. `file_manager_tester` links it in place of your `dbbpt.c`. It was compiled against the current `file_manager.h`, so **do not change the `page`/`header_page` struct layouts or the function prototypes in `file_manager.h`**, or that binary will break. Helper prototypes for `dbbpt.c` go in the `TODO` slots in `dbbpt.h`. The object's symbols show the expected helper breakdown, which mirrors `inmembpt.c`: `find_leaf`, `insert_into_leaf[_after_splitting]`, `insert_into_parent`, `insert_into_new_root`, `insert_into_page[_after_splitting]`, `start_new_tree`, `delete_entry`, `remove_entry_from_{leaf,internal}_page`, `adjust_root`, `coalesce_pages`, `redistribute_pages`, `get_neighbor_index`, `get_left_index`, `cut`. It allocates pages only through `alloc_page1`.

**In-memory `page` ≠ on-disk page.** The `page` struct in `file_manager.h` is a union-like convenience struct and is not the byte layout. `load_page`/`write_page` must serialize field by field with `pread`/`pwrite` at `pgn * PAGE_SIZE + offset`, the same way `load_header_page` does. `page.pgn` is not stored on disk: `load_page` must set it, and `write_page` uses `src->pgn` to find where to write.

On-disk layouts (from the PDF):

| Page | Layout |
|---|---|
| Header (page 0) | `0` free_pgn (i64, head of free list) · `8` root_pgn (i64) · `16` num_pages (i64) · `24` leaf_order (int) · `28` internal_order (int) |
| Free | `0` next free pgn (i64) |
| Leaf | `0` parent_pgn (i64) · `8` is_leaf=1 (int) · `12` num_keys (int) · `120` right_sibling_pgn (i64) · `128 + 128*i` key (i64) + value (char[120]), up to 31 records |
| Internal | `0` parent_pgn · `8` is_leaf=0 · `12` num_keys · `120` **rightmost** child pgn (= `child_pgns[num_keys]`) · `128 + 16*i` key (i64) + child pgn (i64) (= `keys[i]`, `child_pgns[i]`), up to 248 entries |

**Conventions the existing code relies on:**
- **Null page numbers:** `-1` means "no page" (empty root, end of the free list, no sibling, root's parent). Page 0 is always the header, so `destroy_pages` treats `pgn <= 0` as null.
- **Free list:** a singly linked list that starts at `header.free_pgn`. `free_page` pushes a page onto it. When the list is empty, `alloc_page1` doubles the pool by appending pages at EOF (`INIT_PAGE_COUNT` sets the initial size).
- **Header persistence:** `alloc_page(fd)` never writes the header back. So `alloc_page1` must update the `header_page*` it is passed (free_pgn, num_pages) and persist it. That keeps a caller's in-memory header copy consistent before the caller writes `root_pgn`.
- **Ownership:** `alloc_page*` returns a `malloc`ed page that the caller frees. `main.c`'s `find_and_print` frees only `*leaf_out`, so the `record*` that `db_find` returns should point into that leaf buffer and not be a separate allocation.
- **Orders:** `inmembpt` nodes hold at most `order - 1` keys. The array sizes match that: `MAX_LEAF_ORDER 32` gives `records[31]`, and `MAX_INTERNAL_ORDER 249` gives `keys[248]`/`child_pgns[249]`. The comment on `header_page.leaf_order` ("maximum number of pairs") contradicts this, so watch for off-by-one errors. Orders are given per file with `o <path> [l_ord] [i_ord]` and stored in the header.
- **Printing:** `main.c` walks the tree using `child_pgns[0..num_keys]` and follows `right_sibling_pgn` until it hits a negative value, so those fields must be filled in correctly after `load_page`.
- **Duplicate keys:** inserting a key that already exists overwrites its value (`tc.txt` test 4). Values are at most 119 characters plus the terminating NUL.
