.data
dummy: .word 0

.text
main:
    addi $t0, $zero, 3
    addi $t1, $zero, 4
    nop
    nop
    add  $t2, $t0, $t1
    nop
    li   $v0, 10
    syscall
