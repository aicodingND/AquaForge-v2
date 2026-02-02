# AquaForge Design System v2.0

> Generated: 2026-01-27 | Preserves Navy & Gold Brand Identity

---

## 🎨 Brand Colors (PRESERVED)

### Navy Palette - Depth Hierarchy
| Token        | Hex     | Usage               |
| ------------ | ------- | ------------------- |
| `--navy-900` | #040D18 | Deepest backgrounds |
| `--navy-800` | #091A30 | Primary backgrounds |
| `--navy-700` | #0C2340 | Cards, panels       |
| `--navy-600` | #123456 | Elevated surfaces   |
| `--navy-500` | #1a3a5c | Borders, dividers   |
| `--navy-400` | #2a4a6c | Hover states        |
| `--navy-300` | #3a5a7c | Disabled text       |

### Gold Palette - Action & Accent
| Token          | Hex                     | Usage              |
| -------------- | ----------------------- | ------------------ |
| `--gold-600`   | #8B7000                 | Pressed states     |
| `--gold-500`   | #C99700                 | Primary actions    |
| `--gold-400`   | #D4AF37                 | Default accent     |
| `--gold-300`   | #E5C158                 | Hover states       |
| `--gold-200`   | #F0D68A                 | Highlights         |
| `--gold-glow`  | rgba(201, 151, 0, 0.4)  | Focus rings        |
| `--gold-muted` | rgba(201, 151, 0, 0.15) | Subtle backgrounds |

### Semantic Colors
| Token       | Hex     | Usage              |
| ----------- | ------- | ------------------ |
| `--success` | #10B981 | Wins, improvements |
| `--warning` | #F59E0B | Caution states     |
| `--error`   | #EF4444 | Losses, errors     |
| `--info`    | #3B82F6 | Information        |

---

## 📐 Typography

### Recommended Pairings (For Dashboard/Analytics)
**Current:** Inter (system)
**Enhanced Option:** Fira Sans + Fira Code

```css
/* Optional: For data-heavy views */
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

/* Data/stats: Fira Code for monospace numbers */
.stat-value { font-family: 'Fira Code', monospace; }

/* Keep Inter for general UI */
body { font-family: 'Inter', system-ui, sans-serif; }
```

### Type Scale
| Level   | Size            | Weight | Usage                 |
| ------- | --------------- | ------ | --------------------- |
| H1      | 2.5rem (40px)   | 800    | Page titles           |
| H2      | 1.875rem (30px) | 700    | Section headers       |
| H3      | 1.25rem (20px)  | 600    | Card titles           |
| Body    | 0.875rem (14px) | 400    | General text          |
| Caption | 0.75rem (12px)  | 500    | Table headers, labels |

---

## 🖼️ UI Style: Dark Mode (OLED-Optimized)

### Style Profile
- **Keywords:** dark theme, high contrast, deep navy, OLED-friendly
- **Performance:** ⚡ Excellent (less pixel illumination)
- **Accessibility:** ✓ WCAG AAA contrast ratios

### Key Effects
1. **Minimal glow:** `text-shadow: 0 0 10px var(--gold-glow)` for emphasis
2. **Glassmorphism:** `backdrop-filter: blur(12px)` with navy transparency
3. **Gold accents:** Reserve for interactive elements only
4. **Low white emission:** Text at #fafafa, not pure white

### Anti-Patterns to AVOID
| ❌ Don't                | ✅ Do Instead                  |
| ---------------------- | ----------------------------- |
| Light mode default     | Dark mode with optional light |
| Pure white (#fff) text | Slightly off-white (#fafafa)  |
| Slow render animations | GPU-accelerated transforms    |
| Heavy box-shadows      | Subtle elevation with blur    |

---

## 📊 Chart Recommendations

### Primary Charts for AquaForge

| Data Type               | Best Chart      | Libraries          | Notes                                 |
| ----------------------- | --------------- | ------------------ | ------------------------------------- |
| **Scores Over Time**    | Line/Area Chart | Recharts, Chart.js | Use gold for positive trends          |
| **Team Comparisons**    | Horizontal Bar  | Recharts           | Sort by value, gold accent for winner |
| **Event Breakdown**     | Stacked Bar     | Recharts           | Navy palette gradients                |
| **Swimmer Performance** | Radar/Spider    | Recharts           | Limit to 6-8 metrics                  |
| **Live Updates**        | Streaming Area  | D3.js, CanvasJS    | Add pause button                      |

### Chart Color Palette
```javascript
const chartColors = {
  primary: '#D4AF37',    // Gold for main data
  secondary: '#2a4a6c',  // Navy-400 for secondary
  success: '#10B981',    // Improvements
  error: '#EF4444',      // Declines
  grid: '#1a3a5c',       // Navy-500 for gridlines
  axisTick: '#3a5a7c',   // Navy-300 for axis labels
};
```

### Accessibility for Charts
- ✓ Add pattern overlays for colorblind users
- ✓ Include data table fallback
- ✓ Hover tooltips with full context
- ⚠ Limit radar charts to 5-8 axes

---

## 🎬 Animation Guidelines

### Timing Tokens (Already Defined)
| Token                 | Duration | Curve    | Usage               |
| --------------------- | -------- | -------- | ------------------- |
| `--transition-fast`   | 150ms    | ease-out | Micro-interactions  |
| `--transition-base`   | 200ms    | ease-out | State changes       |
| `--transition-slow`   | 300ms    | ease-out | Panel transitions   |
| `--transition-spring` | 400ms    | spring   | Celebratory moments |

### Animation Rules
| ✅ Good                           | ❌ Bad                       |
| -------------------------------- | --------------------------- |
| Skeleton screens during load     | Blank frozen UI             |
| `animate-spin` on loaders        | `animate-bounce` on icons   |
| Fade-in for new content          | Instant appearance          |
| `prefers-reduced-motion` respect | Ignoring motion preferences |

### Loading States Pattern
```tsx
// Good: Skeleton with your existing class
<div className="skeleton h-12 w-full" />

// Good: Gold spinner
<div className="spinner" /> // Already in globals.css
```

---

## ✅ Pre-Delivery Checklist

### Visual Quality
- [ ] No emojis used as icons (use Heroicons/Lucide SVG)
- [ ] All icons from consistent set
- [ ] Brand logos correct
- [ ] Hover states don't cause layout shift
- [ ] Theme colors used directly (`bg-gold-muted` not `var()` wrapper)

### Interaction
- [ ] All clickable elements have `cursor-pointer`
- [ ] Hover states provide visual feedback
- [ ] Transitions are 150-300ms
- [ ] Focus states visible (`:focus-visible` styled)

### Dark Mode Specific
- [ ] Text contrast 4.5:1 minimum (already achieved with #fafafa on navy)
- [ ] Glass/transparent elements visible
- [ ] Borders visible (navy-500 minimum)
- [ ] No pure blacks or whites

### Layout
- [ ] Floating elements have edge spacing
- [ ] No content behind fixed navbar
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No horizontal scroll on mobile

### Accessibility
- [ ] Images have alt text
- [ ] Form inputs have labels
- [ ] Color not the only indicator
- [ ] `prefers-reduced-motion` respected

---

## 🏊 AquaForge-Specific Patterns

### Score Display (Hero Stats)
```css
/* Your existing .score-hero is excellent */
/* Enhancement: Add subtle animation on value change */
.score-value {
  transition: transform 0.3s ease-out;
}
.score-value.updated {
  animation: pulse-gold 0.5s ease-out;
}
```

### Championship Cards
- Use `glass-card` for swim meet cards
- `badge-gold` for winning teams
- `badge-success` for improved times
- `badge-error` for slower times

### Data Tables
- Use existing `.table` classes
- Add zebra striping: `tr:nth-child(even) td { background: rgba(255,255,255,0.02); }`
- Highlight personal bests with `--gold-muted` background

---

## 📱 Responsive Breakpoints

| Breakpoint | Width       | Layout Changes                |
| ---------- | ----------- | ----------------------------- |
| Mobile     | < 768px     | Sidebar hidden, stacked cards |
| Tablet     | 768-1024px  | Collapsed sidebar (72px)      |
| Desktop    | 1024-1440px | Full sidebar (260px)          |
| Large      | > 1440px    | Max-width containers          |

---

## 🔗 Quick Reference

### CSS Custom Properties
```css
/* Colors */
var(--navy-900) to var(--navy-300)
var(--gold-600) to var(--gold-200)
var(--success), var(--warning), var(--error), var(--info)

/* Shadows */
var(--shadow-sm), var(--shadow-md), var(--shadow-lg), var(--shadow-xl)
var(--shadow-gold), var(--shadow-gold-lg)

/* Transitions */
var(--transition-fast), var(--transition-base), var(--transition-slow)

/* Radius */
var(--radius-sm), var(--radius-md), var(--radius-lg), var(--radius-xl)
```

### Utility Classes
```css
/* Text */
.text-gold, .text-gold-muted, .text-success, .text-warning, .text-error, .text-muted

/* Backgrounds */
.bg-gold-muted, .bg-navy-600, .bg-navy-700, .bg-navy-800

/* Borders */
.border-gold, .border-navy

/* Special */
.gradient-text-gold, .glass-card, .skeleton
```
