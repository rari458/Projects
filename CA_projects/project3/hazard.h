#ifndef __HAZARD_H__
#define __HAZARD_H__

#include "simulator.h"

/* detect load-use data hazard in the given pipeline registers
	 @param[in] state: state information containing pipeline registers
	 @return 1 if a data hazard is detected; otherwise, 0 */
int detect_load_use_data_hazard(const state_info*);

/* detect data hazard for a branch instruction in the given pipeline registers
	 @param[in] state: state information containing pipeline registers
	 @return 1 if a data hazard is detected; otherwise, 0 */
int detect_data_hazard_for_branch(const state_info*);
#endif // __HAZARD_H__
