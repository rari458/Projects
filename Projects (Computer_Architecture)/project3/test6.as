.data
dummy: .word 0

.text
main:
    addi $t0, $zero, 0
    beq  $t0, $zero, done
    addi $t1, $zero, 1
done:
    nop
    li   $v0, 10
    syscall
