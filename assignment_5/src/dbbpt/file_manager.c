#include "file_manager.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// On-disk byte offsets inside a leaf/internal page.
#define PARENT_PGN_OFFSET 0
#define IS_LEAF_OFFSET 8
#define NUM_KEYS_OFFSET 12
#define SPECIAL_PGN_OFFSET 120 // leaf: right sibling, internal: rightmost child
#define ENTRIES_OFFSET 128
#define LEAF_ENTRY_SIZE 128		// key (8) + value (120)
#define INTERNAL_ENTRY_SIZE 16  // key (8) + child pgn (8)
#define VALUE_SIZE 120

static off_t page_offset(int64_t pgn)
{
	return (off_t)pgn * PAGE_SIZE;
}

static int clamp_order(int order, int min, int max)
{
	if (order < min) return min;
	if (order > max) return max;
	return order;
}

// Overwrite a whole page with zeros, except the next free page number at offset 0.
static void write_free_page(int fd, int64_t pgn, int64_t next_pgn)
{
	char buf[PAGE_SIZE] = {0};
	memcpy(buf, &next_pgn, sizeof(next_pgn));
	if (pwrite(fd, buf, PAGE_SIZE, page_offset(pgn)) != PAGE_SIZE) exit_with_err_msg("Error on writing free page.");
}

/**
 * @brief Open a database file or create a new one if it doesn't exist.
 * @param file_path[in] The path to the database file.
 * @param leaf_order[in] The leaf order of the B+ tree.
 * @param internal_order[in] The internal order of the B+ tree.
 * @return The file descriptor of the database file. Return -1 if failed.
 *
 * Set the header page and free pages pool during tree creation. Plus, use -1
 * to represent a NULL page number for fields such as the initial root page number
 * in header page or next page number of the last free page.
 */
int open_or_create_tree(const char *file_path, int leaf_order, int internal_order) 
{
	int fd = open(file_path, O_RDWR | O_CREAT, 0644);
	if (fd == -1)
	{
		fprintf(stderr, "Error: Could not open database file '%s'.\n", file_path);
		return -1;
	}

	off_t file_size = lseek(fd, 0, SEEK_END);
	if (file_size == -1)
	{
		fprintf(stderr, "Error: Could not read size of database file '%s'.\n", file_path);
		close(fd);
		return -1;
	}

	// Existing tree: the header already holds the orders, so the arguments are ignored.
	if (file_size > 0) return fd;

	// New tree: header page + (INIT_PAGE_COUNT - 1) free pages chained 1 -> 2 -> ... -> NULL.
	header_page header;
	header.free_pgn = 1;
	header.root_pgn = NULL_PGN;
	header.num_pages = INIT_PAGE_COUNT;
	header.leaf_order = clamp_order(leaf_order, MIN_LEAF_ORDER, MAX_LEAF_ORDER);
	header.internal_order = clamp_order(internal_order, MIN_INTERNAL_ORDER, MAX_INTERNAL_ORDER);

	for (int64_t pgn = 1; pgn < INIT_PAGE_COUNT; pgn++) 
		write_free_page(fd, pgn, (pgn + 1 < INIT_PAGE_COUNT) ? pgn + 1 : NULL_PGN);
	write_header_page(fd, &header);

	return fd;
}

/**
 * @brief Load the header page from the database file.
 * @param fd[in] The file descriptor of the database file.
 * @param dest[out] The destination to store the header page.
 */
void load_header_page(int fd, header_page* dest) {
	off_t cur_offset = 0;
	if (pread(fd, &(dest->free_pgn), 8, cur_offset) == -1) exit_with_err_msg("Error on loading free page number at header page.");
	cur_offset += 8;

	if (pread(fd, &(dest->root_pgn), 8, cur_offset) == -1) exit_with_err_msg("Error on loading root page number at header page.");
	cur_offset += 8;

	if (pread(fd, &(dest->num_pages), 8, cur_offset) == -1) exit_with_err_msg("Error on loading number of pages at header page.");
	cur_offset += 8;

	if (pread(fd, &(dest->leaf_order), 4, cur_offset) == -1) exit_with_err_msg("Error on loading leaf order at header page.");
	cur_offset += 4;

	if (pread(fd, &(dest->internal_order), 4, cur_offset) == -1) exit_with_err_msg("Error on loading internal order at header page.");
	cur_offset += 4;
}

/**
 * @brief Write the header page to the database file.
 * @param fd[in] The file descriptor of the database file.
 * @param src[in] The header page to write.
 */
void write_header_page(int fd, const header_page* src) {
	off_t cur_offset = 0;
	if (pwrite(fd, &(src->free_pgn), 8, cur_offset) < 8) exit_with_err_msg("Error on writing free page number at header page.");
	cur_offset += 8;

	if (pwrite(fd, &(src->root_pgn), 8, cur_offset) < 8) exit_with_err_msg("Error on writing root page number at header page.");
	cur_offset += 8;

	if (pwrite(fd, &(src->num_pages), 8, cur_offset) < 8) exit_with_err_msg("Error on writing number of pages at header page.");
	cur_offset += 8;

	if (pwrite(fd, &(src->leaf_order), 4, cur_offset) < 4) exit_with_err_msg("Error on writing leaf order at header page.");
	cur_offset += 4;

	if (pwrite(fd, &(src->internal_order), 4, cur_offset) < 4) exit_with_err_msg("Error on writing internal order at header page.");
	cur_offset += 4;
}

/**
 * @brief Load a page from the database file.
 * @param fd[in] The file descriptor of the database file.
 * @param pgn[in] The page number of the page to load.
 * @param dest[out] The destination to store the page.
 */
void load_page(int fd, int64_t pgn, page* dest) 
{
	char buf[PAGE_SIZE];
	if (pread(fd, buf, PAGE_SIZE, page_offset(pgn)) != PAGE_SIZE) exit_with_err_msg("Error on loading page.");

	int is_leaf;
	dest->pgn = pgn;
	memcpy(&dest->parent_pgn, buf + PARENT_PGN_OFFSET, 8);
	memcpy(&is_leaf, buf + IS_LEAF_OFFSET, 4);
	memcpy(&dest->num_keys, buf + NUM_KEYS_OFFSET, 4);
	dest->is_leaf = (is_leaf == 1);

	if (dest->is_leaf)
	{
		memcpy(&dest->right_sibling_pgn, buf + SPECIAL_PGN_OFFSET, 8);
		for (int i = 0; i < dest->num_keys; i++)
		{
			const char *entry = buf + ENTRIES_OFFSET + i * LEAF_ENTRY_SIZE;
			memcpy(&dest->keys[i], entry, 8);
			memcpy(dest->records[i].value, entry + 8, VALUE_SIZE);
		}
	}
	else
	{
		memcpy(&dest->child_pgns[dest->num_keys], buf + SPECIAL_PGN_OFFSET, 8);
		for (int i = 0; i < dest->num_keys; i++)
		{
			const char *entry = buf + ENTRIES_OFFSET + i * INTERNAL_ENTRY_SIZE;
			memcpy(&dest->keys[i], entry, 8);
			memcpy(&dest->child_pgns[i], entry + 8, 8);
		}
	}
}

/**
 * @brief Write a page to the database file.
 * @param fd[in] The file descriptor of the database file.
 * @param src[in] The page to write. Return NULL if failed.
 */
void write_page(int fd, const page* src) 
{
	char buf[PAGE_SIZE] = {0};

	int is_leaf = src->is_leaf ? 1 : 0;
	memcpy(buf + PARENT_PGN_OFFSET, &src->parent_pgn, 8);
	memcpy(buf + IS_LEAF_OFFSET, &is_leaf, 4);
	memcpy(buf + NUM_KEYS_OFFSET, &src->num_keys, 4);

	if (src->is_leaf)
	{
		memcpy(buf + SPECIAL_PGN_OFFSET, &src->right_sibling_pgn, 8);
		for (int i = 0; i < src->num_keys; i++)
		{
			char *entry = buf + ENTRIES_OFFSET + i * LEAF_ENTRY_SIZE;
			memcpy(entry, &src->keys[i], 8);
			memcpy(entry + 8, src->records[i].value, VALUE_SIZE);
		}
	}
	else
	{
		memcpy(buf + SPECIAL_PGN_OFFSET, &src->child_pgns[src->num_keys], 8);
		for (int i = 0; i < src->num_keys; i++)
		{
			char *entry = buf + ENTRIES_OFFSET + i * INTERNAL_ENTRY_SIZE;
			memcpy(entry, &src->keys[i], 8);
			memcpy(entry + 8, &src->child_pgns[i], 8);
		}
	}

	if (pwrite(fd, buf, PAGE_SIZE, page_offset(src->pgn)) != PAGE_SIZE) exit_with_err_msg("Error on writing page.");
}

/**
 * @brief Allocate a new page.
 * @param fd[in] The file descriptor of the database file.
 * @return The new page.
 *
 * If no free pages are left, this function doubles the free pages pool, and then allocates one.
 * If memory allocation fails, then kill the process using the `exit_with_err_msg()` function.
 */
page *alloc_page(int fd) {
	header_page header;
	load_header_page(fd, &header);

	return alloc_page1(fd, &header);
}

/**
 * @brief Allocate a new page. This function uses the passed header_page pointer instead of calling load_header_page.
 * @param fd[in] The file descriptor of the database file.
 * @param header_page[in] The header page.
 * @return The new page.
 *
 * If no free pages are left, this function doubles the free pages pool, and then allocates one.
 * If memory allocation fails, then kill the process using the `exit_with_err_msg()` function.
 */
page *alloc_page1(int fd, header_page *header_page) {
	// No free page left: double the file and chain the new pages num_pages -> ... -> NULL.
	if (header_page->free_pgn == NULL_PGN)
	{
		int64_t old_num_pages = header_page->num_pages;
		int64_t new_num_pages = old_num_pages * 2;
		for (int64_t pgn = old_num_pages; pgn < new_num_pages; pgn++)
			write_free_page(fd, pgn, (pgn + 1 < new_num_pages) ? pgn + 1 : NULL_PGN);
		header_page->free_pgn = old_num_pages;
		header_page->num_pages = new_num_pages;
	}

	// Pop the head of the free page list.
	int64_t pgn = header_page->free_pgn;
	int64_t next_free_pgn;
	if (pread(fd, &next_free_pgn, 8, page_offset(pgn)) != 8) exit_with_err_msg("Error on loading next free page number.");
	header_page->free_pgn = next_free_pgn;
	write_header_page(fd, header_page);

	page *new_page = (page *)calloc(1, sizeof(page));
	if (new_page == NULL) exit_with_err_msg("Error on allocating memory fr a new page.");
	new_page->pgn = pgn;
	new_page->parent_pgn = NULL_PGN;
	new_page->is_leaf = false;
	new_page->num_keys = 0;
	new_page->right_sibling_pgn = NULL_PGN;
	new_page->next_pgn = NULL_PGN;
	return new_page;
}

/**
 * @brief Free a page.
 * @param fd[in] The file descriptor of the database file.
 * @param pgn[in] The page number of the page to free.
 */
void free_page(int fd, int64_t pgn) 
{
	header_page header;
	load_header_page(fd, &header);

	// Push the page onto the head of the free page list.
	write_free_page(fd, pgn, header.free_pgn);
	header.free_pgn = pgn;
	write_header_page(fd, &header);
}

/**
 * @brief Print an error message and exit the program.
 * @param err_msg[in] The error message to print.
 */
void exit_with_err_msg(const char* err_msg) {
	perror(err_msg);
	exit(EXIT_FAILURE);
}
