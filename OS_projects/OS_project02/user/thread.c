#include "kernel/types.h"
#include "thread.h"
#include "user/user.h"

#define PGSIZE 4096

int thread_create(void(*start_routine)(void*, void*), void *arg1, void *arg2) {
	void*stack = malloc(PGSIZE);
	if(stack == 0) return -1;
	
	int tid = clone(start_routine, arg1, arg2, stack);
	if (tid < 0) {
		free(stack);
		return -1;
	}
	return tid;
}

int thread_join(){
	void *stack=0;
	int tid = join(&stack);
	
	if (tid > 0 && stack != 0) free(stack);
	
	return tid;
}