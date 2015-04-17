import sys
from random import randint, random, choice, shuffle
from itertools import cycle

lattice_dimension = 1
point_mutation_rate = .0025
frameshift_rate = .05
default_sip = ??

instruction_set = [
    'nop_A',
    'nop_B',
    'nop_C',
    'if_n_equ',
    'if_less',
    'pop',
    'push',
    'swap_stk',
    'swap',
    'shift_r',
    'shift_l',
    'inc',
    'dec',
    'add',
    'sub',
    'nand',
    'IO',
    'h_alloc',
    'h_divide',
    'h_copy',
    'h_search',
    'mov_head',
    'jmp_head',
    'get_head',
    'if_label',
    'set_flow'
]


# a genome that just encodes for copying
starting_genome = [
    'h_alloc',
    'h_search',
    'nop_C',
    'nop_A',
    'mov_head'
    ] + (['nop_C'] * 36) + [
    'h_search',
    'h_copy',
    'if_label',
    'nop_C',
    'nop_A',
    'h_divide',
    'mov_head',
    'nop_A',
    'nop_B'
]

# http://devolab.cse.msu.edu/software/avida/doc/cpu_tour.html
class Organism:

    @staticmethod
    def randval():
        return randint(0, 2 ** 32 - 1)

    def output():
        pass

    # x and y give the location on the lattice
    def __init__(self, lattice, starting_genome, x, y):
        self.lattice = lattice
        self.instructions = starting_genome
        self.x = x
        self.y = y

        self.inputs = cycle([self.randval(), self.randval(), self.randval()])

        # at the very least, ip and rh need to start at beginning
        self.heads = {
            'ip': 0,
            'rh': 0,
            'wh': 0,
            'fh': 0
        }

        self.regs = {
            'ax': self.randval(),
            'bx': self.randval(),
            'cx': self.randval()
        }

        self.active_stack = 0
        self.stacks = [ [], [] ]
        self.sips = 100
        self.computational_merit = 1

        self.recent_copies = []

        self.qreg = None

    def step(self):
        if self.sips == 0:

        ixn = self.instructions[self.heads['ip']]

        ### XXX more underspecified
        if ixn == 'undefined':
        	self.heads['ip'] = 0
        	ixn = self.instructions[self.heads['ip']]

        print ixn
        self.qreg = self.instructions[(self.heads['ip'] + 1) % len(self.instructions)]
        getattr(self, ixn)()
        self.heads['ip'] = (self.heads['ip'] + 1) % len(self.instructions)
        self.sips -= 1

    def pop_stack(self):
        if len(self.stacks[self.active_stack]) == 0:
            return self.randval()
        else:
            return self.stacks[self.active_stack].pop()

    def get_reg(self):
        if self.qreg == 'nop_A':
            return 'ax'
        elif self.qreg == 'nop_C':
            return 'cx'
        else:
            return 'bx'

    def get_complement(self):
        if self.qreg == 'nop_A':
            return 'bx'
        elif self.qreg == 'nop_C':
            return 'ax'
        else:
            return 'cx'

    def resolve_head(self):
        if self.qreg == 'nop_B':
            return 'rh'
        if self.qreg == 'nop_C':
            return 'wh'
        else:
            return 'ip'

    def nop_A(self):
        self.qreg = 'nop_A'

    def nop_B(self):
        self.qreg = 'nop_B'

    def nop_C(self):
        self.qreg = 'nop_C'

    def if_n_equ(self):
        if self.regs[self.get_reg()] != self.regs[self.get_complement()]:
            self.heads['ip'] = (self.heads['ip'] + 1) % len(self.instructions)

    def if_less(self):
        if self.regs[self.get_reg()] >= self.regs[self.get_complement()]:
            self.heads['ip'] = (self.heads['ip'] + 1) % len(self.instructions)

    def pop(self):
        self.regs[self.get_reg()] = self.pop_stack()

    # TODO: they apparently limit depth to 10? unspecified
    def push(self):
        self.stacks[self.active_stack].append(self.regs[self.get_reg()])

    def swap_stk(self):
        self.active_stack = 1 if self.active_stack == 0 else 0

    def swap(self):
        tmp = self.regs[self.get_complement()]
        self.regs[self.get_complement()] = self.regs[self.get_reg()]
        self.regs[self.get_reg()] = tmp

    def shift_r(self):
        self.regs[self.get_reg()] >>= 1

    def shift_l(self):
        self.regs[self.get_reg()] <<= 1
        self.regs[self.get_reg()] %= 2 ** 32

    def inc(self):
        self.regs[self.get_reg()] += 1

    def dec(self):
        self.regs[self.get_reg()] -= 1

    def add(self):
        self.regs[self.get_reg()] = (self.regs['bx'] + self.regs['cx']) % (2 ** 32)

    # python handles modulo of negative numbers correctly
    def sub(self):
        self.regs[self.get_reg()] = (self.regs['cx'] - self.regs['bx']) % (2 ** 32)

    def nand(self):
        self.regs[self.get_reg()] = ~(self.regs['bx']  & self.regs['cx'])

    def IO(self):
        self.output(self.get_reg())
        self.regs[self.get_reg()] = self.inputs.next()

    # TODO: this is pretty underspecified how much memory is actually allocated. it says "as much as they can". is this
    # based on energy? what happens if write head goes too far? should it wrap around?
    def h_alloc(self):
        self.instructions += ['undefined'] * 100

    def h_divide(self):
        # XXX I think wh should be excluded? cut off the remaining "undefined"s

        print self.heads
        child_instructions = self.instructions[self.heads['rh']:self.heads['wh']]
        self.instructions = self.instructions[:self.heads['rh']]

        # XXX: more unspecified
        self.heads['rh'] = self.heads['wh'] = self.heads['fh'] = 0

        if len(child_instructions) == 0:
        	return

        # XXX: is this where we insert a frameshift mutation?
        if random() < frameshift_rate:
            if random() < .5:
                del child_instructions[randint(0,len(child_instructions) - 1)]
            else:
                new_location = randint(0, len(child_instructions))
                new_instruction = choice(instruction_set)
                child_instructions.insert(new_location, new_instruction)
        # TODO parent or child could have instruction length 0?
        if len(child_instructions) == 0:
        	return


        # the child clobbers whoever is originally at this location
        child_x = (self.x + randint(-1, 1)) % lattice_dimension
        child_y = (self.y + randint(-1, 1)) % lattice_dimension
        print child_instructions, self.instructions
        child = Organism(self.lattice, child_instructions, child_x, child_y)

        # "kill" the previous organism at this location
        lattice[child_y][child_x] = child

    def h_copy(self):
        if random() < point_mutation_rate:
            self.instructions[self.heads['wh']] = choice(instruction_set)
        else:
            self.instructions[self.heads['wh']] = self.instructions[self.heads['rh']]

        # XXX should this take in the read head or the actual written instruction?
        self.recent_copies.append(self.instructions[self.heads['rh']])

        self.heads['wh'] = (self.heads['wh'] + 1) % len(self.instructions)
        self.heads['rh'] = (self.heads['rh'] + 1) % len(self.instructions)



    def h_search(self):
        comp_template = []
        i = 1
        while True:
            ixn = self.instructions[(self.heads['ip'] + i) % len(self.instructions)]
            if ixn == 'nop_A':
                comp_template.append('nop_B')
            elif ixn == 'nop_B':
                comp_template.append('nop_C')
            elif ixn == 'nop_C':
                comp_template.append('nop_A')
            else:
                break
            i += 1

        if len(comp_template) == 0:
            self.regs['bx'] = self.regs['cx'] = 0
            self.heads['fh'] = (self.heads['ip'] + 1) % len(self.instructions)
            return

        self.heads['ip'] = (self.heads['ip'] + i - 1) % len(self.instructions)

        for j in range(1, len(self.instructions) - i):
            for k in range(len(comp_template)):
                if self.instructions[(self.heads['ip'] + j + k) % len(self.instructions)] != comp_template[k]:
                    break
            # we found the template!
            else:
                self.regs['bx'] = j
                self.regs['cx'] = len(comp_template)
                self.heads['fh'] = (self.heads['ip'] + j + k + 1) % len(self.instructions)
                return

        # XXX not really specified what should happen if template not found
        self.regs['bx'] = self.regs['cx'] = 0
        self.heads['fh'] = (self.heads['ip'] + 1) % len(self.instructions)

    def mov_head(self):
        self.heads[self.resolve_head()] = self.heads['fh']
        # handle the fact that "step" is about to advance ip by 1
        if self.resolve_head() == 'ip':
            self.heads['ip'] -= 1

    def jmp_head(self):
        # wrap around
        self.heads[self.resolve_head()] += self.regs['cx']

    def get_head(self):
        self.regs['cx'] = self.heads[self.resolve_head()]

    # TODO: how much of the history of copies does this need to take into account
    def if_label(self):
        comp_template = []
        i = 1
        while True:
            ixn = self.instructions[(self.heads['ip'] + i) % len(self.instructions)]
            if ixn == 'nop_A':
                comp_template.append('nop_B')
            elif ixn == 'nop_B':
                comp_template.append('nop_C')
            elif ixn == 'nop_C':
                comp_template.append('nop_A')
            else:
                break
            i += 1

        if len(comp_template) == 0 or len(comp_template) > len(self.recent_copies):
            self.heads['ip'] = (self.heads['ip'] + i) % len(self.instructions)
            return

        self.heads['ip'] = (self.heads['ip'] + i - 1) % len(self.instructions)

        for i in range(len(comp_template)):
            if comp_template[-1 - i] != self.recent_copies[-1 - i]:
                break
        else:
            # we will execute the instruction
            return

        self.heads['ip'] = (self.heads['ip'] + 1) % len(self.instructions)



    def set_flow(self):
        self.heads['fh'] = self.regs['cx']


lattice = []
for i in range(lattice_dimension):
    lattice.append([])
    for j in range(lattice_dimension):
        lattice[-1].append(Organism(lattice, starting_genome, j, i))

while True:
    rows = range(lattice_dimension)
    columns = range(lattice_dimension)
    shuffle(rows)
    shuffle(columns)
    for i in rows:
        for j in columns:
            lattice[i][j].step()
