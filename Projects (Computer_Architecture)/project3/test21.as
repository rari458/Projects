.data
dummy: .word 0

.text
main:
    addi $zero, $zero, 99   
    add  $t0, $zero, $zero
    nop

    addi $v0, $zero, 10
    syscall
