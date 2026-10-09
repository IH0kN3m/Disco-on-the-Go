// Original ARM64 entry shims for the Darwin calling convention.
.text
.p2align 2
.global DiscoDarwinSnprintf
.hidden DiscoDarwinSnprintf
DiscoDarwinSnprintf:
    mov x3, sp
    b DiscoSnprintf
.global DiscoDarwinSprintf
.hidden DiscoDarwinSprintf
DiscoDarwinSprintf:
    mov x2, sp
    b DiscoSprintf
.global DiscoDarwinOpen
.hidden DiscoDarwinOpen
DiscoDarwinOpen:
    mov x2, sp
    b DiscoOpen
.global DiscoDarwinStackProbe
.hidden DiscoDarwinStackProbe
DiscoDarwinStackProbe:
    // Darwin passes the byte count in x9; preserve all general registers.
    stp x10, x11, [sp, #-16]!
    add x10, sp, #16
    mov x11, x9
1:
    cmp x11, #4096
    b.lo 2f
    sub x10, x10, #4096
    ldr xzr, [x10]
    sub x11, x11, #4096
    b 1b
2:
    sub x10, x10, x11
    ldr xzr, [x10]
    ldp x10, x11, [sp], #16
    ret
// The only supplied _setjmp use spills callee-saved registers for conservative
// GC scanning. No longjmp import exists; this does not implement nonlocal jumps.
.global DiscoGCSpill
.hidden DiscoGCSpill
DiscoGCSpill:
    stp x19, x20, [x0]
    stp x21, x22, [x0, #16]
    stp x23, x24, [x0, #32]
    stp x25, x26, [x0, #48]
    stp x27, x28, [x0, #64]
    stp x29, x30, [x0, #80]
    mov x16, sp
    str x16, [x0, #96]
    stp d8, d9, [x0, #104]
    stp d10, d11, [x0, #120]
    stp d12, d13, [x0, #136]
    stp d14, d15, [x0, #152]
    mov w0, #0
    ret
.section .note.GNU-stack,"",%progbits
