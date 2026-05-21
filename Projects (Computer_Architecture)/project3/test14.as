.data
dummy: .word 0

.text
main:
    addi $t0, $zero, 5
    nop
    nop
    nop
    beq  $t0, $t0, skip
    addi $t2, $zero, 99
skip:
    nop
    li   $v0, 10
    syscall
