#ifndef __MEM_H__
#define __MEM_H__

#include "simulator.h"

unsigned int inst_fetch(state_info*, unsigned int);

unsigned int data_load(state_info*, unsigned int);

void data_store(state_info*, unsigned int, unsigned int);

#endif // __MEM_H__
