#ifndef __ALU_H__
#define __ALU_H__

typedef enum { LWSW, BRANCH, ARITHMETIC_LOGIC } ALU_OP;

typedef enum { ALU_UNDEF, ALU_ADD, ALU_SUB, ALU_AND, ALU_OR, ALU_SLT } ALU_FUNC;

/* set up ALU control 
	 @param[in] ALU_op: ALUOp control signal
	 @param[in] opcode: opcode control signal
	 @param[in] func: function field, i.e., imm[5:0]
	 @return value of ALU control for do_ALU */
int setup_ALU_ctl(int ALU_op, unsigned char opcode, unsigned char func);

/* do ALU with the given control
	 @param[in] val1: first input value
	 @param[in] val2: second input value
	 @param[in] ALU_ctl: ALU mode
	 @return result of ALU execution */
int do_ALU(unsigned int val1, unsigned int val2, int ALU_ctl);

#endif // __ALU_H__
