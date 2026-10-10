# Teenage Engineering TX-6

Pocket 6-channel stereo mixer, USB audio interface, tiny synth/drum
sequencer, and recorder. The center of Sam's setup — everything goes here.

## Official docs

- User guide: https://teenage.engineering/guides/tx-6
- Product/spec page (best hardware detail): https://teenage.engineering/products/tx-6
- Downloads / firmware: https://teenage.engineering/downloads/tx-6
- Browser updater: https://teenage.engineering/apps/update

## Firmware update

Latest known: **1.3.3** (2026-01-28). Check the downloads page for newer.

Tip from TE: **save your settings to a scene first** (scenes added in 1.3.0).

**Option A — browser:** https://teenage.engineering/apps/update over USB-C.

**Option B — manual:**
1. Download the latest firmware from the downloads page.
2. Connect TX-6 to the computer via USB-C.
3. **Hold CUE while switching on** → mounts as a disk.
4. Copy the firmware file to the disk, eject, wait for it to finish.

## Inputs / outputs

| Connector | Details |
|-----------|---------|
| Ch 1–6 inputs | 3.5mm stereo, 10 kΩ, 0–42 dB gain, max 13 dBu |
| Main out | 3.5mm stereo (6.35mm adapter included), max 8 dBu / 2 Vrms |
| Aux out | 3.5mm stereo, same spec as main (configurable "split aux out") |
| Cue / headphone | 3.5mm TRRS (headset mic supported), max 2 dBu |
| USB-C | 24-bit/48 kHz audio interface up to 12-in/12-out; USB audio host or device; USB MIDI; USB disk recording/playback (stereo WAV) |
| Bluetooth LE | BLE MIDI, ortho remote |

Battery ~8 h. Inputs are 3.5mm — use 1/4in → 3.5mm cables for guitar-amp/
kalimba sources. TE's "field audio" cables are slim so all six fit.

## Mixer features

- Every channel: 3-band EQ + compressor; knob rows are reassignable.
- Send FX: reverb, chorus, delay. Creative FX: freeze, tape, filter, distortion.
- DJ mode: turn it on its side; channel 1 crossfades channels 5 ↔ 6.
- Scenes (save/recall full mixer state), built-in instrument tuner.
- **Built-in synth + sequencer:** 4 oscillator waveforms, 4 synthesized drum
  sounds, tempo sync, patterns + chaining. Handy as a click/reference.
- Sync out (PO-style 8th-note on aux/cue; sync16 for modular), beat tracking.
- Disk recorder: record the mix to a USB drive (auto-start on signal).

## Tips

- Keep a **channel map** in `setup/signal-chain.md`.
- Guitar amp into a channel: start with channel gain low; amp line/headphone
  out is hotter than an instrument.
- Recording to OP-1 field: `setup/recording.md`.
