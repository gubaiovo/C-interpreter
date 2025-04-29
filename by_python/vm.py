LEA, IMM, JMP, CALL, JZ, JNZ, ENT, ADJ, LEV, LI, LC, SI, SC, PUSH, \
OR, XOR, AND, EQ, NE, LT, GT, LE, GE, SHL, SHR, ADD, SUB, MUL, DIV, MOD, \
OPEN, READ, CLOS, PRTF, MALC, MSET, MCMP, EXIT = range(38)


class VM:
    def __init__(self, text:list, poolsize:int = 256*1024):
        self.poolsize = poolsize
        self.text = text
        self.data = bytearray(poolsize)
        self.stack = [0] * poolsize
        
        self.pc = 0
        self.sp = poolsize - 1
        self.bp = self.sp
        self.ax = 0
        
        self.fd_map = {}
        self.mem_map = {}
        self.next_fd = 3
        
    def read_mem(self, addr, size):
        if addr < 0 or addr+size > self.poolsize:
            raise ValueError("Invalid memory access")
        return bytes(self.data[addr:addr+size])
    def write_mem(self, addr, data):
        if addr < 0 or addr+len(data) > self.poolsize:
            raise ValueError("Invalid memory access")
        self.data[addr:addr+len(data)] = data
    def run(self):
        while True:
            if self.pc >= len(self.text):
                raise RuntimeError("Program counter out of range")
            op = self.text[self.pc] # read operation code
            self.pc += 1 # point to next instruction
            if op == IMM:
                self.ax = self.text[self.pc]
                self.pc += 1
            elif op == LC:
                if 0 <= self.ax < self.poolsize:
                    self.ax = self.data[self.ax]
                else:
                    raise ValueError("Invalid memory access")
            elif op == LI:
                if 0 <= self.ax < self.poolsize:
                    bytes_data = self.data[self.ax:self.ax+4]
                    self.ax = int.from_bytes(bytes_data, byteorder='little', signed=True)
                else:
                    raise ValueError("Invalid memory access")
            elif op == SC:
                addr = self.stack[self.sp]
                self.sp += 1
                if 0 <= addr < self.poolsize:
                    self.data[addr] = self.ax & 0xff
                else:
                    raise ValueError(f"Invalid memory access: {addr}")
            elif op == SI:
                addr = self.stack[self.sp]
                self.sp += 1
                if 0 <= addr <= self.poolsize-4:
                    bytes_data = self.ax.to_bytes(4, byteorder='little', signed=True)
                    self.data[addr:addr+4] = bytes_data
                else:
                    raise ValueError(f"Invalid memory access: {addr}")
            elif op == PUSH:
                print(f"PUSH {self.ax}")
                self.sp -= 1
                self.stack[self.sp] = self.ax
            elif op == JMP:
                self.pc = self.text[self.pc]
            elif op == JZ:
                if self.ax == 0:
                    self.pc = self.text[self.pc]
                else:
                    self.pc += 1
            elif op == JNZ:
                if self.ax != 0:
                    self.pc = self.text[self.pc]
                else:
                    self.pc += 1
            elif op == CALL:
                self.sp -= 1
                self.stack[self.sp] = self.pc + 1
                self.pc = self.text[self.pc]
            elif op == ENT:
                self.sp -= 1
                self.stack[self.sp] = self.bp
                self.bp = self.sp
                self.sp -= self.text[self.pc]
                self.pc += 1
            elif op == ADJ:
                self.sp += self.text[self.pc]
                self.pc += 1
            elif op == LEV:
                self.sp = self.bp
                self.bp = self.stack[self.sp]
                self.sp += 1
                self.pc = self.stack[self.sp]
                self.sp += 1
            elif op == LEA:
                self.ax = self.bp + self.text[self.pc]
                self.pc += 1
                
            elif op in [ADD, SUB, MUL, DIV, MOD, 
                        OR, XOR, AND, SHL, SHR,
                        EQ, NE, LT, GT, LE, GE]:         
                a = self.stack[self.sp]
                self.sp += 1
                if op == ADD: 
                    print(f"ADD a ax: {a} + {self.ax}")
                    self.ax = a + self.ax
                elif op == SUB:
                    print(f"SUB a ax: {a} - {self.ax}")
                    self.ax = a - self.ax
                elif op == MUL: 
                    print(f"MUL a ax: {a} * {self.ax}")
                    self.ax = a * self.ax
                elif op == DIV: 
                    print(f"DIV a ax: {a} / {self.ax}")
                    self.ax = a // self.ax
                elif op == MOD: self.ax = a % self.ax
                elif op == OR: self.ax = a | self.ax
                elif op == XOR: self.ax = a ^ self.ax
                elif op == AND: self.ax = a & self.ax
                elif op == SHL: self.ax = a << self.ax
                elif op == SHR: self.ax = a >> self.ax
                elif op == EQ: self.ax = 1 if a == self.ax else 0
                elif op == NE: self.ax = 1 if a != self.ax else 0
                elif op == LT: self.ax = 1 if a < self.ax else 0
                elif op == GT: self.ax = 1 if a > self.ax else 0
                elif op == LE: self.ax = 1 if a <= self.ax else 0
                elif op == GE: self.ax = 1 if a >= self.ax else 0
                
            elif op == EXIT:
                print(f"exit({self.stack[self.sp]})")
                return self.stack[self.sp]
            elif op == OPEN:
                path = self.read_mem(self.stack[self.sp+1], 256).split(b'\x00')[0].decode()
                mode = self.stack[self.sp]
                try:
                    fd = open(path, {0: 'r', 1: 'w', 2: 'a'}.get(mode, 'r')).fileno()
                    self.fd_map[self.next_fd] = open(path, 'rb' if mode == 0 else 'wb')
                    self.ax = self.next_fd
                    self.next_fd += 1
                except Exception as e:
                    print(f"Error: {e}")
                    self.ax = -1
            elif op == READ:
                fd = self.stack[self.sp+2]
                buf = self.stack[self.sp+1]
                count = self.stack[self.sp]
                if fd in self.fd_map:
                    data = self.fd_map[fd].read(count)
                    self.write_mem(buf, data)
                    self.ax = len(data)
                else:
                    self.ax = -1
            elif op == PRTF:
                fmt_ptr = self.stack[self.sp]        
                fmt_bytes = self.read_mem(fmt_ptr, 256).split(b'\x00')[0]
                fmt = fmt_bytes.decode('utf-8')
                arg_count = fmt.count('%') - 2 * fmt.count('%%') 
                arg_count = max(0, arg_count)  
                
                args = []
                for i in range(arg_count):
                    if self.sp + 1 + i >= self.poolsize:
                        break 
                    args.append(self.stack[self.sp + 1 + i])
                try:
                    output = fmt % tuple(args)
                    print(output, end='')
                    self.ax = len(output) 
                except:
                    self.ax = -1
            else:
                raise RuntimeError(f"Unknown opcode: {op} at PC={self.pc-1}")


def main():
    code = [
        IMM, 3000,
        PUSH,
        PRTF,
        ADJ, 1,
        PRTF,
        EXIT
    ]
    vm = VM(code, poolsize=4096)
    exit_code = vm.run()
    print(f"Exit code: {exit_code}")
if __name__ == '__main__':
    main()