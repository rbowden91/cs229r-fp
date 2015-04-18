import sys
from random import randint, random, choice, shuffle
from itertools import cycle

lattice_dimension = 5
point_mutation_rate = 0.0025
frameshift_rate = 0.05
avg_ixn_per_update = 30

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

tasks = [
    # XXX is this how not should work?
    {
        'name' : 'NOT',
        'merit' : 2,
        'args' : 1,
        'checkers' : [lambda x: ~x]
    },
    {
        'name' : 'NAND',
        'merit' : 2,
        'args' : 2,
        'checkers' : [lambda x, y: ~(x & y)]
    },
    {
        'name' : 'AND',
        'merit' : 4,
        'args' : 2,
        'checkers' : [lambda x, y: x & y]
    },
    {
        'name' : 'OR_N',
        'merit' : 4,
        'args' : 2,
        'checkers' : [(lambda x, y: x | ~y), (lambda x, y: ~x | y)]
    },
    {
        'name' : 'OR',
        'merit' : 8,
        'args' : 2,
        'checkers' : [lambda x, y: x | y]
    },
    {
        'name' : 'AND_N',
        'merit' : 8,
        'args' : 2,
        'checkers' : [(lambda x, y: x & ~y), (lambda x, y: ~x & y)]
    },
    {
        'name' : 'NOR',
        'merit' : 16,
        'args' : 2,
        'checkers' : [lambda x, y: ~x & ~y]
    },
    {
        'name' : 'XOR',
        'merit' : 8,
        'args' : 2,
        'checkers' : [lambda x, y: (x & ~y) | (~x & y)]
    },
    {
        'name' : 'EQU',
        'merit' : 8,
        'args' : 2,
        'checkers' : [lambda x, y: (x & y) | (~x & ~y)]
    }
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

    # x and y give the location on the lattice
    def __init__(self, lattice, starting_genome, x, y):
        self.lattice = lattice
        self.instructions = starting_genome

        # so we don't take into account h_allocs for SIP allocation
        self.initial_length = len(self.instructions)
        self.x = x
        self.y = y

        self.inputs = (self.randval(), self.randval(), self.randval())
        self.input_cycle = cycle(self.inputs)

        # calculate all the potential values we're looking to match against with IO
        self.matches = {}
        for task in tasks:
            task_matches = []
            for c in task['checkers']:
                if task['args'] == 1:
                    task_matches += [
                        { 'value' : c(self.inputs[0]), 'inputs' : [0] },
                        { 'value' : c(self.inputs[1]), 'inputs' : [1] },
                        { 'value' : c(self.inputs[2]), 'inputs' : [0] },
                    ]
                else:
                    task_matches += [
                        { 'value' : c(self.inputs[0], self.inputs[1]), 'inputs' : [0, 1] },
                        { 'value' : c(self.inputs[1], self.inputs[2]), 'inputs' : [1, 2] },
                        { 'value' : c(self.inputs[2], self.inputs[0]), 'inputs' : [0, 2] },
                    ]
            for m in task_matches:
                if m['value'] not in self.matches:
                    self.matches[m['value']] = []
                m['name'] = task['name']
                m['merit'] = task['merit']
                self.matches[m['value']].append(m)


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
        self.sips = 0
        self.computational_merit = 1

        self.recent_copies = []

        self.qreg = None

    def output(self, value):
        # XXX should only check with inputs that have actually been entered
        # XXX do they need to match multiple times to get the merit?? something seemed to suggest that
        for task in tasks:
            if value in self.matches:
                # TODO
                print 'matched task ' + self.matches[value]['name']

    def step(self):
        # a divide could potentially result in a parent or child with no instructions
        if self.sips == 0 or len(self.instructions) == 0:
            return

        ixn = self.instructions[self.heads['ip']]
        #print ixn, self.heads['rh'], self.heads['wh'], self.heads['fh']

        # if we hit the h_alloc'd undefined tail, reset ip to beginning
        if ixn == 'undefined':
            print self.instructions
            self.heads['ip'] = 0
            ixn = self.instructions[0]

        self.qreg = self.instructions[(self.heads['ip'] + 1) % len(self.instructions)]
        getattr(self, ixn)()

        # check in case dividing ruined the parents memory
        if len(self.instructions) != 0:
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

    def push(self):
        self.stacks[self.active_stack].append(self.regs[self.get_reg()])

        # they say they limit the depth of the stack to 10, but only for practical reasons
        if len(self.stacks[self.active_stack]) > 10:
            self.stacks[self.active_stack].pop(0)

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

    def sub(self):
        # python handles modulo of negative numbers correctly
        self.regs[self.get_reg()] = (self.regs['cx'] - self.regs['bx']) % (2 ** 32)

    def nand(self):
        self.regs[self.get_reg()] = ~(self.regs['bx']  & self.regs['cx'])

    def IO(self):
        self.output(self.get_reg())
        self.regs[self.get_reg()] = self.input_cycle.next()

    # TODO: this is pretty underspecified how much memory is actually allocated. it says "as much as they can". is this
    # based on energy? what happens if write head goes too far? should it wrap around?
    def h_alloc(self):
        self.instructions += ['undefined'] * 100

    def h_divide(self):


        # XXX if write head somehow wrapped around, there's overlap, but who knows how to handle it...
        if self.heads['rh'] > self.heads['wh']:
            child_instructions = self.instructions[self.heads['wh']:self.heads['rh']]
        else:
            child_instructions = self.instructions[self.heads['rh']:self.heads['wh']]

        # unspecified, but get rid of all undefined's caused by h-alloc
        child_instructions = filter(lambda x: x != 'undefined', child_instructions)
        self.instructions = filter(lambda x: x != 'undefined', self.instructions[:self.heads['rh']])

        # XXX: more unspecified
        self.heads['rh'] = self.heads['wh'] = self.heads['fh'] = 0
        # XXX XXX XXX what happens if the divide cuts off where the parent's head is? for now just do this
        # -1 so that we increment to instruction 0 at the end of the step
        self.heads['ip'] = -1

        if len(child_instructions) != 0 and random() < frameshift_rate:
            if random() < .5:
                del child_instructions[randint(0,len(child_instructions) - 1)]
            else:
                new_location = randint(0, len(child_instructions))
                new_instruction = choice(instruction_set)
                child_instructions.insert(new_location, new_instruction)

        # the child clobbers whomever is originally at this location
        child_x = (self.x + randint(-1, 1)) % lattice_dimension
        child_y = (self.y + randint(-1, 1)) % lattice_dimension
        child = Organism(self.lattice, child_instructions, child_x, child_y)
        print self.instructions, child_instructions

        # "kill" the previous organism at this location
        lattice[child_y][child_x] = child

    def h_copy(self):
        print len(self.instructions), self.heads['wh'], self.heads['fh']
        if random() < point_mutation_rate:
            self.instructions[self.heads['wh']] = choice(instruction_set)
        else:
            self.instructions[self.heads['wh']] = self.instructions[self.heads['rh']]

        # unspecified whether this hsould use the "mutated" value. Assume it shouldn't, to prevent breaking replication
        # also unspecified, but we limit this to 10 (if-label then can't have a template longer than 10)
        self.recent_copies.append(self.instructions[self.heads['rh']])
        if len(self.recent_copies) > 10:
            self.recent_copies.pop(0)

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

        # unspecified what should happen if template not found
        self.regs['bx'] = self.regs['cx'] = 0
        self.heads['fh'] = (self.heads['ip'] + 1) % len(self.instructions)

    def mov_head(self):
        self.heads[self.resolve_head()] = self.heads['fh']
        # handle the fact that "step" is about to advance ip by 1
        if self.resolve_head() == 'ip':
            self.heads['ip'] -= 1

    def jmp_head(self):
        # wrap around
        self.heads[self.resolve_head()] = (self.heads[self.resolve_head()] + self.regs['cx']) % len(self.instructions)

        # handle the fact that "step" is about to advance ip by 1
        if self.resolve_head() == 'ip':
            self.heads['ip'] -= 1

    def get_head(self):
        self.regs['cx'] = self.heads[self.resolve_head()]

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

rounds = 0
while True:
    # how exactly to allocate SIPs is somewhat unclear. We decided on giving each organism a SIP amount
    # equal to its computational merit (based on tasks completed) * genome_length
    for i in range(lattice_dimension):
        for j in range(lattice_dimension):
            lattice[i][j].sips += lattice[i][j].initial_length * lattice[i][j].computational_merit

    # flatten our 2D array and sort based on SIP
    organisms = [x for sublist in lattice for x in sublist]
    organisms.sort(lambda x, y: y.sips - x.sips)

    # give an average of thirty (default) instructions per organism. this is a single update timeslice
    for i in range(lattice_dimension ** 2 * avg_ixn_per_update):
        # use stochastic update to choose which organism to run an update. see
        # http://en.wikipedia.org/wiki/Fitness_proportionate_selection#Java_-_stochastic_acceptance_O.281.29_version
        while True:
            chosen = randint(0, len(organisms) - 1)
            max_sip = organisms[0].sips
            # apply a step to this organism
            if (float(organisms[chosen].sips) / max_sip >= random()):
                organisms[chosen].step()
                # fix the organisms order in the list
                while chosen + 1 < len(organisms) and organisms[chosen].sips < organisms[chosen+1].sips:
                    organisms[chosen], organisms[chosen+1] = organisms[chosen+1], organisms[chosen]
                    chosen += 1
                break
    print 'done with time slice ' + str(rounds)
    rounds += 1
