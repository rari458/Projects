.data
dummy: .word 0

.text
main:
    addi $t1, $zero, 1
    addi $t1, $zero, 2

    add  $t2, $t1, $zero

    addi $t3, $zero, 3      # Writes to $t3
    addi $t4, $zero, 4      # Writes to $t4

    add  $t5, $t3, $t4

    li   $v0, 10
    syscall
