CC = gcc -DHYU_ITE2031
OBJS = alu.o control.o mem.o reg_file.o loader.o pipeline.o hazard.o forward.o simulator.o
TARGET = simulator
 
.SUFFIXES : .c .o
 
all : $(TARGET)
 
$(TARGET): $(OBJS)
	   $(CC) -o $@ $(OBJS)
 
clean :
	rm -f $(OBJS) $(TARGET)
