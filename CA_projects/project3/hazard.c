#include "hazard.h"
#include "control.h"

int detect_load_use_data_hazard(const state_info* state) {
#ifdef HYU_ITE2031
	if (get_inst_type(state->IDEX.Inst) == LW) {
		field_info fields;
		setup_fields(state->IFID.Inst, &fields);
		if (state->IDEX.RegisterRt != 0 &&
				(state->IDEX.RegisterRt == fields.rs ||
				 state->IDEX.RegisterRt == fields.rt)) {
			return 1;
		}
	}
	return 0;
#endif //HYU_ITE2031
}

int detect_data_hazard_for_branch(const state_info* state) {
#ifdef HYU_ITE2031
	if (get_inst_type(state->IFID.Inst) == BEQ) {
		field_info fields;
		unsigned char idex_dest;
		setup_fields(state->IFID.Inst, &fields);

		if (state->IDEX.RegDest == ASSERT)
			idex_dest = state->IDEX.RegisterRd;
		else
			idex_dest = state->IDEX.RegisterRt;

		if (state->IDEX.RegWrite == ASSERT && idex_dest != 0 &&
				(idex_dest == fields.rs || idex_dest == fields.rt))
			return 1;
	}
	return 0;
#endif //HYU_ITE2031
}
