#ifndef __CONTROL_H__
#define __CONTROL_H__

#define DEASSERT	0
#define ASSERT		1
#define DONT_CARE	3

#include "pipeline.h"

typedef struct {
	unsigned RegDest: 2;
	unsigned Jump: 2;
	unsigned Branch: 2;
	unsigned MemRead: 2;
	unsigned MemtoReg: 2;
	unsigned ALUOp: 2;
	unsigned MemWrite: 2;
	unsigned ALUSrc: 2;
	unsigned RegWrite: 2;
} control;

/* setup the control information for the given instruction
	 @param[in] inst: a given instruction
	 @param[out] ctl: the control information
	 */
void setup_control(unsigned int, control*);

/* print the control information stored in IFID pipeline register 
	 @param[in] IFID: a given IFID pipeline register
	 */
void print_IFID_control(IFID_reg);

/* print the control information stored in IDEX pipeline register 
	 @param[in] IDEX: a given IDEX pipeline register
	 */
void print_IDEX_control(IDEX_reg);

/* print the control information stored in EXMEM pipeline register 
	 @param[in] EXMEM: a given EXMEM pipeline register
	 */
void print_EXMEM_control(EXMEM_reg);

/* print the control information stored in MEMWB pipeline register 
	 @param[in] MEMWB: a given MEMWB pipeline register
	 */
void print_MEMWB_control(MEMWB_reg);

#endif // __CONTROL_H__
