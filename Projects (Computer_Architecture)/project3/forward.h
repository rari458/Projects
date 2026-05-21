#ifndef __FORWARD_H__
#define __FORWARD_H__

#include "simulator.h"

/* forward ID stage for branch instrunctions
	 Note that the forwarding operation takes place 
	 during the second half of the clock cycle.
	 @param[in] state: state information including pipeline registers
	 @return corrected value for the instruction in ID stage
	 */
int forwardIDA(const state_info*, int);
int forwardIDB(const state_info*, int);


/* forward EX stage for non-branch instrunctions
	 Note that the forwarding operation occurs 
	 in the early phase of the clock cycle.
	 @param[in] state: state information including pipeline registers
	 @return corrected value for the instruction in EX stage
	 */
int forwardEXA(const state_info*);
int forwardEXB(const state_info*);

/* forward MEM stage for SW instrunctions
	 Note that the forwarding operation occurs 
	 in the early phase of the clock cycle.
	 @param[in] state: state information including pipeline registers
	 @return corrected value for the instruction in MEM stage
	 */
int forwardMEM(const state_info*);
#endif // __FORWARD_H__
