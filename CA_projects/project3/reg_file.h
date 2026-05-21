#ifndef __REG_FILE_H__
#define __REG_FILE_H__

#include "pipeline.h"

#define NUM_REGS 32 /* number of machine registers */

typedef struct {
	unsigned int regs[NUM_REGS];
	unsigned int write_register;
	unsigned int write_data;
} reg_file;

/* initialize reg files; GP registers */
void init_reg_file();

/* read two value of the given register numbers; rs and rt 
	 @param[in] rs: register rs
	 @param[in] rt: register rt
	 @param[out] IDEX: IDEX pipeline register */
void reg_file_read(unsigned int, unsigned int, IDEX_reg*);

/* update the value of the given register
	 @param[in] rd: destination register number
	 @param[in] data: value to be written to the register
	 @param[out] IDEX: used for internal forwarding */
void reg_file_write(unsigned int, unsigned int, IDEX_reg*);

/* print all state of register files */
void print_reg_file();
#endif // __REG_FILE_H__
