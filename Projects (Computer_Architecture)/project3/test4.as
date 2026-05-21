.data
a: .word 7

.text
main:
    lw   $t0, a($gp)
    add  $t1, $t0, $zero
    nop
    li   $v0, 10
    syscall
