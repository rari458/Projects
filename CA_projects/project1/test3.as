.data
a:	.word	15
b:	.word	25
c:	.word	5
d:	.word	0
e:	.word	0

.text
main:
	lw	$a0, a($gp)
	lw	$a1, b($gp)
	jal	addtwo
	sw	$v0, d($gp)
	lw	$a0, c($gp)
	lw	$a1, d($gp)
	jal	subtrt
	sw	$v0, e($gp)
	j	exit
addtwo:
	add	$v0, $a0, $a1
	jr	$ra
subtrt:
	nor	$t0, $a1, $zero
	addi	$t0, $t0, 1
	add	$v0, $a0, $t0
	slt	$t1, $v0, $zero
	beq	$t1, $zero, ispos
	nor	$v0, $v0, $zero
	addi	$v0, $v0, 1
ispos:
	jr	$ra
exit:
	li	$v0, 10
	syscall
