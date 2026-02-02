# Dashboard Pages Design Guide

> Page-specific overrides for MASTER.md | AquaForge Championship Pages

---

## 📊 Analytics Page

### Chart Recommendations

| Component            | Chart Type     | Color Usage                          |
| -------------------- | -------------- | ------------------------------------ |
| **Score Comparison** | Horizontal Bar | Gold for winner, Navy-400 for others |
| **Time Trends**      | Area Chart     | Gold fill at 20% opacity             |
| **Event Breakdown**  | Stacked Bar    | Navy gradient (600→400)              |
| **Swimmer Radar**    | Spider/Radar   | Gold primary, max 6 metrics          |

### Layout Pattern
```
┌─────────────────────────────────────────┐
│  Score Hero Card (score-hero class)     │
│  [Team A: 245]  vs  [Team B: 198]       │
├───────────────┬─────────────────────────┤
│ Quick Stats   │  Main Chart Area        │
│ (3 stat cards)│  (ChampionshipAnalytics)│
├───────────────┴─────────────────────────┤
│  Data Table (RosterTable)               │
└─────────────────────────────────────────┘
```

### Performance Patterns
- Use `<Suspense>` around ChampionshipAnalytics
- Skeleton loaders for stat cards during fetch
- Lazy load below-fold charts

---

## ⚙️ Optimize Page

### Optimizer Panel Patterns

| State        | Visual Treatment                       |
| ------------ | -------------------------------------- |
| **Idle**     | btn-outline, muted text                |
| **Running**  | btn-gold with spinner, pulse animation |
| **Complete** | badge-success, score highlight         |
| **Error**    | badge-error, error message             |

### Loading State
```tsx
// During optimization
<div className="glass-card animate-pulse-gold">
  <div className="spinner" />
  <p className="text-gold">Optimizing lineup...</p>
</div>
```

### Results Display
- Highlight improvements with `--success` badge
- Show delta with `text-success` or `text-error`
- Use `transition-spring` for celebratory moments

---

## 🏊 Meet Selector Page

### Card Grid Pattern
```tsx
// Use glass-card + card-interactive
<div className="glass-card card-interactive">
  <h3>VISAA Championship</h3>
  <p className="text-muted">January 2026</p>
  <span className="badge-gold">12 Events</span>
</div>
```

### Grid Layout
- Desktop: 3-column grid
- Tablet: 2-column grid
- Mobile: 1-column stack

---

## 📋 Results Page

### Table Enhancements
```css
/* Highlight personal bests */
.row-pb {
  background: var(--gold-muted);
  border-left: 3px solid var(--gold-500);
}

/* Highlight DQs */
.row-dq {
  background: var(--error-muted);
  color: var(--error);
}
```

### Export Actions
- Use `btn-outline` for secondary actions
- `btn-gold` only for primary action (Export)

---

## 🎯 Next.js Specific Patterns

### Data Fetching
```tsx
// ✅ Good: Server Component fetch
async function ChampionshipPage() {
  const data = await fetchChampionshipData();
  return <ChampionshipAnalytics data={data} />;
}

// ❌ Bad: Client-side useEffect
useEffect(() => { fetchData() }, []) // Avoid
```

### Streaming with Suspense
```tsx
// ✅ Good: Stream heavy components
<Suspense fallback={<div className="skeleton h-64" />}>
  <ChampionshipAnalytics />
</Suspense>
```

### Image Optimization
```tsx
// ✅ Use next/image for team logos
import Image from 'next/image';
<Image src={teamLogo} alt="Team Logo" width={48} height={48} />
```

---

## 📱 Mobile Overrides

### Navigation
- Bottom navigation bar on mobile
- Swipe gestures for page transitions
- Floating action button for optimize

### Cards
- Full-width cards on mobile
- Collapsible sections for data tables
- Touch-friendly tap targets (min 44px)

### Tables
- Horizontal scroll with shadow indicators
- Card-based view for small screens
- Use `MobileRosterCard.tsx` pattern
