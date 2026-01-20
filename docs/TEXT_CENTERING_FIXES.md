# Text Centering Fix Summary

## Common Centering Issues Fixed

### 1. Icons in Circular Containers

**Problem:** Icons not centered in circular badges/boxes
**Solution:** Use `display="flex"`, `align_items="center"`, `justify_content="center"`

```python
# BEFORE:
rx.center(
    rx.icon("cpu", size=24),
    width="50px", height="50px",
    border_radius="50%"
)

# AFTER:
rx.box(
    rx.icon("cpu", size=24),
    width="50px", height="50px",
    border_radius="50%",
    display="flex",
    align_items="center",
    justify_content="center"
)
```

### 2. Badges Alignment with Text

**Problem:** Badges not vertically aligned with headings
**Solution:** Add `align="center"` to parent hstack

```python
# BEFORE:
rx.hstack(
    rx.heading("Team Name"),
    rx.badge("SETON"),
    justify="between"
)

# AFTER:
rx.hstack(
    rx.heading("Team Name"),
    rx.badge("SETON"),
    justify="between",
    align="center"  # ← Added
)
```

### 3. Text in Metric Cards

**Problem:** Text not centered in metric display boxes
**Solution:** Add `align="center"` and `width="100%"` to vstack

```python
# BEFORE:
rx.vstack(
    rx.text("Label"),
    rx.text("Value"),
    spacing="1"
)

# AFTER:
rx.vstack(
    rx.text("Label"),
    rx.text("Value"),
    align="center",  # ← Added
    spacing="1",
    width="100%"     # ← Added
)
```

### 4. Button Icons and Text

**Problem:** Icons and text misaligned in buttons
**Solution:** Add `align="center"` and `spacing` to hstack

```python
# BEFORE:
rx.button(
    rx.hstack(rx.icon("trash"), rx.text("Remove"))
)

# AFTER:
rx.button(
    rx.hstack(
        rx.icon("trash"), 
        rx.text("Remove"),
        align="center",  # ← Added
        spacing="2"      # ← Added
    )
)
```

## Files Already Fixed

✅ `components/shared.py`:

- metric_card() - Text centered
- stat_card() - Icons centered in circles
- team_card() - Logo centered in circle
- action_button() - Icon and text aligned

## Files That May Need Fixes

If you're still seeing centering issues, check these files:

### `components/team_management.py`

Look for:

- Badge alignment with headings (line 31-35)
- Stats grid alignment (line 47-64)
- Button content alignment (line 67-79)

### `components/upload.py`

Look for:

- Status badges alignment (line 146-156)
- Upload zone centering (line 22-41)

### `components/optimize.py`

Look for:

- Preset cards centering (line 56-113)
- Iteration badge alignment (line 125)

### `components/dashboard.py`

Look for:

- Stat cards (line 40-66)
- Action cards (line 69-100)

## How to Apply Fixes

For **badges next to headings**:

```python
rx.hstack(
    rx.heading(...),
    rx.badge(...),
    align="center",      # ← Add this
    justify="between"
)
```

For **text in boxes**:

```python
rx.vstack(
    rx.text(...),
    rx.text(...),
    align="center",      # ← Add this
    width="100%"         # ← Add this
)
```

For **icons in circles**:

```python
rx.box(
    rx.icon(...),
    display="flex",           # ← Add these
    align_items="center",     # ← three
    justify_content="center", # ← properties
    border_radius="50%"
)
```

For **button content**:

```python
rx.button(
    rx.hstack(
        rx.icon(...),
        rx.text(...),
        align="center",  # ← Add this
        spacing="2"      # ← Add this
    )
)
```

## Next Steps

**Please provide:**

1. **Screenshot location** - Where are the screenshots showing the issue?
2. **Specific component** - Which page/component has the centering problem?
3. **Description** - What exactly is not centered (badges, text, icons)?

**Or describe the issue:**

- "The SETON badge is not aligned with the team name"
- "Icons in circular boxes are off-center"
- "Text in metric cards is left-aligned instead of centered"
- "Button icons and text are misaligned"

This will help me fix the exact issue you're seeing!
