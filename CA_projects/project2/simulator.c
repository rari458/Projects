/* Project 2: ITE2031 MIPS Simulator */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "mem.h"
#include "loader.h"
#include "simulator.h"

int main(int argc, char *argv[]) {
	unsigned int inst, cycles;
	state_info state;
	field_info fields;
	FILE* in_file;

	if (argc != 2) {
		printf("error: usage: %s <machine-code file>\n", argv[0]);
		exit(1);
	}

	in_file = fopen(argv[1], "r");
	if (in_file == NULL) {
		printf("error: can't open file %s", argv[1]);
		perror("fopen");
		exit(1);
	}

	memset(state.regs, 0, sizeof(state.regs));

	/* Phase-1 map each section to memory
		 load text and data section into state.text and state.data, respectively */
	if (load_sections(in_file, &state))
		goto EXIT_ON_ERRORS;

	/* TODO: Phase-2 $gp, $sp, $fp initialization */
	state.regs[28] = 0x10008000; // $gp
	state.regs[29] = 0x7FFFFFFC; // $sp
	state.regs[30] = 0x7FFFFFFC; // $fp
	state.pc = TEXT_SECTION_START; // PC Initialization

	/* TODO: Phase-3 start simulator by calling main() */
	for (cycles = 0, inst = NOP_INST; get_op_type(inst) != SYSCALL; cycles++) {
		fetch(&state, &inst);
		decode(inst, &fields);
		execute(inst, &fields, &state);
		print_state(&state, cycles);
	}
	
EXIT_ON_ERRORS:
	if (in_file) {
		fclose(in_file);
	}

	return 0;
}

void fetch(state_info* state, unsigned int* inst) {
	// TODO: complete here
	*inst = inst_fetch(state, state->pc);
	state->pc += 4;
}

void decode(const unsigned int inst, field_info* fields) {
	// TODO: complete here
	fields->opcode = (inst >> 26) & 0x3F;
	fields->rs = (inst >> 21) & 0x1F;
	fields->rt = (inst >> 16) & 0x1F;
	fields->rd = (inst >> 11) & 0x1F;
	fields->shamt = (inst >> 6) &0x1F;
	fields->func = inst & 0x3F;
	fields->imm = ((int)((inst & 0xFFFF) << 16)) >> 16;
	fields->addr = inst & 0x3FFFFFF;
}

static inline unsigned int get_address(const field_info* fields, const state_info* state) {
	// TODO: complete here
	return state->regs[fields->rs] + fields->imm;
}

void execute(const unsigned int inst, const field_info* fields, state_info* state) {
	unsigned int word;
	switch (get_op_type(inst)) {
	// TODO: complete here
	case ADD:
		state->regs[fields->rd] = state->regs[fields->rs] + state->regs[fields->rt];
		break;
	case SLT:
		state->regs[fields->rd] = ((int)state->regs[fields->rs] < (int)state->regs[fields->rt]) ? 1 : 0;
		break;
	case NOR:
		state->regs[fields->rd] = ~(state->regs[fields->rs] | state->regs[fields->rt]);
		break;
	case JR:
		state->pc = state->regs[fields->rs];
		break;
	case ADDI:
		state->regs[fields->rt] = state->regs[fields->rs] + fields->imm;
		break;
	case LW:
		word = data_load(state, get_address(fields, state));
		state->regs[fields->rt] = word;
		break;
	case SW:
		data_store(state, get_address(fields, state), state->regs[fields->rt]);
		break;
	case BEQ:
		if (state->regs[fields->rs] == state->regs[fields->rt])
			state->pc += (fields->imm << 2);
		break;
	case J:
		state->pc = (state->pc & 0xF0000000) | (fields->addr << 2);
		break;
	case JAL:
		state->regs[31] = state->pc;
		state->pc = (state->pc & 0xF0000000) | (fields->addr << 2);
		break;
	case NOP:
		break;
	default:
		break;
	}
	state->regs[0] = 0; // $zero is always 0
}

void print_state(state_info* state, unsigned int cycles) {
	int i, j;
	printf("\n@@@\nstate at cycle %d\n", cycles);
	printf("  pc: 0x%08X\n", state->pc);
	printf("  .data:\n");
	for (i = 0; i < state->data_len; i += 4) {
		printf("    mem[0x%08X]: %8X\n", 
				DATA_SECTION_START + i, *((int*) &state->data[i]));
	}
	printf("  registers:\n");
	for (i = 0; i < NUM_REGS >> 2; i++) {
		printf("   ");
		for (j = 0; j < 4; j++) {
			printf(" regs[%02d]: %8X", (i << 2) + j, state->regs[(i << 2) + j]);
		}
		printf("\n");
	}
	printf("end state\n");
}

int get_op_type(const unsigned int inst) {
	unsigned int opcode, func;
	opcode = inst >> 26;
	func = inst & 0x3F;
	switch (opcode) {
		case 2:
			return J;
		case 3:
			return JAL;
		case 4: // I-type: beq
			return BEQ;
		case 8: // I-type: addi
			return ADDI;
		case 0x23:
			return LW;
		case 0x2B: // I-type: sw
			return SW;
		case 0:
			switch (func) {
				case 0:
					return NOP;
				case 8:
					return JR;
				case 0xC:
					return SYSCALL;
				case 0x20:
					return ADD;
				case 0x27:
					return NOR;
				case 0x2A:
					return SLT;
			}
		default:
			return UNDEFINED;
	}
}
