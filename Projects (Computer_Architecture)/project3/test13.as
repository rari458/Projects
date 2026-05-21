.data
dummy: .word 0

.text
main:
    addi $t0, $zero, 1
    addi $t1, $zero, 2
    nop
    nop
    beq  $t0, $t1, skip
    addi $t2, $zero, 99
skip:
    nop
    li   $v0, 10
    syscall
