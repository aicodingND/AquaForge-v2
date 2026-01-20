import os
import subprocess
import sys

def main():
    # Set API_URL from Render environment if available
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        print(f"Detected Render URL: {render_url}")
        os.environ["API_URL"] = render_url
    else:
        print("No RENDER_EXTERNAL_URL found, using default or existing API_URL")

    # Get the port from environment or default to 3000
    port = os.environ.get("PORT", "3000")
    print(f"Reflex App Starting on PORT {port}")
    
    # We also need to set the backend port if necessary, but 8000 is standard internal default.
    # If Render only exposes one port, the frontend must be on that port.
    
    # Run reflex init ensuring it completes
    print("Running reflex init...")
    init_res = subprocess.run("reflex init", shell=True)
    if init_res.returncode != 0:
        print("reflex init failed")
        sys.exit(init_res.returncode)

    # Run reflex
    # We pass --frontend-port to match Render's expected port
    cmd = f"reflex run --env prod --loglevel info --frontend-port {port}"
    print(f"Executing: {cmd}")
    
    # Use Popen or run. Run blocks until complete.
    # We want the python script to run as the process.
    run_res = subprocess.run(cmd, shell=True)
    sys.exit(run_res.returncode)

if __name__ == "__main__":
    main()
