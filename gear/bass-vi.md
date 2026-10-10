# Fender Vintera III Early '60s Bass VI

Sam's Bass VI is a **Fender Vintera III Early '60s Bass VI** in **Olympic
White** (model # 0149390305). It's a six-string bass tuned like a guitar
**one octave lower** (E1 A1 D2 G2 B2 E3), covering bass and baritone-guitar
range.

## Official docs

- Product page (specs): https://eu.fender.com/products/vintera-iii-early-60s-bass-vi
- Bass owner's manual: `fender-bass-manual` in `gear/manuals.yaml` (Fender's
  current general bass manual, linked under Downloads on the product page)
- `fender-bass-vi-1962`: a scanned instruction manual for the original Bass VI.
  Sam's is a modern reissue, so details may differ.
- Fender bass owner's manuals: https://support.fender.com/hc/en-us/articles/42585248961563-Fender-Bass-Guitar-Owner-s-Manuals
- Factory setup specs: https://support.fender.com/hc/en-us/articles/42507226762651-What-are-factory-setup-specs

## Specs

From the [product page](https://eu.fender.com/products/vintera-iii-early-60s-bass-vi):

| | |
|---|---|
| Body | Alder |
| Neck | Maple, Early '60s "C" shape, 30" (762 mm) scale |
| Fingerboard | Round-laminated rosewood, 7.25" radius, 21 vintage tall frets, clay dot inlays; bone nut, 1.650" (42 mm) |
| Pickups | 3 × Vintage-Style Early '60s Bass VI single-coils ("Jaguar-style") |
| Controls | Master Volume, Master Tone; 3 pickup on/off switches and 1 low cut switch (the "strangle switch") |
| Bridge | 6-saddle vintage-style adjustable, with a "floating" tremolo tailpiece, tremolo lock button, push-in arm and integrated Bass VI mute |
| Strings (factory) | Fender USA Bass VI Nickel Plated Steel, .024–.100 (PN 0730250413) |

## Controls

- Each of the 3 pickups has its own on/off switch, so there are 7 pickup
  combinations.
- The **low cut** ("strangle") switch takes out low end; Fender says the
  pickups go from "beefy bass tones to screaming, overdriven guitar-like
  crunch", especially with it on.
- Master volume and tone; the tremolo has a lock button.
- Where they are, per the drawing in Fender's vintage Bass VI manual (Sam's
  reissue may differ in detail): the 3 pickup switches and the low cut switch
  (called the "tone modification switch" there; it works on any pickup
  combination) are on the switch plate on the upper horn; the tone knob is
  just above the input jack, with the volume knob above it
  ([vintage manual pp7–8](https://www.fmicassets.com/Damroot/Original/10001/leg_gtr_Bass_VI_%281962%29.pdf#page=7)).
- **Mute:** built in near the bridge; it damps the strings for short,
  non-sustained notes. Press lightly on its lettered part to switch it on or
  off ([vintage manual p7](https://www.fmicassets.com/Damroot/Original/10001/leg_gtr_Bass_VI_%281962%29.pdf#page=7)).

## Using it with the rig

- Guitar patterns (chords, riffs) sound deep and baritone; single notes on
  the low strings work as basslines.
- It covers bass frequencies — guitar-voiced drives can thin out the low end.
  On the Chroma Console, compare Character effects with the bass strings.
- Tuning: use the TU-3S's **Chromatic** mode (`gear/boss-tuner.md`) and tune
  one octave below guitar.

## Getting a guitar-like tone

When the Bass VI sounds too bassy through the rig, work along the chain
(bass → Chroma Console → Micro Terror → TX-6) and change one thing at a time.
Picture: `setup/diagrams/bass-vi-guitar-tone.yaml` (render it with the
skill's `diagram.py`).

1. **On the bass** (the biggest change):
   - Low cut switch **on**: Fender's
     [product page](https://eu.fender.com/products/vintera-iii-early-60s-bass-vi)
     says the pickups go from "beefy bass tones to screaming, overdriven
     guitar-like crunch".
   - Mute **off**, so notes sustain
     ([vintage manual p7](https://www.fmicassets.com/Damroot/Original/10001/leg_gtr_Bass_VI_%281962%29.pdf#page=7)).
   - Tone knob all the way up; try each pickup on its own and keep the
     brightest (usually the one nearest the bridge). Play with a pick, and
     play chord shapes 12 frets higher: that's one octave up, the same pitch
     as those shapes on a guitar at the nut. *General guitar practice, not
     from Fender's docs.*
2. **Chroma Console:**
   - MIX all the way to effected (the manual suggests starting at 100%), so
     no dry, unfiltered signal gets around the effects
     ([p5](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=5),
     [p6](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=6)).
   - Press **D** (Texture) until it lights red: **Filter**. In its default
     TILT style the center is neutral, and turning the blue AMOUNT knob right
     cuts lows
     ([p17](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=17)).
     For a plain high-pass instead: press A + D, turn the Texture AMOUNT knob
     to pick the style, then A + D to leave
     ([p29](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=29)).
   - Press **A** (Character) until it lights orange (**Sweeten**: a preamp
     with EQ, compression and gentle saturation) or red (**Drive**: warm
     preamp to full overdrive), and turn TILT toward BRIGHT
     ([pp11–12](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=11)).
   - Optional, to play at guitar pitch: press **B** (Movement) until it lights
     purple: **Pitch**. RATE fully right = +1 octave; AMOUNT fully clockwise =
     only the shifted sound, less blends in the original
     ([p14](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=14)).
     The manual doesn't say how it copes with chords: try single notes and
     chords.
   - Save it as a preset: B + C, pick a slot with the AMOUNT knobs or the
     footswitches, then B + C again
     ([pp30–32](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=30)).
3. **Orange Micro Terror:** TONE clockwise = brighter; a bit more GAIN for
   crunch (at zero there's no sound)
   ([p3](https://cdn.shopify.com/s/files/1/0943/5250/7206/files/Micro_Terror_-_Word_Manual_2025_V1.0_EN.pdf?v=1758622989#page=3)).
4. **TX-6, on the amp's channel:** the channel's three parameter knobs are a
   3-band EQ by default (±18 dB per band): turn the **white** knob (low) down
   and the **blue** knob (high) up a little
   ([TX-6 guide p29](https://assets.teenage.engineering/_img/66152ced1cfae6ae3cfe32a7_original.png),
   [p30](https://assets.teenage.engineering/_img/66152ced1cfae6ae3cfe329a_original.png)).
   For more low cut, the track menu (hold shift and press the channel's track
   button; keep pressing to cycle) has a low-pass / high-pass filter: turn
   the select knob toward HP
   ([TX-6 guide p25](https://assets.teenage.engineering/_img/66152cee1cfae6ae3cfe32c2_original.png)).
