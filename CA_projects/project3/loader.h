#ifndef __LOADER_H__
#define __LOADER_H__

#include <stdio.h>

#include "simulator.h"

#define MAX_LINE 80

int load_sections(FILE*, state_info*);

#endif // __LOADER_H__
