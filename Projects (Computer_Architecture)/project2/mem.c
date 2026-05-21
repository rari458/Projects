#include <stdio.h>
#include <stdlib.h>

#include "mem.h"

unsigned int inst_fetch(state_info* state, unsigned int addr) {
	unsigned int inst;
	if (addr < TEXT_SECTION_START || DATA_SECTION_START <= addr) {
		printf("Segmentation faults: %x\n", addr);
		exit(1);
	}
	inst = *((unsigned int*) &(state->text[addr - TEXT_SECTION_START]));
	return inst;
}

unsigned int data_load(state_info* state, unsigned int addr) {
	unsigned int word;
	if (addr < DATA_SECTION_START || (DATA_SECTION_START | 0xFFFFU) < addr) {
		printf("Segmentation faults: %x\n", addr);
		exit(1);
	}
	word = state->data[addr - DATA_SECTION_START];
	return word;
}

void data_store(state_info* state, unsigned int addr, unsigned int word) {
	if (addr < DATA_SECTION_START || (DATA_SECTION_START | 0xFFFFU) < addr) {
		printf("Segmentation faults: %x\n", addr);
		exit(1);
	}
	state->data[addr - DATA_SECTION_START] = word;
}
