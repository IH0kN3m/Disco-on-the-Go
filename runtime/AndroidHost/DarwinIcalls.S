// Apple ARM64 packs scalar stack arguments; AAPCS64 gives each an 8-byte slot.
// TextGenerator's register arguments agree. Repack only its nine stack values.
.text
.p2align 2
.global DiscoTextPopulateBridge
.hidden DiscoTextPopulateBridge
.type DiscoTextPopulateBridge,%function
DiscoTextPopulateBridge:
    .cfi_startproc
    mov x9, sp
    sub sp, sp, #96
    .cfi_def_cfa_offset 96
    stp x29, x30, [sp, #80]
    .cfi_offset 29, -16
    .cfi_offset 30, -8
    ldr w10, [x9]
    str w10, [sp]
    ldr w10, [x9, #4]
    str w10, [sp, #8]
    ldr w10, [x9, #8]
    str w10, [sp, #16]
    ldr w10, [x9, #12]
    str w10, [sp, #24]
    ldrb w10, [x9, #16]
    strb w10, [sp, #32]
    ldr w10, [x9, #20]
    str w10, [sp, #40]
    ldrb w10, [x9, #24]
    strb w10, [sp, #48]
    ldrb w10, [x9, #25]
    strb w10, [sp, #56]
    ldr x10, [x9, #32]
    str x10, [sp, #64]
    adrp x16, DiscoTextPopulateTarget
    ldr x16, [x16, :lo12:DiscoTextPopulateTarget]
    blr x16
    ldp x29, x30, [sp, #80]
    add sp, sp, #96
    .cfi_def_cfa_offset 0
    ret
    .cfi_endproc
.size DiscoTextPopulateBridge,.-DiscoTextPopulateBridge

// Synthetic caller used only by the content-free ABI check in the probe.
.global DiscoTextPopulateTestCaller
.hidden DiscoTextPopulateTestCaller
.type DiscoTextPopulateTestCaller,%function
DiscoTextPopulateTestCaller:
    sub sp, sp, #64
    stp x29, x30, [sp, #48]
    str x0, [sp, #32]
    mov w9, #7
    str w9, [sp]
    mov w9, #8
    str w9, [sp, #4]
    mov w9, #9
    str w9, [sp, #8]
    mov w9, #10
    str w9, [sp, #12]
    mov w9, #1
    strb w9, [sp, #16]
    mov w9, #11
    str w9, [sp, #20]
    strb wzr, [sp, #24]
    mov w9, #1
    strb w9, [sp, #25]
    mov x0, #1
    mov x1, #2
    mov x2, #3
    mov x3, #4
    mov w4, #5
    mov w5, #6
    mov w6, #1
    mov w7, #0
    fmov s0, #1.0
    fmov s1, #2.0
    fmov s2, #3.0
    fmov s3, #4.0
    fmov s4, #5.0
    fmov s5, #6.0
    bl DiscoTextPopulateBridge
    ldp x29, x30, [sp, #48]
    add sp, sp, #64
    ret
.size DiscoTextPopulateTestCaller,.-DiscoTextPopulateTestCaller
.bss
.balign 8
.global DiscoTextPopulateTarget
.hidden DiscoTextPopulateTarget
DiscoTextPopulateTarget: .zero 8
.section .note.GNU-stack,"",%progbits
