.data
dummy: .word 0

.text
main:
    jal  func
    addi $t0, $zero, 1

    addi $v0, $zero, 10
    syscall

func:
    jr   $ra
    nop
