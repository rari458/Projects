#ifndef __SIMULATOR_H__
#define  __SIMULATOR_H__

#include "pipeline.h"
#include "reg_file.h"

#define NOP_INSTR	0U
#define TEXT_SECTION_START 0x00400000
#define DATA_SECTION_START 0x10000000
#define sign_extend(num) (((int) num) << 16 >> 16)
#define is_R_type(inst) (!((inst) >> 26))

typedef enum {
	UNDEFINED = -1, ADD, SLT, NOR, JR, ADDI, LW, SW, BEQ, JAL, J, NOP, LI, SYSCALL, OP_TYPE_MAX
} OP_TYPE;

typedef struct {
	unsigned char opcode;
	unsigned char rs;
	unsigned char rt;
	unsigned char rd;
	unsigned char shamt;
	unsigned char func;
	int imm;
	unsigned int addr;
} field_info;

typedef struct {
	unsigned int pc;
	reg_file* regs;
	unsigned int text_len;
	unsigned int data_len;
	unsigned char* text;
	unsigned char* data;
	/* pipeline registers */
	IFID_reg IFID;
	IDEX_reg IDEX;
	EXMEM_reg EXMEM;
	MEMWB_reg MEMWB;
} state_info;

extern int PCWrite;
extern int IFIDWrite;

// sub-routines for the simulator
void setup_curr_state(state_info**);
void setup_next_state(state_info*, state_info**);
void update_state(state_info*, state_info*);
void print_state(state_info*, retirement_info*);

// helper functions
void setup_fields(unsigned int, field_info*);
int get_inst_type(unsigned int);
int detect_syscall(const state_info*);

#endif //__SIMULATOR_H__
