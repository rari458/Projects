/* Project 3: ITE2031 MIPS Pipelined Simulator */

#include "simulator.h"

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "alu.h"
#include "control.h"
#include "mem.h"
#include "reg_file.h"
#include "loader.h"
#include "pipeline.h"
#include "hazard.h"
#include "forward.h"

extern reg_file rfile;
extern unsigned char text[SEG_SIZE];
extern unsigned char data[SEG_SIZE];

// control to update PC
int PCWrite = 1;
// control to update IFID pipeline register
int IFIDWrite = 1;
// number of cycle elapsed since the start
unsigned int cycles = 0;
state_info states[2];

char INST_TYPE[OP_TYPE_MAX][8] = {"ADD", "SLT", "NOR", "JR", 
	"ADDI", "LW", "SW", "BEQ", "JAL", "J", "NOP", "LI", "SYSCALL"};

int main(int argc, char *argv[]) {
	char line[MAX_LINE];
	state_info *curr_state, *next_state;
	field_info fields;
	retirement_info retired = {0, NOP_INSTR};
	FILE *in_file;

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

	setup_curr_state(&curr_state);

	/* Phase-1 map each section to memory
		 load text and data section into state.text and state.data, respectively */
	if (load_sections(in_file, curr_state))
		goto EXIT_ON_ERRORS;

	/* Phase-2 register initialization */
	reg_file_write(28, 0x10008000, NULL);
	reg_file_write(29, 0x7FFFFFFC, NULL);
	reg_file_write(30, 0x7FFFFFFC, NULL);

	/* Phase-3 start simulator by calling main() */
	curr_state->pc = TEXT_SECTION_START;

	for (print_state(curr_state, &retired),
			setup_next_state(curr_state, &next_state); 
			get_inst_type(retired.Inst) != SYSCALL; 
			cycles++, update_state(curr_state, next_state),
			print_state(curr_state, &retired)) {
		// IF-stage
		fetch(curr_state->pc, &next_state->IFID);
		next_state->pc = curr_state->pc + 4;
		// ID-stage
		decode(&curr_state->IFID, detect_load_use_data_hazard(curr_state)
				|| detect_data_hazard_for_branch(curr_state)
				|| detect_syscall(curr_state), &next_state->IDEX);
		// EX-stage
		execute(&curr_state->IDEX, forwardEXA(curr_state), 
				forwardEXB(curr_state), &next_state->EXMEM);
		// MEM-stage
		memory(&curr_state->EXMEM, forwardMEM(curr_state), 
				&next_state->MEMWB);
		// WB-stage
		writeback(&curr_state->MEMWB, &next_state->IDEX, &retired);
	}
	
EXIT_ON_ERRORS:
	if (in_file) {
		fclose(in_file);
	}

	return 0;
}

void setup_curr_state(state_info** state) {
	int i;
	memset(states, 0, sizeof(state_info) * 2);
	for (i = 0; i < 2; i++) {
		states[i].text = text;
		states[i].data = data;
		states[i].regs = &rfile;
	}
	*state = &states[0];
}

void setup_next_state(state_info* curr, state_info** next) {
	states[1].text_len = curr->text_len;
	states[1].data_len = curr->data_len;
	*next = &states[1];
}

void update_state(state_info* curr, state_info* next) {
	unsigned int inst;
	control ctl;
	field_info fields;
#ifdef HYU_ITE2031
	if (PCWrite) {
		int inst_type = get_inst_type(next->IDEX.Inst);

		if (inst_type == BEQ) {
			if (forwardIDA(next, next->IDEX.valA) == forwardIDB(next, next->IDEX.valB)) {
				curr->pc = next->IDEX.PC + (next->IDEX.Imm << 2);
				memset(&next->IFID, 0, sizeof(IFID_reg));
			} else {
				curr->pc = next->pc;
			}
		} else if (inst_type == J || inst_type == JAL) {
			unsigned int addr = next->IDEX.Inst & 0x3FFFFFF;
			curr->pc = (next->IDEX.PC & 0xF0000000) | (addr << 2);
			memset(&next->IFID, 0, sizeof(IFID_reg));
		} else if (inst_type == JR) {
			curr->pc = (unsigned int) forwardIDA(next, next->IDEX.valA);
			memset(&next->IFID, 0, sizeof(IFID_reg));
		} else {
			// PC updated by next->pc, that is, PC + 4
			curr->pc = next->pc;
		}
	}

	// Pipeline register update
	if (IFIDWrite) {
		curr->IFID = next->IFID;
	} 
	curr->IDEX = next->IDEX;
	curr->EXMEM = next->EXMEM;
	curr->MEMWB = next->MEMWB;
#endif //HYU_ITE2031

	// Enable register write
	PCWrite = 1;
	IFIDWrite = 1;
}

void print_state(state_info* state, retirement_info* retired) {
	int i, j;
	printf("\n@@@\nstate at cycle %d\n", cycles);
	printf("  pc: 0x%08x\n", state->pc);
	printf("  .data:\n");
	for (i = 0; i < state->data_len; i += 4) {
		printf("    mem[0x%08x]: %8x\n", 
				DATA_SECTION_START + i, *((int*) &state->data[i]));
	}
	print_reg_file();
	printf("  pipeline registers:\n");
	printf("             IF               ID      "
			"         EX               MEM              WB(Retire)\n");
	printf("    pc:      0x%08x   |   0x%08x   |   0x%08x   |   0x%08x   |   0x%08x\n", 
			state->IFID.PC, state->IDEX.PC, state->EXMEM.PC, state->MEMWB.PC, retired->PC);
	printf("    inst:    0x%08x   |   0x%08x   |   0x%08x   |   0x%08x   |   0x%08x\n",
			state->IFID.Inst, state->IDEX.Inst, 
				state->EXMEM.Inst, state->MEMWB.Inst, retired->Inst);
	printf("             %-10s   |   %-10s   |   %-10s   |   %-10s   |   %-10s\n",
			INST_TYPE[get_inst_type(state->IFID.Inst)], 
			INST_TYPE[get_inst_type(state->IDEX.Inst)], 
			INST_TYPE[get_inst_type(state->EXMEM.Inst)], 
			INST_TYPE[get_inst_type(state->MEMWB.Inst)],
			INST_TYPE[get_inst_type(retired->Inst)]);
	printf("    ctl:     ALUOp(2) RegDst Jump Brch MemRd Mem2Reg"
			" MemWt ALUSrc RegWt\n");
	printf("             OPRJBMMMAR   |   OPRJBMMMAR   "
			"|   OPRJBMMMAR   |   OPRJBMMMAR\n");
	printf("             ");
	print_IFID_control(state->IFID);
	printf("   |   ");
	print_IDEX_control(state->IDEX);
	printf("   |   ");
	print_EXMEM_control(state->EXMEM);
	printf("   |   ");
	print_MEMWB_control(state->MEMWB);
	printf("\n");
	printf("end state\n");
}

void setup_fields(unsigned int inst, field_info* fields) {
	fields->opcode = inst >> 26;
	fields->rs = (inst >> 21) & 0x1F;
	fields->rt = (inst >> 16) & 0x1F;
	fields->rd = (inst >> 11) & 0x1F;
	fields->shamt = (inst >> 6) & 0x1F;
	fields->func = inst & 0x3F;
	fields->imm = sign_extend(inst & 0xFFFF);
	fields->addr = inst & 0x3FFFFFF;
}

int get_inst_type(unsigned int inst) {
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

int detect_syscall(const state_info* state) {
	return get_inst_type(state->IDEX.Inst) == SYSCALL
		|| get_inst_type(state->EXMEM.Inst) == SYSCALL
		|| get_inst_type(state->MEMWB.Inst) == SYSCALL;
}
