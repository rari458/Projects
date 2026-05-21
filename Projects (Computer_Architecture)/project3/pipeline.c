#include "pipeline.h"

#include "simulator.h"
#include "alu.h"
#include "control.h"
#include "reg_file.h"
#include "mem.h"
#include "forward.h"

#include <string.h>

void fetch(const unsigned int pc, IFID_reg* IFID) {
	unsigned int inst = inst_fetch(pc);
	IFID->PC = pc + 4;
	IFID->Inst = inst_fetch(pc);
}

void decode(const IFID_reg* IFID, const int detected, IDEX_reg* IDEX) {
	unsigned int inst;
	field_info fields;
	control ctl;
	inst = IFID->Inst;
#ifdef HYU_ITE2031
	// Detect any pipeline hazard and stall
	if (detected) {
		memset(IDEX, 0, sizeof(IDEX_reg));
		IDEX->PC       = IFID->PC;
		IDEX->ALUOp    = DONT_CARE;
		IDEX->RegDest  = DONT_CARE;
		IDEX->MemtoReg = DONT_CARE;
		IDEX->ALUSrc   = DONT_CARE;
		PCWrite = 0;
		IFIDWrite = 0;
		return;
	}

	// Decode the given instruction
	setup_fields(inst, &fields);

	// Read registers and store them into pipeline registers
	reg_file_read(fields.rs, fields.rt, IDEX);

	// Store pipeline registers
	IDEX->PC 		 = IFID->PC;
	IDEX->Inst 		 = inst;
	IDEX->OPCode 	 = fields.opcode;
	IDEX->RegisterRs = fields.rs;
	IDEX->RegisterRt = fields.rt;
	IDEX->RegisterRd = fields.rd;
	IDEX->Imm 		 = fields.imm;

	// Determine control signals
	setup_control(inst, &ctl);
	
	// Store control into pipeline registers
	IDEX->ALUOp 	 = ctl.ALUOp;
	IDEX->RegDest 	 = ctl.RegDest;
	IDEX->MemRead 	 = ctl.MemRead;
	IDEX->MemtoReg   = ctl.MemtoReg;
	IDEX->MemWrite   = ctl.MemWrite;
	IDEX->ALUSrc 	 = ctl.ALUSrc;
	IDEX->RegWrite   = ctl.RegWrite;
#endif //HYU_ITE2031
} 

void execute(const IDEX_reg* IDEX, const int valA, const int valB, 
		EXMEM_reg* EXMEM) {
	int ALU_ctl, ALU_out;
#ifdef HYU_ITE2031
	int alu_in2;
	unsigned char dest_reg;

	alu_in2 = (IDEX->ALUSrc == ASSERT) ? IDEX->Imm : valB;
	ALU_ctl = setup_ALU_ctl(IDEX->ALUOp, IDEX->OPCode, IDEX->Imm & 0x3F);
	ALU_out = do_ALU(valA, alu_in2, ALU_ctl);

	if (get_inst_type(IDEX->Inst) == NOR) {
		ALU_out = ~((unsigned int)valA | (unsigned int)valB);
		dest_reg = IDEX->RegisterRd;
	} else if (get_inst_type(IDEX->Inst) == JAL) {
		ALU_out = IDEX->PC;
		dest_reg = 31;
	} else if (IDEX->RegDest == ASSERT) {
		dest_reg = IDEX->RegisterRd;
	} else {
		dest_reg = IDEX->RegisterRt;
	}

	// Store pipeline registers
	EXMEM->PC 	      = IDEX->PC;
	EXMEM->Inst       = IDEX->Inst;
	EXMEM->RegisterRt = IDEX->RegisterRt;
	EXMEM->RegisterRd = dest_reg;
	EXMEM->ALUResult  = (unsigned int)ALU_out;
	EXMEM->Data 	  = valB;
	// Store control into pipeline registers
	EXMEM->RegDest  = IDEX->RegDest;
	EXMEM->MemRead  = IDEX->MemRead;
	EXMEM->MemtoReg = IDEX->MemtoReg;
	EXMEM->MemWrite = IDEX->MemWrite;
	EXMEM->RegWrite = IDEX->RegWrite;
#endif //HYU_ITE2031
}

void memory(const EXMEM_reg* EXMEM, const int valB, MEMWB_reg* MEMWB) {
#ifdef HYU_ITE2031 
	// Data access
	MEMWB->Data = 0;
	if (EXMEM->MemRead == ASSERT)
		MEMWB->Data = data_load(EXMEM->ALUResult);
	if (EXMEM->MemWrite == ASSERT)
		data_store(EXMEM->ALUResult, valB);

	// Store pipeline registers
	MEMWB->PC 		  = EXMEM->PC;
	MEMWB->Inst 	  = EXMEM->Inst;
	MEMWB->RegisterRd = EXMEM->RegisterRd;
	MEMWB->ALUResult  = EXMEM->ALUResult;
	// Store control into pipeline registers
	MEMWB->RegDest  = EXMEM->RegDest;
	MEMWB->MemtoReg = EXMEM->MemtoReg;
	MEMWB->RegWrite = EXMEM->RegWrite;
#endif //HYU_ITE2031
}

void writeback(const MEMWB_reg* MEMWB, IDEX_reg* IDEX,
		retirement_info* retired) {
#ifdef HYU_ITE2031
	if (MEMWB->RegWrite == ASSERT) {
		unsigned int write_val = (MEMWB->MemtoReg == ASSERT)
			? MEMWB->Data : MEMWB->ALUResult;
		reg_file_write(MEMWB->RegisterRd, write_val, IDEX);
	}
#endif //HYU_ITE2031
	// fill the retirement information which is used in print_state()
	retired->PC = MEMWB->PC;
	retired->Inst = MEMWB->Inst;
}
