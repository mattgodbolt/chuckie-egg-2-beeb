# Background disc reads with our own NMI driver: 8271 (Model B) and WD1770 (Master)

Prototype, measured in jsbeeb (jsbeeb-mcp 4.0.1, jsbeeb 2.3.1, the same `intel-fdc.js` / `wd-fdc.js` /
`disc-drive.js` as jsbeeb HEAD). Everything is in this directory (tools/stockb/nmi), run from it with build.sh first.

## Result

It works on both machines, from one binary. After start-up the program never calls the OS or the DFS. It
owns IRQ1V (counting VSyncs, optionally User VIA T1) and &0D00 (the NMI handler), and it drives the
controller directly. A foreground loop counts while sectors arrive. Every sector read checked out against
the tagged disc (each byte pair = track, sector), and every VSync was taken during reads (counts always
match elapsed/40,000 cycles). So did every 1ms T1 IRQ (563 of 564 expected).

`driver.6502` is the deliverable: one driver, with the FDC picked at start-up by `fdc_init` (A = 0 for the
8271, 1 for the 1770; MENU can pass it, since OSBYTE 0 with X=1 returns X=1 on a B and 3 on a Master).
`dtest.6502` runs it on both models from the same disc (`dtest.mjs`, output `dtest.out`):

| request | B (8271) | Master (1770) |
|---|---|---|
| first read, 1/0 (cold) | 236ms | 1300ms (6-rev spin-up) |
| 1/1, 1/2, 1/3 back to back | 19.8ms each | 19.8ms each |
| 5/7, 3/2, 20/9 | 279, 101, 539ms (24ms steps) | 79, 101, 139ms (6ms steps) |
| after 3s idle **with** `fdc_keepalive` each second | 28ms | 29ms |
| after 3s idle without | 208ms (head stays loaded anyway) | 1525ms (motor stopped, spin-up again) |
| `fdc_spinup`, 1s, then read | 107ms | 224ms |

Size: `fdc_init` to the end of the NMI template is 445 bytes, more than the 250 that stock-b.md 2.1 guessed.
It could be trimmed: the 8271 set-up table, and the spin-up/keepalive entries if they aren't wanted.

## The NMI handler (cycles counted, Tom Seddon's self-modifying save of A)

The one in the driver (the "counting" handler) is the same on both chips except for the data register's address
(&FE84 or &FE2B), which `fdc_init` patches:

```
&0D00  STA restore+1   4    ; A saved in the LDA # below: no zero-page byte
       LDA &FE84       4    ; (&FE2B on the 1770)
dst    STA &3000       4    ; page patched by fdc_read; low byte from 0
       INC dst+1       6
       BEQ last        2    ; the 256th byte
restore LDA #0         2
       RTI             6    ; = 28 cycles, + 7 to take the NMI = 35 of the 128 between FM bytes (27%)
last   LDA #&40        ; RTI: the completion NMI then does nothing, and
       STA &0D00       ; the foreground's poll reads the result, which drops
       BNE restore     ; the controller's interrupt line
```

One 256-byte sector per command lets the handler skip the page carry (scarybeasts' advice). I also measured
a variant that reads the status register on every NMI to tell data from completion: 8271 `STA r+1 : LDA &FE80 :
AND #4 : BEQ done : LDA &FE84 : STA dst : INC dst+1 : r LDA #0 : RTI`, 34 cycles + 7. On the 1770 it is
`LDA &FE28 : LSR : LSR : BCC done` (DRQ is bit 1), 36 + 7. Don't test the 8271's busy bit (bit 7) instead:
the 8271's microcode raises INT before it clears busy, so on real hardware a completion NMI can still see busy.

Measured CPU lost to the foreground (busy-loop counter against elapsed cycles):

| | 8271 | 1770 |
|---|---|---|
| counting handler, sector after sector (19.2ms each) | 24.0% | 23.9% |
| status-checking handler | 28.0% | 29.3% |
| whole read incl. ~100ms rotational wait | ~5% | ~5% |

## Measurements: 8271, Model B (`probe2.mjs` -> `probe2.out`, prototype `nmi8271.6502`)

Settings: DFS's own Specify, step &0C, settle &0A, head load 8 (64ms), unload &F (never).

- **Sector after sector on one track**: 19.2ms each (first byte 2.7ms after the command), so ten single-sector
  commands read a whole track in one revolution. The foreground issues the next command within the 27-byte
  gap3 (1.7ms). On a real 8271, accepting a command and 3 parameters takes ~0.2-0.3ms (jsbeeb accepts them
  instantly), which still fits.
- **Multi-sector Read Data (&53, count n)**: also streams. x10 = 234ms, with 39ms of it latency (~19.5ms a
  sector). Asking past sector 9 gives &18 (sector not found) after ~3 revolutions (636ms).
- **Rotational latency**: 12-192ms in 20ms steps depending on when the command lands. jsbeeb is deterministic
  (10 frames to a revolution exactly). On real hardware it is uniform over 0-200ms.
- **Seeks** (head loaded): n x 24ms + 20ms settle at step &0C, n x 6ms + 20ms at step 3. Measured exactly:
  1->10 = 236ms, 10->0 = 260ms, 39->0 = 956ms (step &0C). At step 3: 1->39 = 248ms. A Read Data on another
  track seeks by itself, at the same cost (10/4 from track 1: 380ms all in = 9 steps + settle + rotation).
- **Cold start**: 281ms from a deselected drive (spin-up, then the B's ready latch). After an auto-unload
  (count 12 revs, 3s idle) a read takes 476ms. After WSR &23=0 (deselect) it takes 300ms at 0.1s and 426ms at 5s.
- **Pre-spin**: WSR &23=&48 (select drive 0 + load head), then a read 1s later: 47ms.
- **Head kept loaded** (&F8), read after 5s idle: 109ms (rotation only).

### 8271 facts the driver depends on

- **Command byte**: bits 7-6 select the drive: &40 drive 0, &80 drive 1. Bits 5-0 are the command, and their
  low 2 bits give the parameter count. Read Data (variable size) &53, Seek &69, Specify &75, Write Special
  Register &7A, Read Drive Status &6C, all for drive 0. **A command with select bits 00 (e.g. Specify &35)
  deselects the drive**, which stops the motor and unloads the head. Side 1 is bit 5 of the drive output
  register (WSR &23).
- **Mode register**: WSR &17 = &C1. Bit 0 (no DMA) is required, or every byte is a late-DMA error &0A.
  Bad-track registers: Specify &10/&18 = &FF,&FF,track. jsbeeb powers on with them at 0, and then every
  seek goes 2 tracks too far.
- **Ready on a B**: the drive becomes ready on the 2nd index pulse after it is selected. The first command
  after a cold start returns &10 (not ready). The 8271 **latches** not-ready, and only Read Drive Status
  (&6C) clears the latch. So the retry is: Read Drive Status, then reissue. Retrying alone loops forever.
- **Keeping the head loaded**: the Specify unload nibble &F means it is never unloaded. To let it unload,
  either Specify a count of 1-E revolutions (counted from the end of each command) or use WSR &23 = 0 to
  unload at once. **Never use count 0 on a B**: it unloads after every command, including the not-ready
  failure, so a cold read never becomes ready (measured: it hangs for good).
- **Completion**: an INT (NMI) with the result in &FE81. Reading the result drops INT. Specify and WSR give
  no NMI, and writing parameters clears "result ready", so poll busy for those. The 6502's NMI is
  edge-triggered, so a completion INT left up would mask the next command's data NMIs. Always read the
  result before issuing the next command.
- **Result codes** (mask &1E): 00 ok, 08 clock error, 0A late DMA, 0C ID CRC, 0E data CRC, 10 not ready,
  12 write protect, 18 sector not found. &20 = deleted data.

## Measurements: WD1770, Master 128 (`probew.mjs` -> `probew.out`, prototype `nmi1770.6502`)

Control latch &FE24 = &25 (bit 0 drive 0, bit 2 not-reset, bit 4 side, bit 5 single density). Registers
&FE28 status/command, &FE29 track, &FE2A sector, &FE2B data.

- **Sector after sector**: 19.2ms each (first byte 2.5ms after the command), as on the 8271.
- **Seeks** (motor on): n x 6ms at rate 0, n x 30ms at rate 3, with no settle unless E is set. The 1770
  can't seek within a read, so the driver issues Seek (&10+rate, target in the data register), then Read
  Sector (&80) when the seek completes. Its track register must match the disc's ID.
- **Cold start**: Restore with spin-up wait took 1082ms (6 index pulses). The first read after a reset took
  1.3s, and after the motor stopped ~1.5s.
- **Motor auto-off**: after 9 idle index pulses (1.8s). Idle 1.5s then read: 209ms. Idle 2.5s: 1503ms.
- **Keeping it spinning**: Force Interrupt &D0 while idle restarts the 9-revolution count and gives no INTRQ
  (so no NMI). &D0 every 1.4s for 5.6s, then read: 108ms. `fdc_keepalive` does this, once a second from the
  main loop. &D0 also starts a stopped motor without waiting, so it doubles as `fdc_spinup`: idle 5s, &D0,
  1s, read = 164ms. **Keeping it spinning for the whole game is a choice**, as on the 8271: the drive's
  noise and wear, for loads ~1.3s quicker.
- **h bit** (&88, no spin-up wait) from a stopped motor: 78ms in jsbeeb, which reads fine at part speed. On
  real hardware the first sector may fail until the disc is up to speed, so retry on an error.
- **Multi-sector Read (&90)**: streams one revolution, then doesn't stop at the end of the track. It runs
  until record-not-found (&10) after 5-6 revolutions: 1080-1280ms. Use single sectors (as the driver
  does), or write &D0 after the last wanted byte (but then the last sector's CRC isn't checked).
- **Completion**: INTRQ, 32us after the end, ORed with DRQ onto NMI. Reading the status register drops it;
  writing the next command does too. Error bits (mask &1C): 10 record not found, 08 CRC, 04 lost data.

## Interrupts: VSync, and the game's palette-split T1

The game's split timer is the **User VIA's** T1 (irq.6502), not the System VIA's. NMIs can't be masked, so
a read never loses data to the IRQ handler. The cost runs the other way: an NMI that lands just before or
during the IRQ handler delays the split's writes by up to one handler's length. `probe3*.mjs` ran a 1ms
free-running User VIA T1 and recorded how late its handler read the counter:

| | idle | during reads |
|---|---|---|
| B, worst latency | 32us | 43us |
| Master, worst latency | 32us | 52us |

No IRQs were lost: 563 of 564 T1 IRQs and all VSyncs were taken. The split's 8 ULA writes have about 2us to
spare (stock-b.md), and an NMI handler is 17-21us. So during a load, a split will land a line late on any
frame where a data byte arrives just before or during its writes. Data bytes come every 64us for 16ms of each
20ms sector, so that is most frames while a read is under way. Expect a band edge to flicker for the length
of a load (one sector is about one frame). Nothing short of not reading during the split avoids it, because
the disc's rotation isn't locked to the frame.

## How faithful jsbeeb is, and what may differ on real hardware

jsbeeb's 8271 is a translation of beebjit's, which follows Chris Evans's reverse engineering of the 8271's
microcode. Byte timing (one NMI every 64us), non-DMA mode, late-data detection (&0A), result codes, the
drive-select and drive-output bits, the ready latch, the unload count in index pulses and the step, settle
and load units (2ms/2ms/8ms) are all modelled.

Gaps and guesses:

1. **Command and parameter acceptance is instant.** "Command full" and "parameter full" are never set. A
   real 8271 takes 27-211us per byte. The driver polls them anyway.
2. **The order at completion is instant.** In jsbeeb, busy clears in the same step that INT rises. On a real
   chip it clears a few microseconds later, which is why the handlers test the data-request bit or count bytes.
3. **Spin-up and ready**: jsbeeb models spin-up as an exponential with a 150ms time constant, and the B's
   ready logic as the 2nd index pulse after selection (262ms timeout). Both are recent (jsbeeb #1162) and
   only partly measured. **beebjit differs here**: it reports ready as soon as the drive is selected and
   spinning, with instant spin-up, so a cold 8271 read there costs only the 64ms head load, never a not-ready.
4. **Perfect discs**: no CRC errors, no weak bits, and reading works straight after a seek with no settle.
   Discs converted from SSD have no track-to-track skew (sector 0 always follows the index). A disc formatted
   or duplicated on real hardware may have skew, which changes the latency of crossing a track.
5. **Rotation is locked to emulated time**, so latencies repeat exactly. Real latency is random, mean 100ms.
6. **1770 settle bit E**: jsbeeb applies its 15ms settle only after a spin-up. A real 1770 always delays
   (15-30ms) with E=1. On real hardware use E=1 after a seek, and E=0 when reading the next sector on the
   same track.
7. **1770 motor-off after 9 revolutions**: jsbeeb notes that sources disagree (9 or 10). That &D0 in idle
   restarts the count comes from scarybeasts' tests on a 1772.
8. **Master FDC bus speed**: jsbeeb treats &FE24-&FE2B as 2MHz accesses. If a real Master stretches them to
   1MHz, each handler costs 1-2 cycles more per access.
9. **Step rates**: jsbeeb accepts any step rate, so a real drive may need the slower rates. 6ms on the 1770
   and step 3 on the 8271 work in the emulator. The driver keeps the DFS's &0C on the 8271 and rate 0 on the 1770.
   On a Master, use the configured step rate (MENU can read it).

## Files

- `driver.6502`: the unified driver (below). `dtest.6502` + `dtest.mjs`: the test on both machines (`dtest.out`).
- `nmi8271.6502`, `nmi1770.6502`: the measuring prototypes, a queue of raw controller commands with four NMI
  handler variants. `harness.mjs` runs a queue and times it with breakpoints. `probe1/2/3.mjs` (8271) and
  `probew.mjs`, `probe3w.mjs` (1770), with their `.out` files.
- `build.sh`: baron 0.5.1, then `mkimg.py`, which pads each SSD to 40 tracks with tracks 1-39 tagged.

## driver.6502

```
\ ***************************************************************************
\ A background sector reader for the Model B's 8271 and the Master's WD1770:
\ one driver, the controller picked at start-up (MENU, with the OS alive,
\ can tell: OSBYTE 0 gives X = 1 on a B, 3 on a Master).
\
\   fdc_init      A = FDC_8271 or FDC_1770. Owns &0D00 from now on.
\   fdc_read      A = track, X = sector, Y = destination page: starts reading
\                 one 256-byte sector and returns at once.
\   fdc_poll      C set while the read is under way; then C clear and A = 0
\                 (read) or the controller's error bits. Call it as often
\                 as you like (main loop or VSync): it is where a 1770 seek
\                 turns into the read, and an 8271 not-ready is retried.
\   fdc_keepalive Call about once a second when idle: keeps a 1770's motor
\                 from stopping (it stops after 9 idle revolutions). The
\                 8271's head stays loaded by itself (Specify, unload &F).
\   fdc_spinup    Starts the motor ahead of a read (when Harry nears an exit).
\
\ The NMI handler is the same on both, but for the data register's address:
\ 4 (STA abs) + 4 (LDA data) + 4 (STA abs) + 6 (INC abs) + 2 (BEQ) + 2 (LDA #)
\ + 6 (RTI) = 28 cycles a byte, plus 7 to take the NMI: 35 of the 128
\ between bytes (FM, 64us), 27%. The 256th byte turns it into an RTI, so the
\ completion NMI does nothing, and fdc_poll reads the result, which drops
\ the controller's interrupt (8271 result register, 1770 status register).
\ ***************************************************************************

FDC_8271 = 0
FDC_1770 = 1
NMI_AREA = &0D00
RTI_OP = &40
STA_ABS = &8D

\ 8271 (Model B)
I_STATUS = &FE80 : I_COMMAND = &FE80 : I_RESULT = &FE81 : I_PARAM = &FE81
I_RESET = &FE82 : I_DATA = &FE84
I_STEP = &0C            ; the DFS's own: 24ms a step on jsbeeb (units of 2ms)
I_SETTLE = &0A          ; 20ms
I_LOAD = &F8            ; never unload; 64ms head load
\ WD1770 (Master)
W_CONTROL = &FE24 : W_STATUS = &FE28 : W_COMMAND = &FE28
W_TRACK = &FE29 : W_SECTOR = &FE2A : W_DATA = &FE2B
W_LATCH = &25           ; drive 0, not reset, side 0, single density
W_RATE = 0              ; 6ms steps (r1 r0)

\ Driver state, which must survive the game's death path (fixed zero page
\ or LowState in the game).
fdc_type  = &60
fdc_state = &61         ; 0 idle, 1 seeking (1770), 2 reading
fdc_track = &62         ; wanted track, sector, page
fdc_sect  = &63
fdc_page  = &64
fdc_cur   = &65         ; 1770: where the head is (&FF: unknown)

.fdc_init
{
    STA fdc_type
    LDX #nmi_end - nmi_template - 1
.copy
    LDA nmi_template,X : STA NMI_AREA,X
    DEX : BPL copy
    LDA #RTI_OP : STA NMI_AREA
    LDA #0 : STA fdc_state
    LDA fdc_type : BNE w
    LDA #LO(I_DATA) : STA NMI_AREA + nmi_data - nmi_template + 1
    LDA #HI(I_DATA) : STA NMI_AREA + nmi_data - nmi_template + 2
    LDA #1 : STA I_RESET
    LDX #20
.rw DEX : BNE rw
    STX I_RESET
    LDX #i_init_end - i_init - 1
.cmds
    \ (each a command and its parameters, the count first)
    JSR i_command_x
    BPL cmds
    \ The seek's result (ignored: not ready, most likely, but the head is
    \ at track 0 and the 8271 knows it), read to drop its interrupt.
.seek
    BIT I_STATUS : BMI seek
    LDA I_RESULT
    RTS
.w
    LDA #LO(W_DATA) : STA NMI_AREA + nmi_data - nmi_template + 1
    LDA #HI(W_DATA) : STA NMI_AREA + nmi_data - nmi_template + 2
    LDA #W_LATCH AND NOT(4) : STA W_CONTROL     ; reset
    LDX #20
.ww DEX : BNE ww
    LDA #W_LATCH : STA W_CONTROL
    LDA #&FF : STA fdc_cur
    RTS
}

\ The 8271's set-up, read backwards by i_command_x: count, command,
\ parameters.
.i_init
    EQUB 0, &69, 2                              ; Seek 0 (steps until TRK0)
    EQUB &C1, &17, &7A, 3                       ; Write Special Register: mode, no DMA
    EQUB 0, &FF, &FF, &10, &75, 5               ; Specify bad tracks (none), track 0
    EQUB I_LOAD, I_SETTLE, I_STEP, &0D, &75, 5  ; Specify timings
.i_init_end

\ Issue the 8271 command whose bytes end at i_init + X (count, command,
\ parameters, read downwards); returns X before the next, N set at the end.
.i_command_x
{
.idle
    BIT I_STATUS : BMI idle                     ; busy
    LDY i_init,X : DEX
    LDA i_init,X : STA I_COMMAND : DEX : DEY
    BEQ done
.param
    LDA I_STATUS : AND #&20 : BNE param         ; parameter register full
    LDA i_init,X : STA I_PARAM
    DEX : DEY : BNE param
.done
    TXA
    RTS
}

.fdc_read
{
    STA fdc_track : STX fdc_sect : STY fdc_page
    LDA fdc_type : BNE w
    JMP i_start
.w
    LDA fdc_track : CMP fdc_cur : BEQ w_start
    \ A Seek first (the 1770 can't seek within a read); fdc_poll goes on.
    LDA fdc_cur : BPL known
    LDA #&00 + W_RATE : BPL go                  ; Restore, then the seek
.known
    LDA fdc_track : STA W_DATA
    LDA #&10 + W_RATE
.go
    STA W_COMMAND
    LDA #1 : STA fdc_state
    RTS
}

\ Aim the handler at the page and arm it, then the read command.
.arm
{
    LDA fdc_page : STA NMI_AREA + nmi_dst - nmi_template + 2
    LDA #0 : STA NMI_AREA + nmi_dst - nmi_template + 1
    LDA #STA_ABS : STA NMI_AREA
    LDA #2 : STA fdc_state
    RTS
}

.i_start
{
    JSR arm
.idle
    BIT I_STATUS : BMI idle
    LDA #&53 : STA I_COMMAND                    ; Read Data, drive 0
    LDA fdc_track : JSR param
    LDA fdc_sect : JSR param
    LDA #&21                                    ; one 256-byte sector
.param
    PHA
.full
    LDA I_STATUS : AND #&20 : BNE full
    PLA : STA I_PARAM
    RTS
}

.w_start
{
    JSR arm
    LDA fdc_sect : STA W_SECTOR
    LDA #&80 : STA W_COMMAND                    ; Read Sector
    RTS
}

.fdc_poll
{
    LDA fdc_state : BNE busy
    CLC
    RTS
.busy
    LDA fdc_type : BNE w
    \ 8271
    BIT I_STATUS : BMI still
    LDA I_RESULT : AND #&1E
    CMP #&10 : BNE finished
    \ Not ready (a B makes the drive ready on the second index pulse after
    \ it is selected), latched until a Read Drive Status: that, and again.
    LDA #&6C : STA I_COMMAND
.rds
    BIT I_STATUS : BMI rds
    LDA I_RESULT
    JSR i_start
.still
    SEC
    RTS
.w
    LDA W_STATUS : LSR A : BCS still            ; busy (reading drops INTRQ)
    LDA fdc_state : CMP #1 : BNE w_read
    \ The seek (or restore) is done: now the read.
    LDA fdc_cur : BPL sought
    LDA #0 : STA fdc_cur                        ; restored: now the seek
    LDA fdc_track : STA W_DATA
    LDA #&10 + W_RATE : STA W_COMMAND
    SEC
    RTS
.sought
    LDA fdc_track : STA fdc_cur
    JSR w_start
    SEC
    RTS
.w_read
    LDA W_STATUS : AND #&1C                            ; record not found, CRC, lost data
.finished
    LDX #0 : STX fdc_state
    CLC
    RTS
}

.fdc_keepalive
{
    LDA fdc_type : BEQ out
    LDA fdc_state : BNE out
    LDA #&D0 : STA W_COMMAND                    ; Force Interrupt: no INTRQ
.out
    RTS
}

.fdc_spinup
{
    LDA fdc_state : BNE out
    LDA fdc_type : BNE w
.idle
    BIT I_STATUS : BMI idle
    LDA #&7A : STA I_COMMAND                    ; Write Special Register:
    LDA #&23 : JSR i_start_param                ; drive output = select 0 +
    LDA #&48 : JMP i_start_param                ; load head (and motor)
.w
    LDA #&D0 : STA W_COMMAND                    ; starts the motor
.out
    RTS
}
.i_start_param
{
    PHA
.full
    LDA I_STATUS : AND #&20 : BNE full
    PLA : STA I_PARAM
    RTS
}

\ Copied to &0D00. The first byte is RTI until a read arms it.
.nmi_template
    STA NMI_AREA + nmi_restore - nmi_template + 1
.nmi_data
    LDA I_DATA
.nmi_dst
    STA &3000
    INC NMI_AREA + nmi_dst - nmi_template + 1
    BEQ nmi_last
.nmi_restore
    LDA #0
    RTI
.nmi_last
    LDA #RTI_OP : STA NMI_AREA
    BNE nmi_restore
.nmi_end
```
