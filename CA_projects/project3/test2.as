.data
dummy: .word 0

.text
main:
    addi $t0, $zero, 5
    add  $t1, $t0, $zero
    nop
    li   $v0, 10
    syscall
