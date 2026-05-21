#include "types.h"
#include "riscv.h"
#include "defs.h"
#include "param.h"
#include "memlayout.h"
#include "spinlock.h"
#include "proc.h"

extern struct proc proc[NPROC];
extern struct spinlock tickslock;
extern int sched_mode;
extern uint ticks;

uint64
sys_exit(void)
{
  int n;
  argint(0, &n);
  exit(n);
  return 0;  // not reached
}

uint64
sys_getpid(void)
{
  return myproc()->pid;
}

uint64
sys_fork(void)
{
  return fork();
}

uint64
sys_wait(void)
{
  uint64 p;
  argaddr(0, &p);
  return wait(p);
}

uint64
sys_sbrk(void)
{
  uint64 addr;
  int n;

  argint(0, &n);
  addr = myproc()->sz;
  if(growproc(n) < 0)
    return -1;
  return addr;
}

uint64
sys_sleep(void)
{
  int n;
  uint ticks0;

  argint(0, &n);
  if(n < 0)
    n = 0;
  acquire(&tickslock);
  ticks0 = ticks;
  while(ticks - ticks0 < n){
    if(killed(myproc())){
      release(&tickslock);
      return -1;
    }
    sleep(&ticks, &tickslock);
  }
  release(&tickslock);
  return 0;
}

uint64
sys_kill(void)
{
  int pid;

  argint(0, &pid);
  return kill(pid);
}

// return how many clock tick interrupts have occurred
// since start.
uint64
sys_uptime(void)
{
  uint xticks;

  acquire(&tickslock);
  xticks = ticks;
  release(&tickslock);
  return xticks;
}

uint64
sys_yield(void)
{
  yield();
  return 0;
}

uint64
sys_getlev(void)
{
  if (sched_mode == 0) return 99;
  return myproc()->level;
}

uint64
sys_setpriority(void)
{
  int pid, priority;

  argint(0, &pid);
  argint(1, &priority);

  if (priority < 0 || priority > 3) return -2;

  struct proc *p;
  int found = 0;

  for (p = proc; p < &proc[NPROC]; p++) {
    acquire(&p->lock);
    if (p->pid == pid && p->state != UNUSED) {
      p->priority = priority;
      found = 1;
      release(&p->lock);
      break;
    }
    release(&p->lock);
  }

  if (!found) return -1;

  return 0;
}

uint64
sys_mlfqmode(void)
{
  if (sched_mode == 1) {
    printf("Already in MLFQ mode\n");
    return -1;
  }

  sched_mode = 1;

  acquire(&tickslock);
  ticks = 0;
  release(&tickslock);

  struct proc *p;
  for (p = proc; p < &proc[NPROC]; p++) {
    acquire(&p->lock);
    if (p->state != UNUSED) {
      p->priority = 3;
      p->qtime = 0;
      p->level = 0;
    }
    release(&p->lock);
  }

  printf("successfully changed to MLFQ mode!\n");
  return 0;
}

uint64
sys_fcfsmode(void)
{
  if (sched_mode == 0) {
    printf("Already in FCFS mode\n");
    return -1;
  }

  sched_mode = 0;

  acquire(&tickslock);
  ticks = 0;
  release(&tickslock);

  struct proc *p;
  for (p = proc; p < &proc[NPROC]; p++) {
    acquire(&p->lock);
    if (p->state != UNUSED) {
      p->priority = -1;
      p->level = -1;
      p->qtime = -1;
    }
    release(&p->lock);
  }

  printf("successfully changed to FCFS mode!\n");
  return 0;
}