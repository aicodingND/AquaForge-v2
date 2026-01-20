# Performance Optimization Plan

## SwimAi Reflex - System Lag Optimization

**Date**: 2025-12-14
**Objective**: Optimize system performance by identifying and managing critical vs non-essential components

---

## 🎯 CRITICAL COMPONENTS (Keep Active)

These are essential for core functionality and will be optimized:

### 1. **Core State Management** (ESSENTIAL)

- `state.py` - Main application state
- `states/ui_state.py` - UI state management
- `states/roster_state.py` - Team roster management
- `states/optimization_state.py` - Optimization logic
- **Action**: ✅ Keep active, optimize memory usage

### 2. **File Upload & Parsing** (ESSENTIAL)

- `state.handle_upload()`
- `backend/core/hytek_pdf_parser.py`
- `backend/utils/file_manager.py`
- **Action**: ✅ Keep active, add streaming for large files

### 3. **Core Optimization Engine** (ESSENTIAL)

- `backend/core/optimizer.py`
- `backend/core/scoring.py`
- `backend/core/rules.py`
- `backend/services/optimization_service.py`
- **Action**: ✅ Keep active, optimize cache

---

## ⏸️ NON-CRITICAL COMPONENTS (Pause/Lazy Load)

These can be deferred or loaded on-demand:

### 1. **Analytics Service** (DEFER)

- `backend/core/analytics.py` - Advanced analytics
- `backend/services/analytics_service.py`
- **Action**: ⏸️ Lazy load only when analytics page is accessed
- **Performance Impact**: Low priority for initial load

### 2. **Export Services** (DEFER)

- `backend/services/export_service.py` - CSV, Email, PDF export
- `state.export_csv()`, `state.export_email()`, `state.export_pdf()`
- **Action**: ⏸️ Load only when export is triggered
- **Performance Impact**: Not needed until results exist

### 3. **AI Coach & Advanced Features** (DEFER)

- `backend/utils/ai_coach.py`
- `backend/core/monte_carlo.py`
- `backend/utils/lineup_completion.py`
- **Action**: ⏸️ Disable or lazy load
- **Performance Impact**: CPU/memory intensive, optional

### 4. **PDF Generation** (DEFER)

- `backend/utils/pdf_generator.py`
- **Action**: ⏸️ Load only when exporting
- **Performance Impact**: Heavy dependency, rarely used

### 5. **Test Data & Validation** (DISABLE)

- `backend/utils/test_data_generator.py`
- `state.load_test_data()` (only for demos)
- **Action**: 🛑 Comment out in production mode
- **Performance Impact**: Unnecessary in production

---

## 🚀 PERFORMANCE OPTIMIZATIONS

### Immediate Actions

1. **Lazy Import Heavy Dependencies**
   - Move PDF parsing imports to function scope
   - Defer analytics/export imports until needed

2. **Optimize State Updates**
   - Reduce frequent `yield` calls
   - Batch state updates where possible

3. **Cache Management**
   - Implement LRU cache with size limits
   - Clear stale cache entries automatically

4. **Async Optimization**
   - Use `asyncio.gather()` for parallel operations
   - Implement proper task cancellation

5. **Memory Management**
   - Limit stored roster data size
   - Clear optimization results after export
   - Implement data pagination for large datasets

---

## 📊 Performance Metrics

**Target Improvements:**

- Initial page load: < 2 seconds
- Upload processing: < 5 seconds for typical PDF
- Optimization run: < 10 seconds for standard meet
- Memory usage: < 500MB for typical session

**Current Bottlenecks Identified:**

1. PDF parsing blocking main thread
2. Analytics computed eagerly (not needed initially)
3. Export services loaded but rarely used
4. Test data loading in production mode

---

## ✅ Implementation Checklist

- [ ] Create performance config file
- [ ] Implement lazy loading for analytics
- [ ] Defer export service initialization
- [ ] Optimize state update frequency
- [ ] Add memory monitoring
- [ ] Implement cache size limits
- [ ] Profile and benchmark improvements
- [ ] Add performance logging
