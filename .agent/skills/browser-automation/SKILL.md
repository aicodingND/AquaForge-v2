---
name: Stagehand Browser Automation
description: AI-powered browser automation for resilient web scraping and testing
triggers:
  - scrape website
  - browser automation
  - web data extraction
  - natural language selector
---

# Stagehand Browser Automation Skill 🎭

Use AI-powered natural language for browser automation instead of brittle CSS selectors.

---

## Overview

Stagehand is a Playwright wrapper that enables:
- **Natural language actions** instead of selectors
- **AI-powered element detection**
- **Resilient to UI changes**
- **Structured data extraction**

---

## Installation

```bash
npm install @anthropic-ai/stagehand
```

Or use with existing Playwright:
```bash
pip install playwright stagehand-python
```

---

## Usage Patterns

### Traditional Playwright (Brittle)

```python
# Breaks when UI changes
page.click("#submit-btn")
page.fill("input[name='search']", "VCAC 2026")
```

### Stagehand (Resilient)

```python
# Survives UI changes
await page.act("Click the submit button")
await page.act("Type 'VCAC 2026' in the search box")
```

---

## Key Methods

### act() - Perform Actions

```python
# Click by description
await page.act("Click the login button")

# Fill form fields
await page.act("Enter 'coach@seton.org' in the email field")
await page.act("Enter password in the password field")

# Navigate
await page.act("Click on the Swimmers tab")
```

### extract() - Get Structured Data

```python
# Extract data with schema
swimmers = await page.extract({
    "prompt": "Get all swimmers from this roster",
    "schema": {
        "swimmers": [{
            "name": "string",
            "grade": "number",
            "events": ["string"]
        }]
    }
})
```

### observe() - Understand Page

```python
# Get page state
state = await page.observe("What are the main sections on this page?")
```

---

## AquaForge Use Cases

### 1. SwimCloud Scraping

```python
from stagehand import Stagehand

async def scrape_swimcloud_roster(team_url: str):
    stagehand = Stagehand()
    page = await stagehand.page(team_url)
    
    # Navigate to roster
    await page.act("Click on the Roster tab")
    
    # Extract swimmer data
    roster = await page.extract({
        "prompt": "Extract all swimmers with their best times",
        "schema": {
            "swimmers": [{
                "name": "string",
                "events": [{
                    "name": "string",
                    "time": "string"
                }]
            }]
        }
    })
    
    return roster
```

### 2. Meet Results Scraping

```python
async def scrape_meet_results(meet_url: str):
    page = await stagehand.page(meet_url)
    
    results = await page.extract({
        "prompt": "Extract all event results with places and times",
        "schema": {
            "events": [{
                "name": "string",
                "results": [{
                    "place": "number",
                    "swimmer": "string",
                    "team": "string",
                    "time": "string"
                }]
            }]
        }
    })
    
    return results
```

### 3. E2E Testing with Natural Language

```python
async def test_optimization_flow():
    page = await stagehand.page("http://localhost:3000")
    
    # Upload psych sheet
    await page.act("Click the Upload button")
    await page.act("Select the psych sheet file")
    await page.act("Click Submit")
    
    # Wait for processing
    await page.act("Wait for the optimization to complete")
    
    # Verify results
    results = await page.extract({
        "prompt": "Get the projected score from the results",
        "schema": {
            "our_score": "number",
            "opponent_score": "number"
        }
    })
    
    assert results["our_score"] > 0
```

---

## Comparison with AgentQL

| Feature        | Stagehand           | AgentQL         |
| -------------- | ------------------- | --------------- |
| Approach       | Action descriptions | Query syntax    |
| Best for       | Actions & workflows | Data extraction |
| Learning curve | Lower               | Higher          |
| Precision      | Good                | Excellent       |

### AgentQL Example

```python
# AgentQL uses query syntax
results = await page.query("""
{
    swimmers[] {
        name
        grade
        events[] {
            name
            time
        }
    }
}
""")
```

---

## Integration with AquaForge Scraper

Enhance existing scraper at `scripts/scrape_swimcloud.py`:

```python
# Add natural language fallback
async def get_roster_with_fallback(page):
    try:
        # Try traditional selectors first (faster)
        roster = await scrape_with_selectors(page)
    except Exception:
        # Fall back to AI-powered extraction
        roster = await page.extract({
            "prompt": "Extract swimmer roster from this page",
            "schema": roster_schema
        })
    return roster
```

---

## Best Practices

1. **Use traditional selectors when stable** - Faster
2. **Use AI for dynamic/changing UIs** - More resilient
3. **Cache extracted schemas** - Reduce AI calls
4. **Combine with explicit waits** - Ensure page loaded

---

_Skill: stagehand-browser | Version: 1.0 | Requires: @anthropic-ai/stagehand_
