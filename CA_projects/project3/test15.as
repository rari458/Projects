.data
dummy: .word 0

.text
main:
    j    done
    addi $t0, $zero, 99
done:
    nop
    li   $v0, 10
    syscall
