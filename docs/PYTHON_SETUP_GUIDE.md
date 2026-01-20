# 🐍 Python Setup Guide for SwimAI

## Current Status

✅ **CSV files are ready** - No Python needed for those!
⚠️ **SwimAI app needs Python** to run (Reflex + pandas backend)

---

## Option 1: Quick Setup with Anaconda (Recommended)

### Step 1: Add Anaconda to PATH

1. **Find your Anaconda installation** (usually):
   - `C:\Users\Michael\anaconda3\`
   - `C:\ProgramData\Anaconda3\`
   - `C:\Users\Michael\AppData\Local\anaconda3\`

2. **Add to PATH:**
   - Open PowerShell as Administrator
   - Run:

   ```powershell
   $env:Path += ";C:\Users\Michael\anaconda3;C:\Users\Michael\anaconda3\Scripts"
   ```

   - Replace path with your actual Anaconda location

3. **Verify:**

   ```powershell
   conda --version
   python --version
   ```

### Step 2: Create SwimAI Environment

```bash
# Navigate to project
cd c:\Users\Michael\Desktop\SwimAi\swim_ai_reflex

# Create environment
conda create -n swimai python=3.11 -y

# Activate
conda activate swimai

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Run SwimAI

```bash
conda activate swimai
reflex run
```

---

## Option 2: Use Existing Anaconda Base

If you want to use your existing Anaconda base environment:

```bash
# Activate base
conda activate base

# Navigate to project
cd c:\Users\Michael\Desktop\SwimAi\swim_ai_reflex

# Install dependencies
pip install -r requirements.txt

# Run app
reflex run
```

---

## Option 3: Standalone Python Install

If Anaconda isn't working, install Python directly:

1. **Download:** <https://www.python.org/downloads/>
2. **Install** with "Add to PATH" checked
3. **Install dependencies:**

   ```bash
   cd c:\Users\Michael\Desktop\SwimAi\swim_ai_reflex
   pip install -r requirements.txt
   ```

4. **Run:**

   ```bash
   reflex run
   ```

---

## Required Dependencies

From `requirements.txt`:

- ✅ `reflex==0.8.22` - Web framework
- ✅ `pandas>=2.0.0` - Data processing
- ✅ `pdfplumber>=0.10.0` - PDF parsing
- ✅ `numpy>=1.24.0` - Numerical operations
- ⚠️ `gurobipy>=11.0.0` - Optional (exact optimization, requires license)

---

## Testing Python Setup

Run this to verify everything works:

```bash
python -c "import pandas; import pdfplumber; import numpy; print('✅ All dependencies installed!')"
```

---

## For Right Now

**Good news:** The CSV files I created are **already ready to use**!

You can:

1. **Upload them directly** to a running SwimAI instance
2. **Or** set up Python first, then run the app

The files are at:

- `c:\Users\Michael\Desktop\SwimAi\swim_ai_reflex\uploads\IDEAL_Seton_vs_Trinity_Christian_COMPLETE.csv`
- `c:\Users\Michael\Desktop\SwimAi\swim_ai_reflex\uploads\IDEAL_Trinity_Christian_vs_Seton_COMPLETE.csv`

---

## Quick Command Reference

```bash
# Find Anaconda
where conda

# Activate environment
conda activate swimai

# Install dependencies
pip install -r requirements.txt

# Run SwimAI
reflex run

# Run conversion script (future use)
python complete_conversion.py
```

---

## Troubleshooting

**"conda not found"**

- Anaconda not in PATH
- Add to PATH or use full path: `C:\Users\Michael\anaconda3\Scripts\conda.exe`

**"python not found"**

- Python not in PATH
- Use: `C:\Users\Michael\anaconda3\python.exe`

**"reflex not found"**

- Not installed in current environment
- Run: `pip install reflex==0.8.22`

---

## Next Steps

1. ✅ **CSV files are ready** (no action needed)
2. ⚠️ **To run SwimAI app:** Set up Python environment
3. 🚀 **To use conversion script:** Set up Python + run `complete_conversion.py`

Let me know if you need help with any step!
