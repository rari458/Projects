.data
value1:	.word	1
value2:	.word	2

.text
main:
	lw	$t1, value1($gp)	# load $t1 with 1 (symbolic address)
	lw	$t2, value2($gp)	# load $t2 with 2 (symbolic address)
	addi	$t2, $t2, 1	# increment $t2
	slt	$t0, $t1, $t2 
	nop # same as slt $zero, $zero, 0
	li	$v0, 10	# exit(0)
	syscall
