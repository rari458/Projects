#include "reg_file.h"

#include <stdio.h>
#include <string.h>

reg_file rfile;

void init_reg_file() {
	memset(&rfile, 0, sizeof(reg_file));
}

void reg_file_read(unsigned int rs, unsigned int rt, IDEX_reg* IDEX) {
	IDEX->valA = rfile.regs[rs];
	IDEX->valB = rfile.regs[rt];
}

void reg_file_write(unsigned int rd, unsigned int data, IDEX_reg* IDEX) {
	rfile.regs[rd] = data;
	// internal forwarding
	if (IDEX && IDEX->RegisterRs == rd) {
		IDEX->valA = data;
	} if (IDEX && IDEX->RegisterRt == rd) {
		IDEX->valB = data;
	}
}

void print_reg_file() {
	int i, j;
	// Do not modify the line below
	printf("  registers:\n");
	for (i = 0; i < NUM_REGS >> 2; i++) {
		printf("   ");
		for (j = 0; j < 4; j++) {
			printf(" regs[%02d]: %8x", (i << 2) + j, rfile.regs[(i << 2) + j]);
		}
		printf("\n");
	}
}
