# Teenage Engineering OP-XY

Sequencer-centric synth/sampler/groovebox: 8 instrument tracks + 8 auxiliary
tracks, step sequencer, song mode.

## Official docs

- Full guide PDF (v1.1.15): `op-xy-guide` in `gear/manuals.yaml`; search/read/
  cite it with `manuals.py`. Cite PDF page numbers (the numbers printed on
  the pages are 4–5 lower).

Guide (split into chapters — these fetch better than OP-1/TX-6 pages):

- Index: https://teenage.engineering/guides/op-xy
- Hardware overview: https://teenage.engineering/guides/op-xy/hardware-overview
- Get started: https://teenage.engineering/guides/op-xy/get-started
- Sequencer: https://teenage.engineering/guides/op-xy/sequencer
- Step components: https://teenage.engineering/guides/op-xy/step-components
- Players (arp / maestro): https://teenage.engineering/guides/op-xy/players
- Workflow (patterns / scenes / songs): https://teenage.engineering/guides/op-xy/workflow
- Instrument: https://teenage.engineering/guides/op-xy/instrument
- Synth engines: https://teenage.engineering/guides/op-xy/synth-engines
- Sample: https://teenage.engineering/guides/op-xy/sample
- Auxiliary (brain, punch-in FX, external MIDI/CV/audio, tape): https://teenage.engineering/guides/op-xy/auxiliary
- FX: https://teenage.engineering/guides/op-xy/fx
- Mix: https://teenage.engineering/guides/op-xy/mix
- COM (settings, MIDI, BLE, multi-out): https://teenage.engineering/guides/op-xy/com
- MIDI reference: https://teenage.engineering/guides/op-xy/midi-references
- Downloads / firmware: https://teenage.engineering/downloads/op-xy
- Sound packs: https://teenage.engineering/downloads/op-xy/sound-packs
- Browser updater: https://teenage.engineering/apps/update

## Firmware update

Latest known: **1.1.33** (2026-09-02). Check the downloads page for newer.

**Option A — browser:** https://teenage.engineering/apps/update over USB-C.

**Option B — manual (te boot):**
1. Download the latest `.tfw` from the downloads page.
2. Turn OP-XY **off**, then **hold COM while switching on** → "te boot".
3. Connect USB-C and **press 1** → mounts as a disk.
4. Copy the `.tfw` to the disk, eject, wait for the update to finish.

## Inputs / outputs

| Connector | Details |
|-----------|---------|
| 3.5mm line in | Stereo line-level input |
| 3.5mm out | Stereo out (~2 dBu / 1 Vrms), TRRS headset-mic support |
| 3.5mm multi-out | One mode at a time: MIDI, CV+gate, sync8/16/24, or audio (set in COM; change only while unplugged) |
| USB-C | Audio & MIDI host/device, charging, MTP disk |
| Bluetooth LE | BLE MIDI |
| Built-in | Mic, speaker |

Battery ~16 h. 8 GB storage.

## Built-in sounds & creative features

- **Synth engines (8):** axis (FM), dissolve (tonal noise), epiano, hardsync,
  organ, prism, simple, wavetable. Plus sampler/drum/multisampler/slicer, and
  an "external" engine to sequence outboard MIDI gear.
- **Default new-project tracks:** 1–2 drums, 3 bass, 4 pluck, 5 lead,
  6 soft pluck, 7 strings, 8 pad.
- **Per-track:** envelopes, filter, play mode (poly/mono/legato, portamento),
  LFO (element, random, tremolo, value).
- **Aux tracks:** 1 **brain** (song-wide key/scale + auto-transpose),
  2 **punch-in FX** (24 live keyboard effects), 3 external MIDI, 4 external CV,
  5 external audio (bring line-in/mic into the mix), 6 tape (glitch/
  resample), 7–8 FX I/II sends.
- **Send effects:** chorus, delay, distortion, lofi, phaser, reverb.
- **Sequencer:** up to 4 bars × 16 steps per pattern (longer via track scale),
  step/live recording, groove presets (shuffle, half shuffle, triplet,
  wobbly…), parameter locks.
- **Step components (14):** pulse, hold, multiply, velocity, ramp up, ramp
  down, random, portamento, bend, tonality, jump, skip step, skip parameter
  lock, skip trigger.
- **Players:** arpeggio, maestro (chord record/playback by key).
- **Structure:** pattern → scene (99) → song (9) → project.
- **Mix:** master 3-band EQ, compressor, saturator.

## Sam's favorite presets / patches

| Track/engine | Preset | Why it's good |
|--------------|--------|---------------|

## Syncing with OP-1 field

- **USB-C MIDI:** connect the two with a USB-C cable; one acts as host
  (OP-1 field supports USB MIDI host). Inferred from shared architecture —
  verify and document.
- **BLE MIDI:** advertise OP-XY on Bluetooth MIDI (COM menu), connect from
  the OP-1 field's BLE device list. Both support MIDI clock over BLE.
- OP-XY can sequence the OP-1 field via the **external MIDI** aux track.
