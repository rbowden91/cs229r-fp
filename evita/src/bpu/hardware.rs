//hardware.rs - defines the functionality of a biological processing unit
use rand::{Rng, sample, thread_rng, random, Rand};
use bpu::constants;
use std::cmp::min;
//The registers which exist on our BPU
#[derive(PartialOrd, PartialEq, Eq, Ord, Clone, Copy)]
pub enum Register {
    //AX register
    AX,
    //BX register, our default register
    BX,
    //CX register
    CX
}


//The various heads which shift through our tape
#[derive(PartialOrd, PartialEq, Eq, Ord)]
pub enum Head {
    //Instruction Pointer
    IP,
    //Read head (i.e. where on the tape are we reading?)
    RH,
    //Write head (i.e. where on the tap are we writing?)
    WH,
    //Floating head, used for copying the state of the tape
    FH
}


//Implementation of convenience methods for registers
impl Register {
    //Matches each register to their complement in Evita
    pub fn get_complement(&self) -> Register {
        match *self {
            Register::AX => Register::BX,
            Register::BX => Register::CX,
            Register::CX => Register::AX
        }
    }
    //Maps the active register onto a given head
    pub fn resolve_head(&self) -> Head {
        match *self {
            Register::AX => Head::IP,
            Register::BX => Head::RH,
            Register::CX => Head::WH
        }
    }
}

//The InstructionSet which is run by our BPU
//NOTE: CURR_REG refers to the currently active register, COMP_REG refers to its complement
#[derive(PartialOrd, PartialEq, Eq, Ord, Clone, Copy)]
pub enum InstructionSet {
    //A NO-OP which sets the target register to the value it contains
    NOP(Register),
    //Conditionally skips the next instruction if CURR_REG == COMP_REG
    IFNEQU,
    //Conditionally skips the next instruction if CURR_REG < COMP_REG
    IFLESS,
    //Pops a value off one of the internal stacks
    POP,
    //Pushes a value from the register into the internal stack
    PUSH,
    //Swaps value of CURR_REG with COMP_REG
    SWAP,
    //Swaps the currently active stack
    SWAPSTK,
    //Increments the value of CURR_REG
    INC,
    //Decrements the value of CURR_REG
    DEC,
    //Computes CURR_REG = BX + CX
    ADD,
    //Computes CURR_REG = BX + CX
    SUB,
    //Computes CURR_REG >>= 1
    RSHIFT,
    //Computes CURR_REG <<= 1
    LSHIFT,
    //Computes CURR_REG = ~(a & b)
    NAND,
    //sets FH to a position equal to COMP_REG % MEM_SIZE
    SETFLOW,
    //Moves the currently selected head to the location of FH
    MOVHEAD,
    //sets the currently selected head to CX % MEM_SIZE
    JMPHEAD,
    //sets CX to be equal to the position of the current head
    GETHEAD,
    //Reads the following template and computes its complement
    //Checks if this complement is part of the most recently copied data
    //If it is, we execute the next instruction after the template
    IFLABEL,
    //Outputs CURR_REG for checking, then sets CURR_REG to be one of our inputs
    IO,
    //Allocates memory on the tape for a child, according to size limits
    HALLOC,
    //Splits the current organisms tape into three regions
    //[0x0, RH) becomes the parents tape.
    //[RH, WH) becomes the child's tape (we use [WH, RH) if WH < RH)
    //[max(RH, WH), END] is erased
    //We clear all blank instructions as well
    //Frameshift mutation may occur during this process
    HDIVIDE,
    //Copies the instruction at RH to WH
    //Can have point mutation occur
    HCOPY,
    //Reads the following NOP template
    //Sets Flow-head to the beginning of the template
    //NOTE : If there is no template, goes to the next instruction
    //BX becomes the distance from the current IP to the complement
    //NOTE: If no template, bx becomes 0
    //CX becomes the size of the complement template
    //NOTE: If no template, cx becomes 0
    //This function scans through all of memory to find a complement
    HSEARCH,
    LEARN
}
//Listing of all instructions for iteration
static INSTRUCTIONS: [InstructionSet; 27] = [
    InstructionSet::NOP(Register::AX),
    InstructionSet::NOP(Register::BX),
    InstructionSet::NOP(Register::CX),
    InstructionSet::IFNEQU,
    InstructionSet::IFLESS,
    InstructionSet::POP,
    InstructionSet::PUSH,
    InstructionSet::SWAP,
    InstructionSet::SWAPSTK,
    InstructionSet::INC,
    InstructionSet::DEC,
    InstructionSet::ADD,
    InstructionSet::SUB,
    InstructionSet::RSHIFT,
    InstructionSet::LSHIFT,
    InstructionSet::NAND,
    InstructionSet::SETFLOW,
    InstructionSet::MOVHEAD,
    InstructionSet::JMPHEAD,
    InstructionSet::GETHEAD,
    InstructionSet::IFLABEL,
    InstructionSet::IO,
    InstructionSet::HALLOC,
    InstructionSet::HDIVIDE,
    InstructionSet::HCOPY,
    InstructionSet::HSEARCH,
    InstructionSet::LEARN
];


impl Rand for InstructionSet {
    fn rand<R>(rng: &mut R) -> InstructionSet where R : Rng {
        let select = sample(rng, INSTRUCTIONS.iter(), 1);
        select[0].clone()
    }
}
//Represents the memory in which our instructions lives
pub struct Memory {
    //Our actual memory
    tape : Vec<Option<InstructionSet>>,
}


impl Memory {
    //Creates a new empty memory
    pub fn new() -> Memory {
        Memory{tape : Vec::new()}
    }

    //Creates a tape by coping a subsection of an existing memory
    pub fn with_subsection<'a>(source : &'a Memory, start : i32, end: i32, shift : bool) -> Option<Memory> {
        //if [start, end) is not a valid subselection of the Memory, return None
        if start > end || (end as usize) > source.tape.len() {
           return None;
        }
        //Calculate the length of our new Memory
        let nlen : usize = (end - start) as usize;
        //allocate our new tape
        let mut ntape : Vec<Option<InstructionSet>> = Vec::with_capacity(nlen);
        for idx in start .. end {
            //push each a copy of each element to our new tape
            ntape.push(source.tape[idx as usize]);
        }
        Some(Memory{tape : ntape})
   }

    //Grabs the value at a given position in the tape
    pub fn get(&self, idx : usize) -> Option<InstructionSet>{
        self.tape.get(idx).unwrap_or(&None).clone()
    }

    //Puts a specific value into the array, may mutate if the mutate flag is set
    pub fn put(&mut self, instr : InstructionSet, idx : usize, mutate : bool) {
        if(idx < self.tape.len()){
            if mutate && random::<f64>() < constants::POINT_MUTATION_RATE {
                let mut rng = thread_rng();
                self.tape[idx] = Some(random());
            }
            self.tape[idx] = Some(instr);
        }
    }

    //Get the length of our memory
    pub fn memsize(&self) -> usize{
        self.tape.len()
    }

    //allocates more space in our memory, filled with nones
    pub fn alloc(&mut self){
        let nsize = min::<usize>(constants::MAX_TAPE_SIZE, constants::OFFSPRING_MAX_GROWTH * self.tape.len());
        while self.tape.len() < nsize {
            self.tape.push(None);
        }
    }


}
//Register representing our actual
struct BPU {
    //The memory on which we operate
    mem : Memory,
    //Our registers and current register information
    curr_reg : InstructionSet,
    ax : i32,
    bx : i32,
    cx : i32,
    //Our various heads for reading and writing
    //Floating head for copying
    fh : i32,
    //Our writing head
    wh : i32,
    //Our reading head
    rh : i32,
    //Our Instruction Pointer
    ip : i32,
}
