#include "forward.h"
#include "control.h"

int forwardIDA(const state_info* state, int valA) {
#ifdef HYU_ITE2031
	unsigned char rs = state->IDEX.RegisterRs;

	// EX/MEM -> ID forwarding
	if (state->EXMEM.RegWrite == ASSERT &&
		state->EXMEM.RegisterRd != 0 &&
		state->EXMEM.RegisterRd == rs)
		return state->EXMEM.ALUResult;

	// MEM/WB -> ID forwarding
	if (state->MEMWB.RegWrite == ASSERT &&
		state->MEMWB.RegisterRd != 0 &&
		state->MEMWB.RegisterRd == rs)
		return (state->MEMWB.MemtoReg == ASSERT) ? state->MEMWB.Data : state->MEMWB.ALUResult;

	// No forwarding
	return valA;
#endif //HYU_ITE2031
}

int forwardIDB(const state_info* state, int valB) {
#ifdef HYU_ITE2031
	unsigned char rt = state->IDEX.RegisterRt;

	// EX/MEM -> ID forwarding
	if (state->EXMEM.RegWrite == ASSERT &&
		state->EXMEM.RegisterRd != 0 &&
		state->EXMEM.RegisterRd == rt)
		return state->EXMEM.ALUResult;

	// MEM/WB -> ID forwarding
	if (state->MEMWB.RegWrite == ASSERT &&
		state->MEMWB.RegisterRd != 0 &&
		state->MEMWB.RegisterRd == rt)
		return (state->MEMWB.MemtoReg == ASSERT) ? state->MEMWB.Data : state->MEMWB.ALUResult;

	// No forwarding
	return valB;
#endif // HYU_ITE2031
}

int forwardEXA(const state_info* state) {
#ifdef HYU_ITE2031
	unsigned char rs = state->IDEX.RegisterRs;

	// EX/MEM -> EX forwarding
	if (state->EXMEM.RegWrite == ASSERT &&
		state->EXMEM.RegisterRd != 0 &&
		state->EXMEM.RegisterRd == rs)
		return state->EXMEM.ALUResult;

	// MEM/WB -> EX forwarding
	if (state->MEMWB.RegWrite == ASSERT &&
		state->MEMWB.RegisterRd !=0 &&
		state->MEMWB.RegisterRd == rs)
		return (state->MEMWB.MemtoReg == ASSERT) ? state->MEMWB.Data : state->MEMWB.ALUResult;

	// No forwarding
	return state->IDEX.valA;
#endif // HYU_ITE2031
}

int forwardEXB(const state_info* state) {
#ifdef HYU_ITE2031
	unsigned char rt = state->IDEX.RegisterRt;

	if (state->EXMEM.RegWrite == ASSERT &&
		state->EXMEM.RegisterRd != 0 &&
		state->EXMEM.RegisterRd == rt)
		return state->EXMEM.ALUResult;

	if (state->MEMWB.RegWrite == ASSERT &&
		state->MEMWB.RegisterRd != 0 &&
		state->MEMWB.RegisterRd == rt)
		return (state->MEMWB.MemtoReg == ASSERT) ? state->MEMWB.Data : state->MEMWB.ALUResult;

	// No forwarding
	return state->IDEX.valB;
#endif // HYU_ITE2031
}

int forwardMEM(const state_info* state) {
#ifdef HYU_ITE2031
	if (state->MEMWB.RegWrite == ASSERT &&
		state->MEMWB.RegisterRd != 0 &&
		state->MEMWB.RegisterRd == state->EXMEM.RegisterRt)
		return (state->MEMWB.MemtoReg == ASSERT) ? state->MEMWB.Data : state->MEMWB.ALUResult;

	// No forwarding
	return state->EXMEM.Data;
#endif //HYU_ITE2031
}
