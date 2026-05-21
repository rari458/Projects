.data
arr0:	.word	42
arr1:	.word	17
arr2:	.word	88
arr3:	.word	5
arr4:	.word	63
cnt:	.word	5
min:	.word	0
max:	.word	0

.text
main:
	lw	$t0, arr0($gp)
	add	$t1, $zero, $t0
	add	$t2, $zero, $t0
	lw	$t3, arr1($gp)
	slt	$t4, $t3, $t1
	beq	$t4, $zero, s1
	add	$t1, $zero, $t3
s1:
	slt	$t4, $t2, $t3
	beq	$t4, $zero, s2
	add	$t2, $zero, $t3
s2:
	lw	$t3, arr2($gp)
	slt	$t4, $t3, $t1
	beq	$t4, $zero, s3
	add	$t1, $zero, $t3
s3:
	slt	$t4, $t2, $t3
	beq	$t4, $zero, s4
	add	$t2, $zero, $t3
s4:
	lw	$t3, arr3($gp)
	slt	$t4, $t3, $t1
	beq	$t4, $zero, s5
	add	$t1, $zero, $t3
s5:
	slt	$t4, $t2, $t3
	beq	$t4, $zero, s6
	add	$t2, $zero, $t3
s6:
	lw	$t3, arr4($gp)
	slt	$t4, $t3, $t1
	beq	$t4, $zero, s7
	add	$t1, $zero, $t3
s7:
	slt	$t4, $t2, $t3
	beq	$t4, $zero, s8
	add	$t2, $zero, $t3
s8:
	sw	$t1, min($gp)
	sw	$t2, max($gp)
	nor	$t5, $t1, $zero
	addi	$t5, $t5, 1
	add	$t6, $t2, $t5
	nop
	li	$v0, 10
	syscall
