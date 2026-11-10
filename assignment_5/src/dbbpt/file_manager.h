#ifndef __FILE_MANAGER_H__
#define __FILE_MANAGER_H__

#include <stdint.h>
#include <stdbool.h>
#ifdef _WIN32
#define bool char
#define false 0
#define true 1
#endif

#define MIN_LEAF_ORDER 3
#define MIN_INTERNAL_ORDER 3
#define MAX_LEAF_ORDER 32
#define MAX_INTERNAL_ORDER 249
#define DEFAULT_LEAF_ORDER 32
#define DEFAULT_INTERNAL_ORDER 249

#define INIT_PAGE_COUNT 4

// Type definitions
typedef uint64_t pagenum_t;

// Constants
#define PAGE_SIZE 4096
#define HEADER_PAGE_NUM 0
#define NULL_PGN -1 // "no page" (empty root, end of free list, no sibling, no parent)

// Structures
typedef struct record {
	char value[120];
} record;

typedef struct page {
	int64_t pgn;

	int64_t parent_pgn;
	bool is_leaf;
	int num_keys;
	int64_t keys[248];

	record records[31]; // for leaf page
	int64_t right_sibling_pgn; // for leaf page

	int64_t child_pgns[249]; // for internal page

	int64_t next_pgn; // for free page
} page;

typedef struct header_page {
	int64_t free_pgn;
	int64_t root_pgn;
	int64_t num_pages;

	// A maximum number of (key, value) pairs in the leaf page
	int leaf_order;
	// A maximum number of children in the internal node. The number of keys in the internal node is (internal_order - 1)
	int internal_order;
} header_page;

// Function prototypes
int open_or_create_tree(const char *file_path, int leaf_order, int internal_order);
void load_header_page(int fd, header_page* dest);
void write_header_page(int fd, const header_page* src);
void load_page(int fd, int64_t pgn, page* dest);
void write_page(int fd, const page* src);
page *alloc_page(int fd);
page *alloc_page1(int fd, header_page* header);
void free_page(int fd, int64_t pgn);

// Helper functions
void exit_with_err_msg(const char* err_msg);

#endif /* __FILE_MANAGER_H__ */
