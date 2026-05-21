#include <stdio.h>
#include <stdlib.h>

#include "mem.h"

unsigned char text[SEG_SIZE];
unsigned char data[SEG_SIZE];

unsigned int inst_fetch(unsigned int addr) {
	unsigned int inst;
	if (addr < TEXT_SECTION_START || DATA_SECTION_START <= addr) {
		printf("Segmentation faults: %x\n", addr);
		exit(1);
	}
	inst = *((unsigned int*) &(text[addr - TEXT_SECTION_START]));
	return inst;
}

unsigned int data_load(unsigned int addr) {
	unsigned int word;
	if (addr < DATA_SECTION_START || (DATA_SECTION_START | 0xFFFFU) < addr) {
		printf("Segmentation faults: %x\n", addr);
		exit(1);
	}
	word = *((unsigned int*) &(data[addr - DATA_SECTION_START]));
	return word;
}

void data_store(unsigned int addr, unsigned int word) {
	if (addr < DATA_SECTION_START || (DATA_SECTION_START | 0xFFFFU) < addr) {
		printf("Segmentation faults: %x\n", addr);
		exit(1);
	}
	data[addr - DATA_SECTION_START] = word & 0xFF;
	data[addr - DATA_SECTION_START + 1] = (word >> 8) & 0xFF;
	data[addr - DATA_SECTION_START + 2] = (word >> 16) & 0xFF;
	data[addr - DATA_SECTION_START + 3] = (word >> 24) & 0xFF;
}
