.data
dummy: .word 0

.text
main:
    jal  func
    j    done
func:
    addi $t0, $zero, 42
    j    done
done:
    nop
    li   $v0, 10
    syscall
