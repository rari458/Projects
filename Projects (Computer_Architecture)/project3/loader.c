#include "loader.h"

#include <string.h>
#include <stdlib.h>

int load_sections(FILE* in_file, state_info* state) {
	int i; unsigned int word;
	char line[MAX_LINE];

	// read out the size of .text section
	if (!fgets(line, MAX_LINE, in_file) 
			|| !(state->text_len = atoi(line))) {
		printf("Invalid section size for .text\n");
		return -1;
	}

	// read out the size of .data section
	if (!fgets(line, MAX_LINE, in_file) 
			|| !(state->data_len = atoi(line))) {
		printf("Invalid section size for .data\n");
		return -1;
	}

	// load words into .text section
	for (i = 0; i < state->text_len; i += 4) {
		if (!fgets(line, MAX_LINE, in_file) 
				|| !(sscanf(line, "%d", &word))) {
			printf("Unrecognized machine code in .text\n");
			return -1;
		}
		memcpy(&state->text[i], &word, sizeof(word));
	}

	// load words into .data section
	for (i = 0; i < state->data_len; i += 4) {
		if (!fgets(line, MAX_LINE, in_file) 
				|| !(sscanf(line, "%d", &word))) {
			printf("Unrecognized machine code in .data\n");
			return -1;
		}
		memcpy(&state->data[i], &word, sizeof(word));
	}
	return 0;
}
