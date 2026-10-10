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

## Controls and menus

From the [manual](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440):

| To | Do this |
|----|---------|
| Pick an effect | Each module has a button: **A** Character, **B** Movement, **C** Diffusion, **D** Texture. Press it to step to the next effect; the button lights in that effect's colour, in the order of the table above: red, orange, green, blue, purple (D lit red = Filter, B lit purple = Pitch) ([p6](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=6), [p9](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=9)) |
| Bypass one module's effect | Press and hold its button ([p9](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=9)) |
| Shape the sound | Character: TILT (dark ↔ bright, neutral at center) + AMOUNT. Movement: RATE + AMOUNT. Diffusion: TIME + AMOUNT. Texture: AMOUNT. MIX blends dry ↔ effected; start at 100% effected ([p6](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=6), [p11](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=11)) |
| Secondary controls (grey labels under the knobs) | A + B; A + B again to leave ([p19](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=19)) |
| FX SETUP | A + D: module order, dual bypass, capture routing, filter style (turn the Texture AMOUNT knob: TILT, low-pass or high-pass), expression; A + D or BYPASS to leave ([pp26–29](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=26)) |
| Save a preset | B + C, choose the slot with the AMOUNT knobs or the footswitches, then B + C again ([pp30–32](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=30)) |
| Calibrate to the instrument | Hold both footswitches until the lights show a purple animation, then play at normal volume; redo it when switching between instruments with very different output levels ([pp7–8](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=7)). How to leave the menu isn't on those pages: unverified |

Two effects in detail:

- **Filter** (Texture): TILT style by default, neutral at center, turn left to
  cut highs and right to cut lows; FX SETUP can make it a low-pass or
  high-pass instead, saved per preset
  ([p17](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=17),
  [p29](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=29)).
- **Pitch** (Movement): RATE fully left = −1 octave, center = no shift, fully
  right = +1 octave; AMOUNT sets how much shifted signal you hear (100% wet
  fully clockwise)
  ([p14](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=14)).
  With the Bass VI, +1 octave puts it at guitar pitch (`gear/bass-vi.md`).

## Sam's favorite presets

| Preset # | Modules used | Sounds like |
|----------|--------------|-------------|
