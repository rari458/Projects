.data
dummy: .word 0

.text
main:
    addi $t0, $zero, 10
    jal  func
    nop
    addi $t1, $v0, 5
    li   $v0, 10
    syscall

func:
    addi $v0, $t0, 20
    jr   $ra
    nop
