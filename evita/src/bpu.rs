//bpu.rs - defines the functionality of a biological processing unit

//The registers which exist on our BPU
enum Register {
    //AX register
    AX,
    //BX register, our default register
    BX,
    //CX register
    CX
}

//The various heads which shift through our tape
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
enum InstructionSet {
    //A NO-OP which sets the target register to the value it contains
    NOP(Register),
    //Conditionally jumps if CURR_REG != COMP_REG
    IFNEQU,
    //Conditionally jumps if CURR_REG < COMP_REG
    IFLESS,



}
