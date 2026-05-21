.data
src: .word 1024
dst: .word 0

.text
main:
    lw   $t0, src($gp)
    sw   $t0, dst($gp)

    lw   $t1, dst($gp)
    nop

    li   $v0, 10
    syscall
