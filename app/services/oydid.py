import subprocess
import json
import os
from fastapi import HTTPException

def run_oydid_command(args, input_data=None):
    """Helper to run oydid commands"""
    # Check for OYDID_LOCATION environment variable
    location = os.getenv("OYDID_LOCATION")
    if location and "--location" not in args and "-l" not in args:
        cmd = ["oydid"] + ["--location", location] + args
    else:
        cmd = ["oydid"] + args
    
    input_str = None
    if input_data:
        if isinstance(input_data, dict):
            input_str = json.dumps(input_data)
        else:
            input_str = str(input_data)

    try:
        print(f"DEBUG: Running oydid command: {cmd}")
        # if input_str:
        #     print(f"DEBUG: Input: {input_str}")
        
        process = subprocess.run(
            cmd,
            input=input_str,
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            error_msg = process.stderr.strip() if process.stderr else process.stdout.strip()
            print(f"DEBUG: Command failed with return code {process.returncode}")
            print(f"DEBUG: Error details: {error_msg}")
            # Attach the error message to the process object so the router can access it easily
            process.error_msg = error_msg
        
        return process
    except Exception as e:
        print(f"DEBUG: Exception during command execution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")
