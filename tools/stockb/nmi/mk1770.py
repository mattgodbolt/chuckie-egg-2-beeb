s=open('nmi8271.6502').read()
s=s.replace('''\\ A background disc reader for the Model B's 8271, a prototype''','''\\ The same prototype for the Master 128's WD1770''',1)
s=s.replace('''fdc_status  = &FE80     ; read
fdc_command = &FE80     ; write
fdc_result  = &FE81     ; read
fdc_param   = &FE81     ; write
fdc_reset   = &FE82
fdc_data    = &FE84
''','''fdc_control = &FE24     ; Master: b0 drive 0, b1 drive 1, b2 not reset, b4 side, b5 single density
fdc_status  = &FE28     ; read (clears INTRQ)
fdc_command = &FE28     ; write
fdc_track   = &FE29
fdc_sector  = &FE2A
fdc_data    = &FE2B
CONTROL     = &25       ; drive 0, running, side 0, FM
''')
s=s.replace('''E_N = 1                 ; parameter count
E_P = 2                 ; 4 parameters''','''E_N = 1                 ; which of the four to write: b0 track, b1 sector, b2 data, b3 control
E_P = 2                 ; track register, sector register, data register, control latch''')
s=s.replace('"*RUN NMIT"','"*RUN NMIW"').replace('filename = "NMIT"','filename = "NMIW"')
s=s.replace('''    \\ Reset the 8271: the DFS may have left a head-unload count running.
    LDA #1 : STA fdc_reset
    LDX #20
.rwait DEX : BNE rwait
    STX fdc_reset
''','''    \\ Reset the 1770 (the latch's bit 2 low).
    LDA #CONTROL AND NOT(4) : STA fdc_control
    LDX #20
.rwait DEX : BNE rwait
    LDA #CONTROL : STA fdc_control
''')
old='''.nc LDA fdc_status : BMI busy
    LDY #E_VARIANT : LDA (entry),Y : LSR A : BCS from_nmi
    \\ No completion NMI handled (variants 0 and 2): the result is here, if
    \\ the command gives one (Specify and Write Special Register don't).
    LDA fdc_status : AND #&10 : BEQ got
    LDA fdc_result : JMP got
.from_nmi'''
assert old in s
s=s.replace(old,'''.nc LDA fdc_status : LSR A : BCS busy
    LDY #E_VARIANT : LDA (entry),Y : LSR A : BCS from_nmi
    \\ No completion NMI handled (variants 0 and 2): the status is the result,
    \\ and reading it drops INTRQ (and with it the NMI line).
    LDA fdc_status : JMP got
.from_nmi''')
a=s.index('''.got
    STA result
'''); b=s.index('.finished')
s=s[:a]+'''.got
    STA result
'''+s[b:]
a=s.index('\\ The command and its parameters'); b=s.index('\\ Copy the entry')
s=s[:a]+'''\\ The registers the entry names, then the command.
.issue
{
.wait_idle
    LDA fdc_status : LSR A : BCS wait_idle      ; busy
    LDA #0 : STA result
    LDY #E_N : LDA (entry),Y : STA mask
    LDY #E_P
    LSR mask : BCC no_track : LDA (entry),Y : STA fdc_track
.no_track
    INY : LSR mask : BCC no_sector : LDA (entry),Y : STA fdc_sector
.no_sector
    INY : LSR mask : BCC no_data : LDA (entry),Y : STA fdc_data
.no_data
    INY : LSR mask : BCC no_control : LDA (entry),Y : STA fdc_control
.no_control
    LDY #E_CMD : LDA (entry),Y : STA fdc_command
    RTS
}

'''+s[b:]
s=s.replace('''\\ Variant 0: nothing expected but the completion (Seek, Specify).''','''\\ Variant 0: nothing expected but the completion (Restore, Seek): INTRQ
\\ stays up until the foreground reads the status.''')
a=s.index('\\ Variant 1:'); b=s.index('\\ Variant 2:')
s=s[:a]+'''\\ Variant 1: the status register says which NMI this is (and reading it
\\ drops INTRQ). 4 + 4 + 2 + 2 + 2 + 4 + 4 + 6 + 2 + 6 = 36 cycles a data
\\ byte, plus 7 to take the NMI.
.h_status
    STA hs_restore+1 - h_status + NMI_AREA
    LDA fdc_status : LSR A : LSR A : BCC hs_complete    ; DRQ
    LDA fdc_data
.hs_dst STA &3000
    INC hs_dst+1 - h_status + NMI_AREA
.hs_restore LDA #0
    RTI
.hs_complete
    LDA fdc_status : STA nmi_result
    LDA #&FF : STA done
    BNE hs_restore

'''+s[b:]
s=s.replace('''\\ it turns itself into an RTI for the completion NMI, and the foreground
\\ reads the result.''','''\\ it turns itself into an RTI for the completion NMI (INTRQ), and the
\\ foreground reads the status, which drops INTRQ.''')
a=s.index('\\ Variant 3:'); b=s.index('.irq')
s=s[:a]+'''\\ Variant 3: as 1, carrying into the page, for multi-sector reads.
.h_multi
    STA hm_restore+1 - h_multi + NMI_AREA
    LDA fdc_status : LSR A : LSR A : BCC hm_complete
    LDA fdc_data
.hm_dst STA &3000
    INC hm_dst+1 - h_multi + NMI_AREA
    BNE hm_restore
    INC hm_dst+2 - h_multi + NMI_AREA
.hm_restore LDA #0
    RTI
.hm_complete
    LDA fdc_status : STA nmi_result
    LDA #&FF : STA done
    BNE hm_restore

'''+s[b:]
s=s.replace("delay = &7D\n","delay = &7D\nmask = &7E\n")
s=s.replace("; NMI handler: 0 RTI, 1 status check, 2 counting, 3 multi-page; +&80 retry while not ready","; NMI handler: 0 RTI, 1 status check, 2 counting, 3 multi-page")
s=s.replace("\\ The harness (nmi8271.mjs)","\\ The harness (harness.mjs)")
open('nmi1770.6502','w').write(s)
