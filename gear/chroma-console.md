# Hologram Electronics Chroma Console

Multi-effect pedal with four effect "modules" that can run together. The only
pedal on Sam's board: instruments → Chroma Console → amp. Jacks are printed
INPUT L / INPUT R and OUTPUT L / OUTPUT R; for a mono guitar, use one input
and one output
([manual pp42–43](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=42)).

## Official docs

- Product page: https://www.hologramelectronics.com/pages/chroma-console
- Manual: https://www.hologramelectronics.com/pages/chroma-console-manual
  (the PDF, firmware V1.04, is `chroma-console-manual` in `gear/manuals.yaml`)
- Firmware: https://www.hologramelectronics.com/pages/chroma-console-firmware
- Support: https://www.hologramelectronics.com/pages/support

## Firmware update

Over **USB-C** using Hologram's updater — follow the current instructions and
version on the firmware page above (they change over time; check there rather
than trusting a remembered version number).

## Modules and effects

Up to 4 effects at once (one per module), order is re-arrangeable.

| Module | Effects |
|--------|---------|
| **Character** (drive/tone) | Drive, Sweeten, Fuzz, Howl, Swell |
| **Movement** (modulation) | Doubler, Vibrato, Phaser, Tremolo, Pitch |
| **Diffusion** (time/space) | Cascade (delay), Reels (tape echo), Space (reverb), Collage (granular), Reverse |
| **Texture** (lo-fi/grit) | Filter, Squash, Cassette, Broken, Interference |

Other features:
- **Gesture:** record knob movements and play them back as automation.
- **Capture:** short on-board looping/capture within the effect chain.
- **Drift:** global randomness/instability for a worn-tape feel.
- Presets (~80), MIDI (preset recall + CC), expression pedal input.
- Stereo or mono in/out; selectable true/buffered bypass.
- Input sensitivity is adjustable — works with guitar, bass, **synths and
  drum machines** too (could process OP-XY/OP-1 field/kalimba).

Unverified — confirm in the manual and update here: MIDI jack type, exact
power draw (9V DC center-negative; current rating TBD).

## Sam's favorite presets

| Preset # | Modules used | Sounds like |
|----------|--------------|-------------|
