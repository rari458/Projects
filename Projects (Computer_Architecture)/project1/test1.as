.data
x:	.word	10
y:	.word	20
z:	.word	30
sum:	.word	0
max:	.word	0

.text
main:
	lw	$t0, x($gp)
	lw	$t1, y($gp)
	lw	$t2, z($gp)
	add	$t3, $t0, $t1
	add	$t3, $t3, $t2
	sw	$t3, sum($gp)
	slt	$t4, $t0, $t1
	beq	$t4, $zero, xbig1
	add	$t5, $zero, $t1
	j	cmp2
xbig1:
	add	$t5, $zero, $t0
cmp2:
	slt	$t4, $t5, $t2
	beq	$t4, $zero, done
	add	$t5, $zero, $t2
done:
	sw	$t5, max($gp)
	nor	$t6, $t0, $zero
	addi	$t6, $t6, 1
	add	$t7, $t0, $t6
	nop
	li	$v0, 10
	syscall
