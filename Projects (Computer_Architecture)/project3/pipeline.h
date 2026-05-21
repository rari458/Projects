#ifndef __PIPELINE_H__
#define __PIPELINE_H__

typedef struct {
	unsigned int PC;
	unsigned int Inst;
} IFID_reg;

typedef struct {
	unsigned int PC;
	unsigned int Inst;
	// decoding results
	unsigned char OPCode; 
	unsigned char RegisterRs;
	unsigned char RegisterRt;
	unsigned char RegisterRd;
	int Imm;
	// register reads from two operands
	unsigned int valA;
	unsigned int valB;
	// control signal 
	unsigned ALUOp: 2;
	unsigned RegDest: 2;
	unsigned MemRead: 2;
	unsigned MemtoReg: 2;
	unsigned MemWrite: 2;
	unsigned ALUSrc: 2;
	unsigned RegWrite: 2;
} IDEX_reg;

typedef struct {
	unsigned int PC;
	unsigned int Inst;
	// decoding results
	unsigned char RegisterRt;
	unsigned char RegisterRd;
	// output from ALU 
	unsigned int ALUResult;
	unsigned int Data;
	// control signal
	unsigned RegDest: 2;
	unsigned MemRead: 2;
	unsigned MemtoReg: 2;
	unsigned MemWrite: 2;
	unsigned RegWrite: 2;
} EXMEM_reg;

typedef struct {
	unsigned int PC;
	unsigned int Inst;
	// decoding results
	// unsigned char OPCode;
	unsigned char RegisterRd;
	// output from ALU 
	unsigned int ALUResult;
	unsigned int Data;
	// control signal
	unsigned RegDest: 2;
	unsigned MemtoReg: 2;
	unsigned RegWrite: 2;
} MEMWB_reg;

typedef struct {
	unsigned int PC;
	unsigned int Inst;
} retirement_info;

/* Execute the instruction fetch (IF) stage of the MIPS pipeline
	 @param[in] pc: the current PC value
	 @param[out] IFID: IFID pipeline register */
void fetch(const unsigned int, IFID_reg*);

/* Execute the instruction decode (ID) stage of the MIPS pipeline
	 @param[in] IFID: IFID pipeline register
	 @param[in] detected: detected data-hazard will result in pipeline stall
	 @param[out] IDEX: IDEX pipeline register */
void decode(const IFID_reg*, const int, IDEX_reg*);

/* Execute the instruction execution (EX) stage of the MIPS pipeline
	 @param[in] IDEX: IDEX pipeline register
	 @param[in] valA: either the value from register rs or its forwarded value
	 @param[in] valB: either the value from register rt or its forwarded value
	 @param[out] EXMEM: EXMEM pipeline register */
void execute(const IDEX_reg*, const int, const int, EXMEM_reg*);

/* Execute the instruction memory access (MEM) stage of the MIPS pipeline
	 @param[in] EXMEM: EXMEM pipeline register
	 @param[out] MEMWB: MEMWB pipeline register */
void memory(const EXMEM_reg*, const int, MEMWB_reg*);

/* Execute the instruction write-back (WB) stage of the MIPS pipeline
	 @param[in] MEMWB: MEMWB pipeline register 
	 @param[out] IDEX: IDEX pipeline register (used for internal forwarding)
	 @param[out] retired: retired instruction information */
void writeback(const MEMWB_reg*, IDEX_reg*, retirement_info*);

#endif // __PIPELINE_H__

