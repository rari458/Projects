#include "file_manager.h"
#include "dbbpt.h"

#include <inttypes.h>
#include <stdbool.h>
#ifdef _WIN32
#define bool char
#define false 0
#define true 1
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// FUNCTION DEFINITIONS.
// Find API
/**
 * @brief Find a record with the given key.
 * @param fd[in] The file descriptor of the database file.
 * @param key[in] The key to find.
 * @param verbose[in] Whether to print verbose output.
 * @param leaf_out[out] The leaf page pointer where the key is found.
 * @return The record with the given key, or NULL if not found.
 */
record *db_find(int fd, int64_t key, bool verbose, page **leaf_out) 
{
	header_page header;
	load_header_page(fd, &header);

	*leaf_out = NULL;
	if (header.root_pgn == NULL_PGN)
	{
		if (verbose) printf("Empty tree.\n");
		return NULL;
	}

	page *leaf = (page *)malloc(sizeof(page));
	if (leaf == NULL) exit_with_err_msg("Error on allocating memory for a leaf page.");
	find_leaf(fd, header.root_pgn, key, verbose, leaf);
	*leaf_out = leaf;

	int i = find_key_index(leaf, key);
	return (i == -1) ? NULL : &leaf->records[i];
}

// Helper functions for find API
/**
 * @brief Trace the path from the root to the leaf that would hold the key.
 * @param root_pgn[in] The root page number. Must not be NULL_PGN.
 * @param dest[out] The leaf page.
 */
void find_leaf(int fd, int64_t root_pgn, int64_t key, bool verbose, page *dest)
{
	load_page(fd, root_pgn, dest);
	while (!dest->is_leaf)
	{
		if (verbose) print_page_keys(dest);
		int i = 0;
		while (i < dest->num_keys && key >= dest->keys[i]) i++;
		if (verbose) printf("%d ->\n", i);
		load_page(fd, dest->child_pgns[i], dest);
	}
	if (verbose)
	{
		printf("Leaf ");
		print_page_keys(dest);
	}
}

/**
 * @brief Return the index of the key in the page, or -1 if it is not there.
 */
int find_key_index(const page *p, int64_t key)
{
	for (int i = 0; i < p->num_keys; i++)
		if (p->keys[i] == key) return i;
	return -1;
}

// Insertion API
/**
 * @brief Insert a record with the given key and value.
 * @param fd[in] The file descriptor of the database file.
 * @param key[in] The key to insert.
 * @param value[in] The value to insert.
 */
void db_insert(int fd, int64_t key, char *value) 
{
	header_page header;
	load_header_page(fd, &header);

	// Case: the tree does not exist yet.
	if (header.root_pgn == NULL_PGN)
	{
		start_new_tree(fd, &header, key, value);
		return ;
	}

	page leaf;
	find_leaf(fd, header.root_pgn, key, false, &leaf);

	// Case: duplicate key. Update the value.
	int i = find_key_index(&leaf, key);
	if (i != -1)
	{
		set_record(&leaf.records[i], value);
		write_page(fd, &leaf);
		return;
	}

	// Case: leaf has room for the record.
	if (leaf.num_keys < header.leaf_order - 1)
	{
		insert_into_leaf(&leaf, key, value);
		write_page(fd, &leaf);
		return;
	}

	// Case: leaf must be split.
	insert_into_leaf_after_splitting(fd, &header, &leaf, key, value);
}

// Helper functions for insertion API
// Every helper that allocates a page takes the caller's header_page, so alloc_page1()
// keeps it up to date and it can be written back safely when the root changes.

/**
 * @brief First insertion: create a root leaf holding a single record.
 */
void start_new_tree(int fd, header_page *header, int64_t key, const char *value)
{
	page *root = alloc_page1(fd, header);
	root->is_leaf = true;
	root->parent_pgn = NULL_PGN;
	root->right_sibling_pgn = NULL_PGN;
	root->keys[0] = key;
	set_record(&root->records[0], value);
	root->num_keys = 1;
	write_page(fd, root);

	header->root_pgn = root->pgn;
	write_header_page(fd, header);
	free(root);
}

/**
 * @brief Insert a record into a leaf that has room for it. Memory only; the caller writes the page.
 */
void insert_into_leaf(page *leaf, int64_t key, const char *value)
{
	int insertion_point = 0;
	while (insertion_point < leaf->num_keys && leaf->keys[insertion_point] < key) insertion_point++;

	for (int i = leaf->num_keys; i > insertion_point; i--)
	{
		leaf->keys[i] = leaf->keys[i - 1];
		leaf->records[i] = leaf->records[i - 1];
	}
	leaf->keys[insertion_point] = key;
	set_record(&leaf->records[insertion_point], value);
	leaf->num_keys++;
}

/**
 * @brief Insert a record into a full leaf, splitting it in half and pushing the
 * first key of the new (right) leaf up into the parent.
 */
void insert_into_leaf_after_splitting(int fd, header_page *header, page *leaf, int64_t key, const char *value)
{
	int order = header->leaf_order;
	int64_t temp_keys[MAX_LEAF_ORDER];
	record temp_records[MAX_LEAF_ORDER];
	int i, j;

	int insertion_index = 0;
	while (insertion_index < leaf->num_keys && leaf->keys[insertion_index] < key) insertion_index++;

	for (i = 0, j = 0; i < leaf->num_keys; i++, j++)
	{
		if (j == insertion_index) j++;
		temp_keys[j] = leaf->keys[i];
		temp_records[j] = leaf->records[i];
	}
	temp_keys[insertion_index] = key;
	set_record(&temp_records[insertion_index], value);

	page *new_leaf = alloc_page1(fd, header);
	new_leaf->is_leaf = true;

	int split = cut(order - 1);
	leaf->num_keys = 0;
	for (i = 0; i < split; i++)
	{
		leaf->keys[i] = temp_keys[i];
		leaf->records[i] = temp_records[i];
		leaf->num_keys++;
	}
	for (i = split, j = 0; i < order; i++, j++)
	{
		new_leaf->keys[j] = temp_keys[i];
		new_leaf->records[j] = temp_records[i];
		new_leaf->num_keys++;
	}

	new_leaf->right_sibling_pgn = leaf->right_sibling_pgn;
	leaf->right_sibling_pgn = new_leaf->pgn;
	new_leaf->parent_pgn = leaf->parent_pgn;

	// Persist both halves before touching the parent; they are not written again afterward.
	write_page(fd, leaf);
	write_page(fd, new_leaf);

	insert_into_parent(fd, header, leaf, new_leaf->keys[0], new_leaf);
	free(new_leaf);
}

/**
 * @brief Insert the key and the right page into the parent of the left page.
 * Both left and right must be already be written to disk.
 */
void insert_into_parent(int fd, header_page *header, page *left, int64_t key, page *right)
{
	// Case: new root.
	if (left->parent_pgn == NULL_PGN)
	{
		insert_into_new_root(fd, header, left, key, right);
		return;
	}

	page parent;
	load_page(fd, left->parent_pgn, &parent);
	int left_index = get_left_index(&parent, left->pgn);

	// Simple case: the new key fits into the parent.
	if (parent.num_keys < header->internal_order - 1)
	{
		insert_into_page(&parent, left_index, key, right->pgn);
		write_page(fd, &parent);
		return;
	}

	// Harder case: split the parent.
	insert_into_page_after_splitting(fd, header, &parent, left_index, key, right->pgn);
}

/**
 * @brief Create a new root with two children, and update the header.
 */
void insert_into_new_root(int fd, header_page *header, page *left, int64_t key, page *right)
{
	page *root = alloc_page1(fd, header);
	root->is_leaf = false;
	root->parent_pgn = NULL_PGN;
	root->keys[0] = key;
	root->child_pgns[0] = left->pgn;
	root->child_pgns[1] = right->pgn;
	root->num_keys = 1;
	write_page(fd, root);

	left->parent_pgn = root->pgn;
	right->parent_pgn = root->pgn;
	write_page(fd, left);
	write_page(fd, right);

	header->root_pgn = root->pgn;
	write_header_page(fd, header);
	free(root);
}

/**
 * @brief Insert a key and its right child into an internal page that has room. Memory only.
 */
void insert_into_page(page *p, int left_index, int64_t key, int64_t right_pgn)
{
	for (int i = p->num_keys; i > left_index; i--)
	{
		p->child_pgns[i + 1] = p->child_pgns[i];
		p->keys[i] = p->keys[i - 1];
	}
	p->child_pgns[left_index + 1] = right_pgn;
	p->keys[left_index] = key;
	p->num_keys++;
}

/**
 * @brief Insert a key and its right child into a full internal page, splitting it
 * and pushing the middle key (k_prime) up into the parent.
 */
void insert_into_page_after_splitting(int fd, header_page *header, page *old_page, int left_index, int64_t key, int64_t right_pgn)
{
	int order = header->internal_order;
	int64_t temp_keys[MAX_INTERNAL_ORDER];
	int64_t temp_child_pgns[MAX_INTERNAL_ORDER + 1];
	int i, j;

	for (i = 0, j = 0; i < old_page->num_keys + 1; i++, j++)
	{
		if (j == left_index + 1) j++;
		temp_child_pgns[j] = old_page->child_pgns[i];
	}
	for (i = 0, j = 0; i < old_page->num_keys; i++, j++)
	{
		if (j == left_index) j++;
		temp_keys[j] = old_page->keys[i];
	}
	temp_child_pgns[left_index + 1] = right_pgn;
	temp_keys[left_index] = key;

	page *new_page = alloc_page1(fd, header);
	new_page->is_leaf = false;

	int split = cut(order);
	old_page->num_keys = 0;
	for (i = 0; i < split - 1; i++)
	{
		old_page->child_pgns[i] = temp_child_pgns[i];
		old_page->keys[i] = temp_keys[i];
		old_page->num_keys++;
	}
	old_page->child_pgns[i] = temp_child_pgns[i];
	int64_t k_prime = temp_keys[split - 1];
	for (++i, j = 0; i < order; i++, j++)
	{
		new_page->child_pgns[j] = temp_child_pgns[i];
		new_page->keys[j] = temp_keys[i];
		new_page->num_keys++;
	}
	new_page->child_pgns[j] = temp_child_pgns[i];
	new_page->parent_pgn = old_page->parent_pgn;

	write_page(fd, old_page);
	write_page(fd, new_page);

	// Childrent that moved to the new page must point to it on disk.
	for (i = 0; i <= new_page->num_keys; i++) set_parent_pgn(fd, new_page->child_pgns[i], new_page->pgn);

	insert_into_parent(fd, header, old_page, k_prime, new_page);
	free(new_page);
}

/**
 * @brief Return the index of left_pgn in the parent's child_pgns.
 */
int get_left_index(const page *parent, int64_t left_pgn)
{
	int left_index = 0;
	while (left_index <= parent->num_keys && parent->child_pgns[left_index] != left_pgn) left_index++;
	return left_index;
}

// Deletion API
/**
 * @brief Delete a record with the given key.
 * @param fd[in] The file descriptor of the database file.
 * @param key[in] The key to delete.
 */
void db_delete(int fd, int64_t key) 
{
	header_page header;
	load_header_page(fd, &header);
	if (header.root_pgn == NULL_PGN) return;

	page leaf;
	find_leaf(fd, header.root_pgn, key, false, &leaf);
	if (find_key_index(&leaf, key) == -1) return;

	delete_entry(fd, &header, &leaf, key, NULL_PGN);
}

// Helper functions for delete API
// free_page() rewrites the header on disk, so the header_page passed around here is only
// used for the orders. Code that changes root_pgn reloads the header first (adjust_root).

/**
 * @brief Remove an entry from a page and rebalance the tree if the page underflows.
 * @param n[in] The page, already loaded. It is written (or freed) by this funciton.
 * @param key[in] The key to remove.
 * @param child_pgn[in] Internal page only: the child page number to remove. Ignored for leaves.
 */
void delete_entry(int fd, const header_page *header, page *n, int64_t key, int64_t child_pgn)
{
	if (n->is_leaf) remove_entry_from_leaf_page(n, key);
	else remove_entry_from_internal_page(n, key, child_pgn);

	// Case: deletion from the root.
	if (n->parent_pgn == NULL_PGN)
	{
		adjust_root(fd, n);
		return;
	}

	// Case: page stays at or above the minimum.
	int min_keys = n->is_leaf ? cut(header->leaf_order - 1) : cut(header->internal_order) - 1;
	if (n->num_keys >= min_keys)
	{
		write_page(fd, n);
		return;
	}

	// Case: page falls below the minimum. Find the neighbor and the key between them (k-prime).
	page parent;
	load_page(fd, n->parent_pgn, &parent);
	int neighbor_index = get_neighbor_index(&parent, n->pgn);
	int k_prime_index = (neighbor_index == -1) ? 0 : neighbor_index;
	int64_t k_prime = parent.keys[k_prime_index];

	page neighbor;
	load_page(fd, (neighbor_index == -1) ? parent.child_pgns[1] : parent.child_pgns[neighbor_index], &neighbor);

	int capacity = n->is_leaf ? header->leaf_order : header->internal_order - 1;
	if (neighbor.num_keys + n->num_keys < capacity) coalesce_pages(fd, header, n, &neighbor, &parent, neighbor_index, k_prime);
	else redistribute_pages(fd, n, &neighbor, &parent, neighbor_index, k_prime_index, k_prime);
}

/**
 * @brief Remove a key and its record from a leaf. Memory only.
 */
void remove_entry_from_leaf_page(page *leaf, int64_t key)
{
	int i = find_key_index(leaf, key);
	for (++i; i < leaf->num_keys; i++)
	{
		leaf->keys[i - 1] = leaf->keys[i];
		leaf->records[i - 1] = leaf->records[i];
	}
	leaf->num_keys--;
}

/**
 * @brief Remove a key and a child page number from an internal page. Memory only.
 */
void remove_entry_from_internal_page(page *p, int64_t key, int64_t child_pgn)
{
	int i = find_key_index(p, key);
	for (++i; i < p->num_keys; i++) p->keys[i - 1] = p->keys[i];

	int num_children = p->num_keys + 1;
	i = 0;
	while (p->child_pgns[i] != child_pgn) i++;
	for (++i; i < num_children; i++) p->child_pgns[i - 1] = p->child_pgns[i];

	p->num_keys--;
}

/**
 * @brief Fix the root after a deletion from it: free it if it became empty and
 * promote its only child (or empty the tree).
 */
void adjust_root(int fd, page *root)
{
	// Case: nonempty root.
	if (root->num_keys > 0)
	{
		write_page(fd, root);
		return;
	}

	// Case: empty root. Promote the only child, or the tree becomes empty.
	int64_t new_root_pgn = NULL_PGN;
	if (!root->is_leaf)
	{
		new_root_pgn = root->child_pgns[0];
		set_parent_pgn(fd, new_root_pgn, NULL_PGN);
	}
	free_page(fd, root->pgn);

	// Reload: free_page() just changed the header on disk.
	header_page header;
	load_header_page(fd, &header);
	header.root_pgn = new_root_pgn;
	write_header_page(fd, &header);
}

/**
 * @brief Return the index of n's left neighbor in the parent, or -1 if n is the leftmost child.
 */
int get_neighbor_index(const page *parent, int64_t n_pgn)
{
	for (int i = 0; i <= parent->num_keys; i++) if (parent->child_pgns[i] == n_pgn) return i - 1;

	fprintf(stderr, "Search for nonexistent child page %" PRId64 " in parent page %" PRId64 ".\n", n_pgn, parent->pgn);
	exit(EXIT_FAILURE);
}

/**
 * @brief Merge the right page of (n, neighbor) into the left one, remove k_prime from
 * the parent, then free the emptied right page.
 */
void coalesce_pages(int fd, const header_page *header, page *n, page *neighbor, page *parent, int neighbor_index, int64_t k_prime)
{
	int i, j;

	// Swap so that n is always the right page and neighbor the left one.
	if (neighbor_index == -1)
	{
		page *tmp = n;
		n = neighbor;
		neighbor = tmp;
	}

	int neighvor_insertion_index = neighbor->num_keys;

	if (!n->is_leaf)
	{
		// Internal: append k_prime, then all of n's keys and children.
		neighbor->keys[neighvor_insertion_index] = k_prime;
		neighbor->num_keys++;

		int n_end = n->num_keys;
		for (i = neighvor_insertion_index + 1, j = 0; j < n_end; i++, j++)
		{
			neighbor->keys[i] = n->keys[j];
			neighbor->child_pgns[i] = n->child_pgns[j];
			neighbor->num_keys++;
			n->num_keys--;
		}
		neighbor->child_pgns[i] = n->child_pgns[j];

		// All children must now point up to the merged page.
		for (i = 0; i < neighbor->num_keys + 1; i++) set_parent_pgn(fd, neighbor->child_pgns[i], neighbor->pgn);
	}
	else
	{
		// Leaf: append n's records and take over its right sibling.
		for (i = neighvor_insertion_index, j = 0; j < n->num_keys; i++, j++)
		{
			neighbor->keys[i] = n->keys[j];
			neighbor->records[i] = n->records[j];
			neighbor->num_keys++;
		}
		neighbor->right_sibling_pgn = n->right_sibling_pgn;
	}

	write_page(fd, neighbor);

	int64_t n_pgn = n->pgn;
	delete_entry(fd, header, parent, k_prime, n_pgn);
	free_page(fd, n_pgn);
}

/**
 * @brief Move one entry from the neighbor into n, and update k_prime in the parent.
 */
void redistribute_pages(int fd, page *n, page *neighbor, page *parent, int neighbor_index, int k_prime_index, int64_t k_prime)
{
	int i;

	if (neighbor_index != -1)
	{
		// Case: n has a left neighbor. Move the neighbor's last entry to n's front.
		if (!n->is_leaf) n->child_pgns[n->num_keys + 1] = n->child_pgns[n->num_keys];
		for (i = n->num_keys; i > 0; i--)
		{
			n->keys[i] = n->keys[i - 1];
			if (n->is_leaf) n->records[i] = n->records[i - 1];
			else n->child_pgns[i] = n->child_pgns[i - 1];
		}

		if (!n->is_leaf)
		{
			n->child_pgns[0] = neighbor->child_pgns[neighbor->num_keys];
			set_parent_pgn(fd, n->child_pgns[0], n->pgn);
			n->keys[0] = k_prime;
			parent->keys[k_prime_index] = neighbor->keys[neighbor->num_keys - 1];
		}
		else
		{
			n->records[0] = neighbor->records[neighbor->num_keys - 1];
			n->keys[0] = neighbor->keys[neighbor->num_keys - 1];
			parent->keys[k_prime_index] = n->keys[0];
		}
	}
	else
	{
		// Case: n is the leftmost child. Move the right neighbor's first entry to n's end.
		if (n->is_leaf)
		{
			n->keys[n->num_keys] = neighbor->keys[0];
			n->records[n->num_keys] = neighbor->records[0];
			parent->keys[k_prime_index] = neighbor->keys[1];
		}
		else
		{
			n->keys[n->num_keys] = k_prime;
			n->child_pgns[n->num_keys + 1] = neighbor->child_pgns[0];
			set_parent_pgn(fd, n->child_pgns[n->num_keys  +1], n->pgn);
			parent->keys[k_prime_index] = neighbor->keys[0];
		}

		for (i = 0; i < neighbor->num_keys - 1; i++)
		{
			neighbor->keys[i] = neighbor->keys[i + 1];
			if (neighbor->is_leaf) neighbor->records[i] = neighbor->records[i + 1];
			else neighbor->child_pgns[i] = neighbor->child_pgns[i + 1];
		}
		if (!neighbor->is_leaf) neighbor->child_pgns[i] = neighbor->child_pgns[i + 1];
	}

	n->num_keys++;
	neighbor->num_keys--;

	write_page(fd, n);
	write_page(fd, neighbor);
	write_page(fd, parent);
}

// Destroy API
void db_destroy(int fd) {
	header_page header;
	load_header_page(fd, &header);
	destroy_pages(fd, header.root_pgn);

	// Reload: free_page() changed the free page list in the header on disk.
	load_header_page(fd, &header);
	header.root_pgn = NULL_PGN;
	write_header_page(fd, &header);
}

// Helper functions for destroy API
void destroy_pages(int fd, int64_t pgn) {
	if (pgn <= 0) return;
	page cur_page;
	load_page(fd, pgn, &cur_page);
	if (!cur_page.is_leaf) for (int i = 0; i < cur_page.num_keys + 1; i++) destroy_pages(fd, cur_page.child_pgns[i]);
	free_page(fd, pgn);
}

// Utility helper functions
/**
 * @brief Find the place to split a page that is too big into two.
 */
int cut(int length)
{
	if (length % 2 == 0) return length / 2;
	return length / 2 + 1;
}

/**
 * @brief Copy a value into a record, truncating it to fit (119 chars + NUL).
 * strncpy zero-fills the rest of the buffer, so no garbage bytes are written to disk.
 */
 void set_record(record *dest, const char *value)
 {
	strncpy(dest->value, value, sizeof(dest->value) - 1);
	dest->value[sizeof(dest->value) - 1] = '\0';
 }

 /**
  * @brief Load a page, set its parent page number, and write it back.
  */
 void set_parent_pgn(int fd, int64_t pgn, int64_t parent_pgn)
 {
	page p;
	load_page(fd, pgn, &p);
	p.parent_pgn = parent_pgn;
	write_page(fd, &p);
 }

 /**
  * @brief Print the keys of a page as "[k0 k1 ...]".
  */
 void print_page_keys(const page *p)
 {
	printf("[");
	for (int i = 0; i < p->num_keys; i++) printf("%s%" PRId64, (i == 0) ? "" : " ", p->keys[i]);
	printf("] ");
 }
