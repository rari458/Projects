#include "alu.h"

int setup_ALU_ctl(int ALU_op, unsigned char opcode, unsigned char func) {
	switch (ALU_op) {
		case LWSW:
			// LWSW instructions, set as ADD
			return ALU_ADD;
		case BRANCH:
			// BEQ instructions, set as SUB
			return ALU_SUB;
		case ARITHMETIC_LOGIC:
			if (opcode == 0x00) {
				// R-type instructions
				switch (func) {
					case 0x20:
						return ALU_ADD;
					case 0x22:
						return ALU_SUB;
					case 0x24:
						return ALU_AND;
					case 0x25:
						return ALU_OR;
					case 0x2A:
						return ALU_SLT;
				}
			} else {
				// I-type arithmetic/logical instructions
				switch (opcode) {
					case 0x08: // ADDI
						return ALU_ADD;
				}
			}
	}
	return ALU_UNDEF;
}

int do_ALU(unsigned int val1, unsigned int val2, int ALU_ctl) {
	// TODO: complete here
	switch (ALU_ctl) {
		case ALU_ADD:
			return val1 + val2;
		case ALU_SUB:
			return val1 - val2;
		case ALU_AND:
			return val1 & val2;
		case ALU_OR:
			return val1 | val2;
		case ALU_SLT:
			return (int) val1 < (int) val2;
	}
}
