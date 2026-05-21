#ifndef __MEM_H__
#define __MEM_H__

#include "simulator.h"

#define SEG_SIZE 65536		/* maximum number of "bytes" in memory */

unsigned int inst_fetch(unsigned int);

unsigned int data_load(unsigned int);

void data_store(unsigned int, unsigned int);

#endif // __MEM_H__
