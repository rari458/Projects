/* Project 1: Assembler code fragment */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#define MAX_LINE_LEN 1000
#define MAX_NAME_LEN 8
#define MAX_DATA	50
#define MAX_INST 50
#define MAX_SYMBOLS 50

#define R_TYPE 0
#define I_TYPE 1
#define J_TYPE 2
#define PSUEDO 3

struct symbol {
	char name[MAX_NAME_LEN];
	int offset;
};

const char* reg_names[32] = { "$zero", "$at", "$v0", "$v1",
    "$a0", "$a1", "$a2", "$a3",
    "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
    "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
    "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"};

/* Symbol tables for data and instrunctions */
int n_dsym, n_isym;
struct symbol dsym[MAX_SYMBOLS], isym[MAX_SYMBOLS];

/* data and text sections */
int n_data, n_inst;
unsigned int data[MAX_DATA], text[MAX_INST];

int get_type(char*);
int read_and_parse(FILE*, int*, char*, char*, 
		char*, char*, char*, char*, char*);
int regnum(char*);
int find_sym(struct symbol*, int, char*);
int gp_offset(struct symbol*, int, char*);
int pc_offset(struct symbol*, int, char*, int);
int psuedo_offset(struct symbol*, int, char*);
unsigned int encode(int, char*, char*, char*, char*, char*);
void print_fields(unsigned);

int main(int argc, char *argv[]) {
	int i, is_data_section;
	char *inFile, *outFile;
	FILE *inFilePtr, *outFilePtr;

	char label[MAX_NAME_LEN], value[MAX_NAME_LEN], opcode[MAX_NAME_LEN], 
			 rd[MAX_NAME_LEN], rs[MAX_NAME_LEN], rt[MAX_NAME_LEN],
			 imm[MAX_NAME_LEN];

	if (argc != 3) {
		printf("error: usage: %s <assembly-code-file> <machine-code-file>\n",
				argv[0]);
		exit(1);
	}

	inFile = argv[1];
	outFile = argv[2];

	inFilePtr = fopen(inFile, "r");
	if (inFilePtr == NULL) {
		printf("error in opening %s\n", inFile);
		exit(1);
	}
	outFilePtr = fopen(outFile, "w");
	if (outFilePtr == NULL) {
		printf("error in opening %s\n", outFile);
		exit(1);
	}

	/* initialization of data structures */
	/* we will parse two sections; .data and .text
		 and manage infomation into two separate tables.
		 is_data_section indicates that the assembly was in
		 whether .data section or not. */
	is_data_section = 0;

	/* symbol tables for .data and .text */
	n_dsym = n_isym = 0; // index for each table
	memset(dsym, 0, sizeof(struct symbol) * MAX_SYMBOLS);
	memset(isym, 0, sizeof(struct symbol) * MAX_SYMBOLS);

	/* byte offset for the section; .data and .text repsectively. */
	n_data = n_inst = 0; // byte offset (or address) for each section
	memset(data, 0, sizeof(int) * MAX_DATA);
	memset(text, 0, sizeof(int) * MAX_INST);

	/* TODO: Phase-1 label detection 
	 	       using read_and_parse() to build symbol tables. 
	         dsym is for data symbols and isym is for text symbols. */
	n_data = n_inst = 0;
	while (read_and_parse(inFilePtr, &is_data_section,
				label, value, opcode, rd, rs, rt, imm)) {
		/*
		if (is_data_section) {
		}
		*/
	}

	/* this is how to rewind the file ptr so that you start reading from the
		 beginning of the file */
	n_data = n_inst = 0;
	rewind(inFilePtr);

	/* TODO: Phase-2 generate machine codes
	         information is encoded into two section; data[] and text[] */
	while (read_and_parse(inFilePtr, &is_data_section, 
				label, value, opcode, rd, rs, rt, imm)) {
		/*
		if (is_data_section) {
		}
		*/
	}

	/* TODO: Phase-3 write each section to outfile
		       put each binary in the section into the out file.
					 The text section should be followed by data. */

	/* if you want to verify all fields in the machine language */
	for (i = 0; i < n_inst; i++) {
		print_fields(text[i]);
	}

	if (inFilePtr) {
		fclose(inFilePtr);
	}
	if (outFilePtr) {
		fclose(outFilePtr);
	}
	return 0;
}

/*
 * Read and parse a line of the assembly-language file. 
 * is_data_section is returned to indicate whther 
 * the section is data or text.
 * Parsed fields are returned in label, opcode, rd, rs, rt, imm 
 * (these strings must have memory already allocated to them).
 *
 * Return values:
 *     0 if reached end of file
 *     1 if all went well
 *
 * exit(1) if line is too long.
 */
int read_and_parse(FILE* inFilePtr, int* is_data_section,
		char* label, char* value,
		char* opcode, char* rd, char* rs, char* rt, char* imm)
{
	char line[MAX_LINE_LEN];
	char *ptr, *pos;

	/* clear prior result */
	label[0] = value[0] = opcode[0] 
		= rd[0] = rs[0] = rt[0] = imm[0] = '\0';

READ_NEXT:
	/* read the line from the assembly-language file */
	if (!fgets(line, MAX_LINE_LEN, inFilePtr)) {
		/* reached end of file */
		return 0;
	}

	/* check for line too long (by looking for a \n) */
	if (!strchr(line, '\n')) {
		/* line too long */
		printf("error: line too long\n");
		exit(1);
	}

	/* Removing comments */
	if ((pos = strchr(line, '#'))) {
		*pos = '\0';
	}

	ptr = line;
	/* Section names */
	if (strstr(ptr, ".data")) {
		/* no assembly language to parse on this line */
		*is_data_section = 1;
		goto READ_NEXT;
	} else if (strstr(ptr, ".text")) {
		/* no assembly language to parse on this line */
		*is_data_section = 0;
		goto READ_NEXT;
	}

	/* Labels */
	if (sscanf(ptr, "%[^:\t\n\r ]", label)) {
		ptr += strlen(label);
		ptr++;
	}

	if (*is_data_section) {
		if ((pos = strstr(ptr, ".word"))) {
			/* Skip .word */
			ptr = (pos + 5);
		}

		/* Immediate values in the data section */
		sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r ]", value);
		if (!strlen(value)) {
			goto READ_NEXT;
		}
	} else {
		/* Assembly languages */
		sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r ]", opcode);
		if (!strlen(opcode)) 
			goto READ_NEXT;

		ptr = strstr(ptr, opcode) + strlen(opcode);
		switch (get_type(opcode)) {
			case R_TYPE:
				if (!strcmp(opcode, "jr")) {
					sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r ]", rs);
				} else {
					sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r, ],%*[\t\n\r ]"
							"%[^\t\n\r, ],%*[\t\n\r ]%[^\t\n\r ]", rd, rs, rt);
				}
				break;
			case I_TYPE:
				if (!strcmp(opcode, "lw") || !strcmp(opcode, "sw")) {
					sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r, ],%*[\t\n\r ]%[^(](%[^)]", 
							rt, imm, rs);
				} else if (!strcmp(opcode, "li")) {
					sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r, ],%*[\t\n\r ]"
							"%[^\t\n\r, ]", rt, rs);
				} else if (!strcmp(opcode, "beq")) {
					sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r, ],%*[\t\n\r ]"
							"%[^\t\n\r, ],%*[\t\n\r ]%[^\t\n\r ]", rs, rt, imm);
				} else {
					sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r, ],%*[\t\n\r ]"
							"%[^\t\n\r, ],%*[\t\n\r ]%[^\t\n\r ]", rt, rs, imm);
				}
				break;
			case J_TYPE:
				sscanf(ptr, "%*[\t\n\r ]%[^\t\n\r ]", imm);
				break;
		}
	}
	return 1;
}

/* This is a helper function to indicate MIPS instruction type */
int get_type(char* opcode) {
	if (!strcmp(opcode, "add")) {
		return R_TYPE;
	} else if (!strcmp(opcode, "slt")) {
		return R_TYPE;
	} else if (!strcmp(opcode, "nor")) {
		return R_TYPE;
	} else if (!strcmp(opcode, "jr")) {
		return R_TYPE;
	} else if (!strcmp(opcode, "addi")) {
		return I_TYPE;
	} else if (!strcmp(opcode, "lw")) {
		return I_TYPE;
	} else if (!strcmp(opcode, "sw")) {
		return I_TYPE;
	} else if (!strcmp(opcode, "beq")) {
		return I_TYPE;
	} else if (!strcmp(opcode, "j")) {
		return J_TYPE;
	} else if (!strcmp(opcode, "jal")) {
		return J_TYPE;
	} else if (!strcmp(opcode, "nop")) {
		return R_TYPE;
	} else if (!strcmp(opcode, "li")) {
		return I_TYPE;
	} else if (!strcmp(opcode, "syscall")) {
		return R_TYPE;
	} 
}

/* This is a helper function to translate a register name
	 into a register number. i.e., $zero to 0 */
int regnum(char* string) {
	int i;
	if (string[0] != '$')
		return -1;

	for (i = 0; i < 32; i++) {
		if (!strcmp(string, reg_names[i])) {
			return i;
		}
	}
	return -1;
}

/* Find a label in the symbol table and return its index. 
	 If no label found, it returns -1. */
int find_sym(struct symbol* symbols, int n_symbols, char* name) {
	// TODO: complete here
	return -1;
}

/* For lw and sw instructions, used to encode the immediate field 
	 with the given label. */
int gp_offset(struct symbol* symbols, int n_symbols, char* label) {
	int base;
	// We assume that $gp has 0x10008000
	base = 0x10008000;
	// TODO: complete here
	return 0;
}

/* For beq and bne instructions, used to encode the immediate field 
	 with the given label. */
int pc_offset(struct symbol* symbols, int n_symbols, char* label, int pc) {
	/* TODO: complete here */
	return 0;
}

/* For J-type instructions, used to encode the immediate field 
	 with the given label. */
int psuedo_offset(struct symbol* symbols, int n_symbols, char* label) {
	/* TODO: complete here */
	return 0;
}

/* A function returns a binary corresponding to the given assembly language. */
unsigned int encode(int pc, char* opcode, char* rs, char* rt, char* rd, char* imm) {
	unsigned int ret = 0U;
	unsigned int f_opcode, f_rs, f_rt, f_rd, f_shamt, f_func, f_imm;
	f_opcode = f_rs = f_rt = f_rd = f_shamt = f_func = f_imm = 0;

	/* TODO: complete here.
		 determine all field values for the given information.
		 we provide a few encoding examples; nop, li, and syscall */
	if (!strcmp(opcode, "nop")) { 
		// 0x00000000
		f_opcode = 0U; f_func = 0U;
	} else if (!strcmp(opcode, "li")) {
		// same as addi $rt, $zero, imm
		f_opcode = 8; f_rt = regnum(rt); f_imm = atoi(rs) & 0xFFFF;
	} else if (!strcmp(opcode, "syscall")) { 
		// 0x0000000C
		f_opcode = 0U; f_func = 12U;
	}

	switch (get_type(opcode)) {
		case R_TYPE:
			return f_opcode << 26 | f_rs << 21 | f_rt << 16 | f_rd << 11
				| f_shamt << 6 | f_func;
		case I_TYPE:
			return f_opcode << 26 | f_rs << 21 | f_rt << 16 | f_imm;
		case J_TYPE:
			return f_opcode << 26 | f_imm;
	}
}

/* This is a utility function to print each file in a machine language. */
void print_fields(unsigned int inst) {
	unsigned int opcode = inst >> 26;
	printf("%3d | ", opcode);
	if (opcode == 2 || opcode == 3) {
		// J-type
		printf("%27d\n", inst & 0x3FFFFFF);
	} else {
		printf("%3d | ", (inst >> 21) & 0x1F );
		printf("%3d | ", (inst >> 16) & 0x1F );
		if (opcode == 0) {
			// R-type
			printf("%3d | ", (inst >> 11) & 0x1F );
			printf("%3d | ", (inst >> 6) & 0x1F );
			printf("%3d\n", (inst) & 0x3F );
		} else {
			// I-type
			printf("%15d\n", (((signed) inst) << 16) >> 16);
		}
	}
}
