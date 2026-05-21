.data
val: .word 5

.text
main:
    lw   $t0, val($gp)      
    addi $t1, $zero, 5

    beq  $t0, $t1, match

    addi $t2, $zero, 99
    j    end

match:
    addi $t2, $zero, 1

end:
    nop
    li   $v0, 10
    syscall
