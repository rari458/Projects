.data
a: .word 0

.text
main:
    addi $t0, $zero, 42
    sw   $t0, a($gp)
    nop
    li   $v0, 10
    syscall
