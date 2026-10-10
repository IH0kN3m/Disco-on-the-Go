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
.global DiscoDarwinPrintf
.hidden DiscoDarwinPrintf
DiscoDarwinPrintf:
    mov x1, sp
    b DiscoPrintf
.global DiscoDarwinFcntl
.hidden DiscoDarwinFcntl
DiscoDarwinFcntl:
    mov x2, sp
    b DiscoFcntl
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
// Full plugin setjmp storage is private to this adapter: 168 register bytes,
// 8 Linux signal-mask bytes and an ownership cookie in Darwin's 192-byte buffer.
.global DiscoPluginSetjmp
.hidden DiscoPluginSetjmp
DiscoPluginSetjmp:
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
    mov x19, x0
    mov x16, #0x4a50
    str x16, [x19, #176]
    add x2, x19, #168
    mov x0, #2
    mov x1, #0
    mov x3, #8
    mov x8, #135 // Linux ARM64 rt_sigprocmask
    svc #0
    cbnz x0, 3f
    ldr x19, [x19]
    ret
.global DiscoPluginLongjmp
.hidden DiscoPluginLongjmp
DiscoPluginLongjmp:
    mov x19, x0
    mov w20, w1
    ldr x16, [x19, #176]
    mov x17, #0x4a50
    cmp x16, x17
    b.ne 3f
    add x1, x19, #168
    mov x0, #2
    mov x2, #0
    mov x3, #8
    mov x8, #135
    svc #0
    cbnz x0, 3f
    cmp w20, #0
    csinc w0, w20, wzr, ne
    mov x16, x19
    ldp x19, x20, [x16]
    ldp x21, x22, [x16, #16]
    ldp x23, x24, [x16, #32]
    ldp x25, x26, [x16, #48]
    ldp x27, x28, [x16, #64]
    ldp x29, x30, [x16, #80]
    ldp d8, d9, [x16, #104]
    ldp d10, d11, [x16, #120]
    ldp d12, d13, [x16, #136]
    ldp d14, d15, [x16, #152]
    ldr x16, [x16, #96]
    mov sp, x16
    ret
3:
    b abort
.section .note.GNU-stack,"",%progbits
