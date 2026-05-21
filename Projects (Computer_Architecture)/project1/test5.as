.data
base:	.word	2
exp:	.word	8
out:	.word	0

.text
main:
	lw	$a0, base($gp)
	lw	$a1, exp($gp)
	jal	power
	sw	$v0, out($gp)
	j	exit
power:
	addi	$v0, $zero, 1
	beq	$a1, $zero, pdone
	add	$t0, $zero, $a1
	add	$t1, $zero, $a0
ploop:
	beq	$t0, $zero, pdone
	addi	$t2, $t0, -1
	beq	$t2, $zero, pskip
	jal	mult
	j	pnext
pskip:
	add	$v0, $zero, $t1
pnext:
	addi	$t0, $t0, -1
	j	ploop
pdone:
	jr	$ra
mult:
	add	$t3, $zero, $zero
	add	$t4, $zero, $t1
mloop:
	beq	$t4, $zero, mdone
	add	$t3, $t3, $v0
	addi	$t4, $t4, -1
	j	mloop
mdone:
	add	$v0, $zero, $t3
	jr	$ra
exit:
	nor	$t5, $v0, $zero
	addi	$t5, $t5, 1
	slt	$t6, $t5, $zero
	nop
	li	$v0, 10
	syscall
