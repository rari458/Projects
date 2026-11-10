/*
 *  bpt.c
 */
#define Version "1.16.1"
/*
 *
 *  bpt:  B+ Tree Implementation
 *
 *  Copyright (c) 2018  Amittai Aviram  http://www.amittai.com
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions are met:
 *
 *  1. Redistributions of source code must retain the above copyright notice,
 *  this list of conditions and the following disclaimer.
 *
 *  2. Redistributions in binary form must reproduce the above copyright notice,
 *  this list of conditions and the following disclaimer in the documentation
 *  and/or other materials provided with the distribution.

 *  3. The name of the copyright holder may not be used to endorse
 *  or promote products derived from this software without specific
 *  prior written permission.

 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER "AS IS"
 *  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 *  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 *  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE
 *  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 *  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 *  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 *  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 *  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 *  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 *  POSSIBILITY OF SUCH DAMAGE.

 *  Author:  Amittai Aviram
 *    http://www.amittai.com
 *    amittai.aviram@gmail.com or afa13@columbia.edu
 *  Original Date:  26 June 2010
 *  Last modified: 02 September 2018
 *
 *  This implementation demonstrates the B+ tree data structure
 *  for educational purposes, includin insertion, deletion, search, and display
 *  of the search path, the leaves, or the whole tree.
 *
 *  Must be compiled with a C99-compliant C compiler such as the latest GCC.
 *
 *  Usage:  bpt <filepath> [<input_filepath>]
 *  Filepath argument is mandatory to specify the file to store the B+ tree,
 *  input_filepath is optional to specify the file to read initial input from.
 *
 */
#include "file_manager.h"

// Find API
record *db_find(int fd, int64_t key, bool verbose, page **leaf_out);

// Helper functions for find API
void find_leaf(int fd, int64_t root_pgn, int64_t key, bool verbose, page *dest);
int find_key_index(const page *p, int64_t key);

// Insertion API
void db_insert(int fd, int64_t key, char *value);

// Helper functions for insertion API
void start_new_tree(int fd, header_page *header, int64_t key, const char *value);
void insert_into_leaf(page *leaf, int64_t key, const char *value);
void insert_into_leaf_after_splitting(int fd, header_page *header, page *leaf, int64_t key, const char *value);
void insert_into_parent(int fd, header_page *header, page *left, int64_t key, page *right);
void insert_into_new_root(int fd, header_page *header, page *left, int64_t key, page *right);
void insert_into_page(page *p, int left_index, int64_t key, int64_t right_pgn);
void insert_into_page_after_splitting(int fd, header_page *header, page *old_page, int left_index, int64_t key, int64_t right_pgn);
int get_left_index(const page *parent, int64_t left_pgn);

// Deletion API
void db_delete(int fd, int64_t key);

// Helper functions for delete API
void delete_entry(int fd, const header_page *header, page *n, int64_t key, int64_t child_pgn);
void remove_entry_from_leaf_page(page *leaf, int64_t key);
void remove_entry_from_internal_page(page *p, int64_t key, int64_t child_pgn);
void adjust_root(int fd, page *root);
int get_neighbor_index(const page *parent, int64_t n_pgn);
void coalesce_pages(int fd, const header_page *header, page *n, page *neighbor, page *parent, int neighbor_index, int64_t k_prime);
void redistribute_pages(int fd, page *n, page *neighbor, page *parent, int neighbor_index, int k_prime_index, int64_t k_prime);

// Destroy API
void db_destroy(int fd);

// Helper functions for destroy API
void destroy_pages(int fd, int64_t pgn);

// Common utility helper functions
int cut(int length);
void set_record(record *dest, const char *value);
void set_parent_pgn(int fd, int64_t pgn, int64_t parent_pgn);
void print_page_keys(const page *p);