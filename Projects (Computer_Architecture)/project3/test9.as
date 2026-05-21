.data
a: .word 0

.text
main:
    lw   $t0, a($gp)
    nop
    beq  $t0, $zero, done
    addi $t1, $zero, 1
done:
    nop
    li   $v0, 10
    syscall
