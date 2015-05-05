//bpu.rs - defines the functionality of a biological processing unit


//The Tape for a child can only be at most 2 x the parents
const OFFSPRING_MAX_GROWTH : i32 = 2;
//Any tape can be atmost 2048 at any time
const MAX_TAPE_SIZE : i32 = 2048;
//The registers which exist on our BPU
#[deriving(Ord)]
enum Register {
    //AX register
    AX,
    //BX register, our default register
    BX,
    //CX register
    CX
}

//The various heads which shift through our tape
#[deriving(Ord)]
enum Head {
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
    fn getComplement(&self) -> Register {
        match *self {
            AX => BX,
            BX => CX,
            CX => AX
        }
    }
    //Maps the active register onto a given head
    fn resolveHead(&self) -> Head {
        match *self {
            AX => IP,
            BX => RH,
            CX => WH
        }
    }
}

//The InstructionSet which is run by our BPU
//NOTE: CURR_REG refers to the currently active register, COMP_REG refers to its complement
#[deriving(Ord, Rand)]
enum InstructionSet {
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
    //Checks if the following template is a subset of complement template
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
    //A blank instruction, used for uninitialized memory
    BLANK

}
