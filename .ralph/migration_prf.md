# Ralph PRF: Reflex to Next.js Migration

## Objective
Migrate AquaForge from Reflex to a standalone Next.js frontend + FastAPI backend architecture.

## Success Criteria
1. **FastAPI backend runs standalone** on port 8001 with all endpoints functional
2. **Next.js frontend scaffolded** with proper project structure
3. **Core pages created**: Dashboard, Upload, Optimize, Results
4. **API integration working**: Frontend successfully calls backend
5. **Build succeeds**: Both frontend and backend build without errors
6. **File upload works**: Can upload Excel files through new frontend

## Phase 1: Backend Standalone Verification
**Goal**: Ensure FastAPI works completely independently of Reflex

### Tasks
- [ ] 1.1 Verify `python run_server.py --mode api` starts successfully
- [ ] 1.2 Test `/health` endpoint returns OK
- [ ] 1.3 Test `/api/v1/optimize/backends` returns backend list
- [ ] 1.4 Test `/api/v1/data/upload` accepts file uploads
- [ ] 1.5 Run `pytest tests/test_api_integration.py` - all pass

### Validation Command
```bash
python ralph.py --check-complete --conditions api_starts
```

## Phase 2: Next.js Frontend Scaffold
**Goal**: Create the Next.js project with proper structure

### Tasks
- [ ] 2.1 Create `frontend/` directory
- [ ] 2.2 Initialize Next.js with TypeScript: `npx create-next-app@latest ./frontend --typescript --tailwind --app --eslint --src-dir`
- [ ] 2.3 Install dependencies: `shadcn/ui`, `zustand`, `axios`
- [ ] 2.4 Create API client in `frontend/src/lib/api.ts`
- [ ] 2.5 Configure CORS in backend for `localhost:3001`

### Target Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx           # Dashboard
│   │   ├── layout.tsx         # Root layout
│   │   ├── upload/page.tsx    # File upload
│   │   ├── optimize/page.tsx  # Optimization controls
│   │   └── results/page.tsx   # Results display
│   ├── components/
│   │   ├── ui/               # shadcn components
│   │   ├── FileUpload.tsx
│   │   ├── TeamCard.tsx
│   │   └── OptimizePanel.tsx
│   ├── lib/
│   │   ├── api.ts            # API client
│   │   └── utils.ts
│   └── stores/
│       └── appStore.ts       # Zustand store
├── package.json
└── tailwind.config.ts
```

### Validation
```bash
cd frontend && npm run build
```

## Phase 3: Core UI Components
**Goal**: Port essential Reflex components to React

### Components to Port
| Reflex Component | React Component | Priority |
|------------------|-----------------|----------|
| `upload.py` | `FileUpload.tsx` | P0 |
| `team_management.py` | `TeamCard.tsx` | P0 |
| `optimize.py` | `OptimizePanel.tsx` | P0 |
| `dashboard.py` | `Dashboard.tsx` (page) | P0 |
| `sidebar.py` | `Sidebar.tsx` | P1 |
| `analysis.py` | `Analysis.tsx` | P1 |
| `impressive_stats.py` | `StatsCard.tsx` | P2 |

### Tasks
- [ ] 3.1 Create `FileUpload.tsx` with drag-and-drop
- [ ] 3.2 Create `TeamCard.tsx` to display loaded team data
- [ ] 3.3 Create `OptimizePanel.tsx` with optimizer controls
- [ ] 3.4 Create Zustand store with upload/optimization state
- [ ] 3.5 Wire up API calls to backend

### Validation
```bash
cd frontend && npm run dev
# Manually verify pages render
```

## Phase 4: API Integration
**Goal**: Frontend fully communicates with backend

### API Client (`frontend/src/lib/api.ts`)
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';

export const api = {
  health: () => fetch(`${API_BASE}/health`),
  
  upload: (file: File, teamType: 'seton' | 'opponent') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('team_type', teamType);
    return fetch(`${API_BASE}/data/upload`, { method: 'POST', body: formData });
  },
  
  optimize: (data: OptimizeRequest) => 
    fetch(`${API_BASE}/optimize`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data) 
    }),
    
  export: (format: 'csv' | 'pdf', results: any) =>
    fetch(`${API_BASE}/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format, results })
    }),
};
```

### Tasks
- [ ] 4.1 Implement API client with all endpoints
- [ ] 4.2 Add error handling and loading states
- [ ] 4.3 Test file upload end-to-end
- [ ] 4.4 Test optimization end-to-end
- [ ] 4.5 Test export functionality

### Validation
```bash
# Backend running on 8001, frontend on 3001
# Upload file, run optimization, export - all work
```

## Phase 5: Styling and Polish
**Goal**: Match or exceed current Reflex UI quality

### Design System
- Colors: Navy blue primary, gold accent, dark mode
- Fonts: Inter, Outfit (already loaded)
- Effects: Glassmorphism, subtle animations

### Tasks
- [ ] 5.1 Configure Tailwind with custom theme
- [ ] 5.2 Add glassmorphism card styles
- [ ] 5.3 Add loading animations
- [ ] 5.4 Responsive design for mobile
- [ ] 5.5 Dark mode support

## Boundaries
- **DO NOT** modify the existing Reflex code in this phase
- **DO NOT** touch `swim_ai_reflex/` directory  
- **DO NOT** break the existing app - it should continue working
- **FOCUS** on creating new `frontend/` directory only
- **KEEP** backend changes minimal (CORS config only)

## Current Status
- Phase: 1 (Backend Verification)
- Iteration: 0
- Last Updated: 2026-01-08

## Ralph Loop Commands
```bash
# Check Phase 1 complete
python ralph.py --check-complete --conditions api_starts

# Check all phases
python ralph.py --check-complete --conditions build_succeeds api_starts tests_pass
```
