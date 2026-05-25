# Why depth-to-water, not piezometric head?

This document explains the physical reasoning behind using **groundwater depth**
(metres below ground surface) rather than **piezometric head** (metres above sea level)
in the 2S-TOOL stress-strain analysis.

---

## 1. The two quantities

```
                            GROUND SURFACE
                         ┌──────────────────┐  ┌───────┐
                         │  monitoring well  │  │  well │
                         │       casing      │  │  cap  │
                         │        ▌▐         │  └───┬───┘
                         │        ▌▐         │      │
                         │        ▌▐         │      │
     ┌───────────────────┼────────▌▐─────────┼──────┼───────────  SEA LEVEL (0 m)
     │                   │        ▌▐         │      │
     │   piezometric     │   ┌────▌▐────┐    │      │
     │   head (m)  ──────┼───┤  screen  ├────┼──────┤  h = +5 m
     │   = elevation     │   └────▌▐────┘    │      │   (head ABOVE sea level)
     │   of water surface│        ▌▐         │      │
     │                   │   ┌────▌▐────┐    │      │
     │                   │   │  screen  │    │      │
     │                   │   └──────────┘    │      │
     │                   │        ▌▐         │      │
     └───────────────────┴────────▌▐─────────┴──────┘
    (depth increases ↓)

     depth-to-water (m) = well_elev - piezometric_head
     = distance from ground surface down to the water level in the well

Example: TUKU well 09050321
  well_elev = 17.3 m  (ground surface is 17.3 m above sea level)
  piezometric_head = +5.5 m  (water stands 5.5 m above sea level)
  → depth = 17.3 - 5.5 = 11.8 m below ground
```

- **Piezometric head** is referenced to sea level — shared reference across all wells, but wells sit at different ground elevations.
- **Depth-to-water** is referenced to the **ground surface at that well** — local reference, but physically meaningful for stress calculations.

---

## 2. The stress-strain curve

```
  2S-TOOL plots:   x-axis = Ground displacement (m)  [reversed: right → left = more compaction]
                   y-axis = Groundwater depth (m)     [down = deeper water]
```

When groundwater is pumped, the water table drops. Deeper water means lower pore pressure,
which means **higher effective stress** on the aquifer skeleton:

```
    Δσ' = γ_w × Δh          (effective stress change = unit weight of water × head decline)
```

Since `depth = elev − head`, a head decline of Δh is exactly a depth increase of Δh:

```
    Δ(depth) = −Δ(head)
```

The stress-strain curve plots **depth** on the y-axis so that:

```
                   MORE STRESS
                       ↑
                       │    ╭────╮  ← elastic loop (loading limb)
        GWL depth (m)  │   ╱      ╲
                       │  ╱        ╲
                       │ ╱          ╲
                       │╱            ╲
                       └──────────────────→  Ground displacement (m) [reversed]
                              MORE COMPACTION →
```

The key insight: **both axes point in the direction of increasing stress**.
Rightward = more compaction (strain). Downward = deeper water (stress proxy).

---

## 3. Four reasons depth is the natural choice

### Reason 1: hp_inicial is a depth concept
```
   "Preconsolidation head" is the deepest historical groundwater level
   the aquifer has ever experienced.

   It is measured as a depth below ground — the deepest the water table
   has ever been drawn down by historical pumping.

   If a well has well_elev = 17 m and the deepest head ever recorded was
   h_min = −5.5 m, then:

       hp_inicial = 17 − (−5.5) = 22.5 m  depth below ground

   This is a physically intuitive number for hydrogeologists.
```

### Reason 2: Well-to-well comparability
```
          Well A                    Well B
     elev = 17 m                elev = 110 m
     (coastal plain)            (foothills)

     h_A = +5 m                 h_B = +95 m
     depth_A = 12 m             depth_B = 15 m

   Using piezometric head directly:  h_A (5 m) vs h_B (95 m) — meaningless
   Using depth:                      depth_A (12 m) vs depth_B (15 m) — comparable

   Depth normalizes to the same reference (ground surface). Two wells with
   similar depths are experiencing similar stress regimes, regardless of
   their absolute elevation.
```

### Reason 3: The hysteresis loop orientation is intuitive
```
   Using DEPTH (m):                Using HEAD (m):

   stress ↑  depth ↑               stress ↑  head ↓
      │     ╭──╮                      │     ╭──╮
      │    ╱    ╲                     │    ╱    ╲
      │   ╱      ╲                    │   ╱      ╲
      └──────────→ disp               └──────────→ disp
        (both axes run                       (head axis runs OPPOSITE
         with stress)                         to stress direction)

   With depth, loading = downward on BOTH axes → loops open naturally downward.
   With head, loading = head DROPS while strain INCREASES → visually disorienting.
```

### Reason 4: MATLAB original convention
```
   The method by Navarro-Hernández, Valdes-Abellan, and Tomás was developed
   with Spanish aquifer datasets (Vega Baja, Alicante) where groundwater
   measurements are reported as depth-to-water. The algorithm's y-interval
   peak-detection logic and elastic-period classifier were designed around
   depth values. Switching to head would require inverting every sign-sensitive
   decision in the MATLAB logic — not just the plot axis.
```

---

## 4. Mathematical equivalence (with a caveat)

The conversion is a pure offset:

```
    GWL_depth = well_elev − piezometric_head
```

Since only **changes** in depth/head matter for stress calculations, and the slope
of the stress-strain curve depends on Δdepth / Δdisplacement, the offset cancels:

```
    Δ(depth)     −Δ(head)
    ───────── = ─────────   →  same slope, same S_kv, same S_ke
    Δ(disp)      Δ(disp)
```

If the original MATLAB code used head instead of depth, the numerical results (S_kv,
S_ke values) would be **identical**. Only the visual orientation of the plots and the
interpretation of hp_inicial as a threshold would differ.

The choice is therefore about **physical interpretation**, not numerical necessity.

---

## 5. Does unconfined vs confined matter?

**Short answer: No, the depth-to-water conversion is valid for both.** But the physical
meaning of the measurement differs, and this matters for interpreting the results.

### 5.1 What the well actually measures

```
    UNCONFINED AQUIFER                     CONFINED AQUIFER
    ==================                     ================

    ┌────────────────────┐                 ┌────────────────────┐
    │  ground surface    │                 │  ground surface    │
    ├────────────────────┤                 ├────────────────────┤
    │                    │                 │                    │
    │   unsaturated      │                 │   aquitard (clay)  │  ← confining layer
    │   zone             │                 │                    │
    │                    │                 ├────────────────────┤
    │   ═══════════════  │ ← water table   │                    │
    │                    │                 │   confined aquifer │  ← under pressure
    │   saturated zone   │  (free surface) │   (sand/gravel)    │
    │   (unconfined      │                 │                    │
    │    aquifer)        │                 │   well screen ──── │  ← where measurement is taken
    │                    │                 │                    │
    │   well screen ──── │                 ├────────────────────┤
    │                    │                 │   aquitard (clay)  │
    └────────────────────┘                 └────────────────────┘

    Well water level = actual             Well water level = pressure head
    water table elevation                 (may rise ABOVE the aquifer top —
                                          this is the definition of "confined")
```

In an **unconfined aquifer**, the piezometric head is literally the elevation of the
free water surface (the water table). The well water level sits at exactly the top of
the saturated zone.

In a **confined aquifer**, the piezometric head is a **pressure reading**, not a free
surface. Water in the well rises above the top of the aquifer because the aquifer is
pressurized by the weight of the overlying confining layers. The water level you see in
the well casing does NOT correspond to a free water surface at that depth — it is the
height the water would rise if the confining pressure were released.

### 5.2 Why both give the same effective stress

Terzaghi's principle of effective stress:

```
    σ' = σ_total − u

    where:  σ'       = effective stress (what drives compaction)
            σ_total  = total overburden stress (weight of everything above)
            u        = pore water pressure
```

When you pump from either aquifer type, pore pressure (u) drops. The total stress from
the overburden does not change. So:

```
    Δσ' = −Δu                    (effective stress increases when pore pressure drops)
```

Since pore pressure is measured as piezometric head:

```
    u = γ_w × (h − z)            where z = elevation of the measurement point

    Δu = γ_w × Δh                (total stress and elevation are constant)
    Δσ' = −γ_w × Δh

    And since:  Δ(depth) = −Δh
    Therefore:  Δσ' = γ_w × Δ(depth)
```

**The effective stress change is proportional to the change in water level in the
well, regardless of whether the aquifer is confined or unconfined.** A 1-metre drop
in the water level in the well casing produces the same effective stress increase
(γ_w × 1 m ≈ 9.81 kPa per metre of water) in both cases.

### 5.3 The one subtlety: unconfined aquifers have an extra term

In an unconfined aquifer, when the water table drops, the pore space above the new
water table drains. This means the total stress also changes slightly (the overburden
above the measurement point loses some water weight). The full expression becomes:

```
    Δσ' = γ_w × Δh  −  γ_w × Δh × (degree of saturation change)
                ↑                        ↑
         pore pressure term        total stress correction
         (dominates)              (small, often neglected)
```

For a confined aquifer, the total stress term is exactly zero — the overburden weight
does not change because the aquifer remains fully saturated and the confining layers
transmit the overburden weight to the aquifer skeleton through grain-to-grain contact.

**In practice, for the subsidence-relevant stress ranges in the Taiwan dataset, the
total stress correction for unconfined conditions is negligible.** The 2S-TOOL method
treats both aquifer types identically, using the water level change in the well as the
driving stress signal.

### 5.4 Relevance to this project

The Choushui River Fluvial Plain wells are screened in **confined aquifers** (see
`data/gwl/well_info/gwl_allwells_flat.csv` — screen depths of 40–280 m below ground,
isolated between clay aquitards). The piezometric head measured in these wells is a
**pore pressure** measurement, not a free water table.

When we convert to depth via `depth = elev − head`, we are NOT claiming that there is
a water table at that depth. We are simply using the linear relationship between head
decline and effective stress increase. The "depth" value is a stress index — it answers
the question: *"how much effective stress has been added to the aquifer skeleton since
the head was last at this level?"*

```
    Piezometric head = +5 m      →  "Water pressure supports 5 m of water column
                                     above sea level at this screen depth."

    GWL depth = 12 m             →  "The effective stress at this screen is equivalent
                                     to what it would be if the water table were 12 m
                                     below ground in an equivalent unconfined system."

    hp_inicial = 22.8 m          →  "The maximum effective stress this aquifer layer
                                     has ever experienced is equivalent to a 22.8 m
                                     water table drawdown below ground surface."
```

---

## 6. Summary

| Aspect | Depth-to-water | Piezometric head |
|--------|---------------|-----------------|
| Reference | Ground surface (per-well) | Sea level (shared) |
| Increases when | Pumping / drought | Recharge / wet season |
| hp_inicial | Deepest ever depth (intuitive) | Lowest ever head (less intuitive) |
| Cross-well compare | Directly comparable | Requires elevation correction |
| Plot orientation | Both axes follow stress | Head axis inverted vs stress |
| Numerical result | Identical S_kv, S_ke | Identical S_kv, S_ke |

**Conclusion:** The 2S-TOOL uses depth-to-water because hp_inicial is physically defined
as a depth, and the stress-strain curve reads more intuitively when both axes point in
the direction of increasing stress. The conversion `depth = elev − head` is applied at
input-preparation time so that the core algorithm never needs to know about elevation.
