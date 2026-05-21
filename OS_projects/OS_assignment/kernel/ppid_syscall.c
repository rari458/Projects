#include "types.h"
#include "param.h"
#include "memlayout.h"
#include "riscv.h"
#include "spinlock.h"
#include "proc.h"
#include "defs.h"

int
get_ppid(void)
{
	return myproc()->parent->pid;
}

uint64
sys_getppid(void)
{
	return get_ppid();
}
