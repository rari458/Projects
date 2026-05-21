.data
ra1: .word 0
ra2: .word 0
arg: .word 0

.text
main:
    addi $t0, $zero, 3
    jal  outer
    add  $v1, $v0, $t0

    li   $v0, 10
    syscall

outer:
    sw   $ra, ra1($gp)
    sw   $t0, arg($gp)
    jal  inner
    lw   $t0, arg($gp)
    add  $v0, $v0, $t0
    lw   $ra, ra1($gp)
    jr   $ra

inner:
    sw   $ra, ra2($gp)
    addi $v0, $t0, 10
    lw   $ra, ra2($gp)
    jr   $ra
