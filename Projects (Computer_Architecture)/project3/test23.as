.data
el0: .word 5
el1: .word 12
el2: .word 3

.text
main:
    addi $t2, $zero, 0

    lw   $t0, el0($gp)
    slt  $t1, $t2, $t0
    beq  $t1, $zero, s0
    add  $t2, $t0, $zero

s0: lw   $t0, el1($gp)
    slt  $t1, $t2, $t0
    beq  $t1, $zero, s1
    add  $t2, $t0, $zero

s1: lw   $t0, el2($gp)
    slt  $t1, $t2, $t0
    beq  $t1, $zero, done
    add  $t2, $t0, $zero

done:
    li   $v0, 10
    syscall
