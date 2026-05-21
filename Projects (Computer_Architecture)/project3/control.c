#include "alu.h"
#include "control.h"
#include "simulator.h"

#include <stdio.h>

void setup_control(unsigned int inst, control* ctl) {
#ifdef HYU_ITE2031
	switch (get_inst_type(inst)) {
	// TODO: complete here
		case ADD: case SLT: case NOR:
			ctl->RegDest  = ASSERT;
			ctl->Jump     = DEASSERT;
			ctl->Branch   = DEASSERT;
			ctl->MemRead  = DEASSERT;
			ctl->MemtoReg = DEASSERT;
			ctl->ALUOp 	  = ARITHMETIC_LOGIC;
			ctl->MemWrite = DEASSERT;
			ctl->ALUSrc   = DEASSERT;
			ctl->RegWrite = ASSERT;
			break;
		case JR:
			ctl->RegDest  = DONT_CARE;
			ctl->Jump 	  = ASSERT;
			ctl->Branch   = DEASSERT;
			ctl->MemRead  = DEASSERT;
			ctl->MemtoReg = DONT_CARE;
			ctl->ALUOp    = ARITHMETIC_LOGIC;
			ctl->MemWrite = DEASSERT;
			ctl->ALUSrc   = DEASSERT;
			ctl->RegWrite = DEASSERT;
			break;
		case ADDI:
			ctl->RegDest  = DEASSERT;
			ctl->Jump 	  = DEASSERT;
			ctl->Branch   = DEASSERT;
			ctl->MemRead  = DEASSERT;
			ctl->MemtoReg = DEASSERT;
			ctl->ALUOp 	  = ARITHMETIC_LOGIC;
			ctl->MemWrite = DEASSERT;
			ctl->ALUSrc   = ASSERT;
			ctl->RegWrite = ASSERT;
			break;
		case LW:
			ctl->RegDest  = DEASSERT;
			ctl->Jump 	  = DEASSERT;
			ctl->Branch   = DEASSERT;
			ctl->MemRead  = ASSERT;
			ctl->MemtoReg = ASSERT;
			ctl->ALUOp 	  = LWSW;
			ctl->MemWrite = DEASSERT;
			ctl->ALUSrc   = ASSERT;
			ctl->RegWrite = ASSERT;
			break;
		case SW:
			ctl->RegDest  = DONT_CARE;
			ctl->Jump 	  = DEASSERT;
			ctl->Branch   = DEASSERT;
			ctl->MemRead  = DEASSERT;
			ctl->MemtoReg = DONT_CARE;
			ctl->ALUOp    = LWSW;
			ctl->MemWrite = ASSERT;
			ctl->ALUSrc   = ASSERT;
			ctl->RegWrite = DEASSERT;
			break;
		case BEQ:
			ctl->RegDest  = DONT_CARE;
			ctl->Jump 	  = DEASSERT;
			ctl->Branch   = ASSERT;
			ctl->MemRead  = DEASSERT;
			ctl->MemtoReg = DONT_CARE;
			ctl->ALUOp    = BRANCH;
			ctl->MemWrite = DEASSERT;
			ctl->ALUSrc   = DEASSERT;
			ctl->RegWrite = DEASSERT;
			break;
		case J:
			ctl->RegDest  = DONT_CARE;
			ctl->Jump 	  = ASSERT;
			ctl->Branch   = DEASSERT;
			ctl->MemRead  = DEASSERT;
			ctl->MemtoReg = DONT_CARE;
			ctl->ALUOp 	  = LWSW;
			ctl->MemWrite = DEASSERT;
			ctl->ALUSrc   = DEASSERT;
			ctl->RegWrite = DEASSERT;
			break;
		case JAL:
			ctl->RegDest  = ASSERT;
			ctl->Jump 	  = ASSERT;
			ctl->Branch   = DEASSERT;
			ctl->MemRead  = DEASSERT;
			ctl->MemtoReg = DEASSERT;
			ctl->ALUOp    = LWSW;
			ctl->MemWrite = DEASSERT;
			ctl->ALUSrc   = DEASSERT;
			ctl->RegWrite = ASSERT;
			break;
		default: // NOP, SYSCALL, UNDEFINED
			ctl->RegDest  = DONT_CARE;
			ctl->Jump     = DEASSERT;
			ctl->Branch   = DEASSERT;
			ctl->MemRead  = DEASSERT;
			ctl->MemtoReg = DONT_CARE;
			ctl->ALUOp    = DONT_CARE;
			ctl->MemWrite = DEASSERT;
			ctl->ALUSrc   = DONT_CARE;
			ctl->RegWrite = DEASSERT;
			break;
	}
#endif //HYU_ITE2031
}

void print_IFID_control(IFID_reg reg) {
	printf("----------");
}

void print_IDEX_control(IDEX_reg reg) {
	printf("%s%c--%c%c%c%c%c", reg.ALUOp == 0 ? "00" : reg.ALUOp == 1 ? 
			"01" : reg.ALUOp == 2 ? "10" : "XX",
			reg.RegDest == DONT_CARE ? 'X' : reg.RegDest == ASSERT ? '1' : '0',
			reg.MemRead == DONT_CARE ? 'X' : reg.MemRead == ASSERT ? '1' : '0',
			reg.MemtoReg == DONT_CARE ? 'X' : reg.RegDest == ASSERT ? '1' : '0',
			reg.MemWrite == DONT_CARE ? 'X' : reg.MemWrite == ASSERT ? '1' : '0',
			reg.ALUSrc == DONT_CARE ? 'X' : reg.ALUSrc == ASSERT ? '1' : '0',
			reg.RegWrite == DONT_CARE ? 'X' : reg.RegWrite == ASSERT ? '1' : '0');
}

void print_EXMEM_control(EXMEM_reg reg) {
	printf("--%c--%c%c%c-%c", 
			reg.RegDest == DONT_CARE ? 'X' : reg.RegDest == ASSERT ? '1' : '0',
			reg.MemRead == DONT_CARE ? 'X' : reg.MemRead == ASSERT ? '1' : '0',
			reg.MemtoReg == DONT_CARE ? 'X' : reg.RegDest == ASSERT ? '1' : '0',
			reg.MemWrite == DONT_CARE ? 'X' : reg.MemWrite == ASSERT ? '1' : '0',
			reg.RegWrite == DONT_CARE ? 'X' : reg.RegWrite == ASSERT ? '1' : '0');
}

void print_MEMWB_control(MEMWB_reg reg) {
	printf("--%c---%c--%c", 
			reg.RegDest == DONT_CARE ? 'X' : reg.RegDest == ASSERT ? '1' : '0',
			reg.MemtoReg == DONT_CARE ? 'X' : reg.RegDest == ASSERT ? '1' : '0',
			reg.RegWrite == DONT_CARE ? 'X' : reg.RegWrite == ASSERT ? '1' : '0');
}
