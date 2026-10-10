# BOSS TU-3S chromatic tuner

Sam's tuner is the **TU-3S**. It's on whenever its AC adaptor is connected,
it has no footswitch, and its OUTPUT is never muted
([TU-3S manual](https://static.roland.com/assets/media/pdf/TU-3S_M_eng02_W.pdf#page=1);
everything below is from that one page). Whether it's still on the
pedalboard is **TODO**, so it's left out of `setup/signal-chain.md` for now.

## Official docs

- Product page: https://www.boss.info/us/products/tu-3s/
- Owner's manual (one page): `boss-tu-3s-manual` in `gear/manuals.yaml`

The manual has no firmware or update procedure.

## Jacks and power

| Jack | What it does |
|------|--------------|
| INPUT | The guitar or bass to tune |
| OUTPUT | To effects or the amp. The tuner is always on, and the sound here is never muted |
| DC IN | BOSS PSA-series AC adaptor (sold separately). That's the only power supply listed: there's no battery |
| DC OUT | While the AC adaptor is in, powers other PSA-compatible pedals through a PCS-20A parallel DC cord (optional) |

Current draw: 30 mA at 9 V, or 85 mA in High Brightness mode. Don't use
cables with a built-in resistor.

## Modes (MODE button)

| Mode | Use it for |
|------|------------|
| Chromatic | All twelve notes; the display shows the note name |
| Chromatic flat | The same, one (♭) or two (2) semitones lower |
| Guitar | Tuning by guitar string number (7-string guitars too) |
| Guitar flat | Guitar, one to six semitones lower |
| Bass | Tuning by bass string number (its extra strings are Lo-B and Hi-C) |
| Bass flat | Bass, one to three semitones lower |

Range C0–C8, accurate to ±1 cent. Play one note: tune until both tuning
guide indicators light and the center of the meter is green.

- **Bass VI** (E1 A1 D2 G2 B2 E3): use **Chromatic**, which shows the note
  name for any note. The string-number modes are laid out for regular
  guitars and basses.

## Settings

- **Meter style:** the STREAM/CENT button switches between CENT (the
  default; the center lights green when in tune) and STREAM.
- **Reference pitch** (436–445 Hz, 440 by default): press MODE and
  STREAM/CENT together, then MODE = +1 Hz and STREAM/CENT = −1 Hz.
- **Accu-Pitch Sign** (the lights stream to the center once tuning is
  stable): hold STREAM/CENT while connecting the AC adaptor, then press
  STREAM/CENT to turn it on or off.
- **High Brightness** (for outdoors): hold STREAM/CENT for 2 seconds;
  do it again to go back.

Mode, meter style, reference pitch and Accu-Pitch Sign stay stored after
power-off.

## Placement and power order

- **TODO:** is it still on the pedalboard? If it is, it goes **first**,
  before the Chroma Console: the manual says other effects must come after
  the TU-3S, or it can't tune correctly.
- Turn the volume down and power everything off before connecting. Power
  the guitar amp on **last**, and off **first**.
