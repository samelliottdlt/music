# Teenage Engineering OP-1 field

Portable synthesizer, sampler, drum machine, and 4-track tape recorder.
**Not** the original OP-1 — the original's guide (`/guides/op-1/original`)
does not apply.

## Official docs

- User guide PDF (firmware 1.7.0): `op-1-field-guide` in `gear/manuals.yaml`;
  search/read/cite it with `manuals.py` (see the skill). It's the
  "download as PDF" link on the guide page.
- User guide (single long web page): https://teenage.engineering/guides/op-1
- Downloads / firmware + release notes: https://teenage.engineering/downloads/op-1/field
- Product/spec page: https://teenage.engineering/products/op-1
- Browser updater (Web MIDI): https://teenage.engineering/apps/update
- Sound packs: https://teenage.engineering/downloads/op-1/sound-packs

> The guide web page is JS-rendered; plain fetches often return only legal
> text. Use the registered PDF instead (it's linked from the guide page, not
> from the downloads page).

## Firmware update

Latest known: **1.7.3** (2026-05-26). Check the downloads page for newer.

**Option A — browser (easiest):** open https://teenage.engineering/apps/update
in Chrome/Edge, connect via USB-C, follow the prompts.

**Option B — manual (te boot):**
1. Download the latest `.tfw` file from the downloads page.
2. Turn the OP-1 field **off**.
3. **Hold COM while switching it on** → "te boot" appears.
4. Connect USB-C to your computer and **press 1** → it mounts as a disk.
5. Copy the `.tfw` file onto the disk, then eject safely.
6. Wait for the update to finish; follow on-screen instructions.

## Inputs / outputs

| Connector | Details |
|-----------|---------|
| 3.5mm input | Stereo line-in (mono/stereo selectable), 13 kΩ, 0–31 dB gain |
| 3.5mm output | Stereo out, max 8 dBu / 2 Vrms; TRRS headset-mic support |
| USB-C | USB audio host & device (multi-channel), USB MIDI host & device, MTP disk for files, charging |
| Bluetooth LE | BLE MIDI (host and peripheral) |
| FM radio | Receive **and transmit** (87.5–108 MHz); can sync transmit freq with OB-4 |
| Built-in | Stereo mic, speaker |

No MIDI DIN, no sync jack. Battery ~24 h.

## Built-in sounds & creative features

- **Synth engines:** cluster, digital, dimension, dna, drwave, dsynth, fm,
  phase, pulse, sampler, string, voltage, vocoder, amp (fw 1.6.0), plus a
  built-in tuner (fw 1.6.0).
- **Drum:** drum sampler kits ("dbox" drum engine), per-key pitch/loop/play mode.
- **Sequencers:** arpeggio, endless (up to 999 steps), finger, hold, pattern,
  sketch, tombola.
- **LFOs:** element (gyro/mic/etc.), midi, random, tremolo, value, velocity.
- **Effects:** cwo, delay, grid, mother (reverb), nitro, phone, punch, spring,
  terminal. Master EQ + compressor.
- **Tape:** 4 stereo tracks, up to 8 tapes, 4 tape formats (studio 4-track,
  vintage 4-track, porta, disc mini); tape tricks: reverse, speed/pitch,
  scrub, lift/drop/merge, undo (fw 1.6.9).
- **Scales:** no scale-lock — transpose with the octave buttons/shift. (The
  OP-XY's "brain" handles keys/scales.)
- **Factory presets:** the exact preset names live on the device / sound
  packs, not in the text guide. Sam's favorites go below.

## Sam's favorite presets / patches

| Engine | Preset | Why it's good |
|--------|--------|---------------|

## Tips

- Recording the whole rig: see `setup/recording.md`.
- Sync with OP-XY: USB-C MIDI (one device as host) or BLE MIDI; see `gear/op-xy.md`.
