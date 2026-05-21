.data
n:	.word	10
result:	.word	0

.text
main:
	lw	$t0, n($gp)
	addi	$t1, $zero, 0
	addi	$t2, $zero, 1
	addi	$t3, $zero, 0
loop:
	beq	$t3, $t0, end
	add	$t4, $t1, $t2
	add	$t1, $zero, $t2
	add	$t2, $zero, $t4
	addi	$t3, $t3, 1
	j	loop
end:
	sw	$t1, result($gp)
	slt	$t5, $t1, $t0
	beq	$t5, $zero, pos
	nor	$t1, $t1, $zero
	addi	$t1, $t1, 1
pos:
	add	$t6, $t1, $zero
	nop
	li	$v0, 10
	syscall
