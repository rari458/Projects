.data
a: .word 5
b: .word 0

.text
main:
    lw   $t0, a($gp)
    nop
    sw   $t0, b($gp)
    nop
    li   $v0, 10
    syscall
