# Orange Micro Terror (amp head)

Small guitar amp head: 20 W with a valve (12AX7/ECC83) preamp. Sam feeds the
TX-6 from its **HEADPHONES** jack.

> **No speaker cabinet: keep HEADPHONES plugged in.** Sam has no cab; the
> OB-4 (through the TX-6) is his only speaker. The manual says that if the
> HEADPHONES jack isn't in use, a speaker cabinet must be connected at all
> times during use
> ([p3](https://cdn.shopify.com/s/files/1/0943/5250/7206/files/Micro_Terror_-_Word_Manual_2025_V1.0_EN.pdf?v=1758622989#page=3)).
> So the **HEADPHONES → TX-6 cable must be plugged in whenever the amp is
> on**: connect it before switching the amp on, and switch the amp off
> before unplugging it.

## Official docs

- Product page: https://orangeamps.com/products/micro-terror
- Product manual PDF (V1.0, Aug 2025): `orange-micro-terror-manual` in
  `gear/manuals.yaml`; search/read/cite it with `manuals.py`

No firmware: nothing to update.

## Controls and jacks

From the [Micro Terror manual p3](https://cdn.shopify.com/s/files/1/0943/5250/7206/files/Micro_Terror_-_Word_Manual_2025_V1.0_EN.pdf?v=1758622989#page=3):

| Control / jack | What it does |
|----------------|--------------|
| GAIN | Clean at low settings, heavy distortion at high ones. **At zero there's no sound at all** |
| TONE | Clockwise = brighter |
| VOLUME | Overall output volume |
| INPUT | Instrument in (here: from the Chroma Console) |
| AUX IN | 3.5 mm in for a phone or laptop; summed to mono |
| HEADPHONES | 1/4in jack with CabSim (recreates an Orange 4×12 cabinet). Also meant for connecting to a mixer or recording console: **this is what feeds the TX-6** |
| SPEAKER OUTPUTS (rear) | Speaker cabinet only, rated 8 Ω or higher, with a speaker cable (never an instrument cable) |
| DC INPUT (rear) | 15 V DC / 2 A: only the power adapter that came with it |

Specs: 20 W, valve preamp (1 × 12AX7/ECC83), output impedance 8–16 Ω.

## Into the TX-6 safely

1. Turn the amp's VOLUME to zero before switching it on
   ([p2](https://cdn.shopify.com/s/files/1/0943/5250/7206/files/Micro_Terror_-_Word_Manual_2025_V1.0_EN.pdf?v=1758622989#page=2)).
2. Cable the amp's **HEADPHONES** (1/4in) to a TX-6 channel input (3.5 mm)
   with a 1/4in → 3.5 mm cable. Which channel is TODO (`setup/signal-chain.md`).
3. When the plug goes in, the TX-6 asks for the input mode: pick **mono**,
   which mixes the left input to both sides (the guitar signal is mono)
   ([TX-6 guide p23](https://assets.teenage.engineering/_img/66152cee1cfae6ae3cfe32d1_original.png)).
4. Start with the amp's VOLUME and the TX-6 channel gain low, then bring them
   up.
5. **Never** connect the SPEAKER OUTPUTS to the TX-6. The headphones and
   speaker outputs work at the same time, but if nothing is plugged into
   HEADPHONES, a speaker cabinet must be connected whenever the amp is on
   ([p3](https://cdn.shopify.com/s/files/1/0943/5250/7206/files/Micro_Terror_-_Word_Manual_2025_V1.0_EN.pdf?v=1758622989#page=3)).
   Sam has no cabinet, so the HEADPHONES cable stays in (see the top of this
   file).

## Using it for non-guitar instruments

Sam runs every instrument through it (Bass VI, Jaguar, Telecaster, Ibanez
TOD10N, Colour Palette kalimba). What the manual says that matters for that
([p3](https://cdn.shopify.com/s/files/1/0943/5250/7206/files/Micro_Terror_-_Word_Manual_2025_V1.0_EN.pdf?v=1758622989#page=3)):

- The HEADPHONES out (the one feeding the TX-6) always has the CabSim, which
  recreates an Orange 4×12 guitar cabinet. The manual lists no way to turn it
  off. Great for the electrics; it colors the nylon acoustic and the kalimba.
- GAIN goes from clean (low) to heavy distortion (high), and at zero there's
  no sound. For the cleanest sound, keep GAIN just above zero and make up the
  level with VOLUME and the TX-6 channel gain.
- One INPUT: anything stereo before it (the Chroma Console's stereo effects)
  ends up mono.
- How the CabSim affects the Bass VI's low end isn't in the manual: unverified.

**Skipping the amp** (an option, for the kalimba / nylon, or for stereo
effects): the Chroma Console makes stereo from a mono input when both outputs
are connected; its output impedance is under 1 kΩ
([Chroma Console manual p43](https://cdn.shopify.com/s/files/1/0920/2928/8752/files/CC_manual_WEB.pdf?v=1758823440#page=43)).
The TX-6 inputs are 3.5mm stereo with 0–42 dB of gain (`gear/tx-6.md`) and
have a stereo input mode, the default
([TX-6 guide p24](https://assets.teenage.engineering/_img/66152cee1cfae6ae3cfe32c4_original.png)).
So OUTPUT L + R → a dual 1/4in → 3.5mm stereo cable → a free TX-6 channel in
stereo mode should work (not yet tried on this rig). If the amp is switched
on, its HEADPHONES → TX-6 cable must still stay plugged in (top of this file).
