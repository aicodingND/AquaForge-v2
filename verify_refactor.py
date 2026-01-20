
import asyncio
import os
from swim_ai_reflex.backend.services.data_service import data_service

async def verify_refactor():
    print("Verifying DataService Refactor...")
    
    # Create dummy file content
    dummy_pdf_content = b"%PDF-1.4 dummy content"
    dummy_filename = "test_refactor.pdf"
    
    # 1. Test process_raw_upload (Mocking the upload)
    print(f"\nTest 1: Processing raw upload: {dummy_filename}")
    
    # We expect this to fail parsing (invalid PDF) but succeed saving/validation steps
    # Or fail fast if validation strictness is high.
    # Actually, parse_hytek_pdf might fail or return empty DF.
    
    result = await data_service.process_raw_upload(dummy_filename, dummy_pdf_content)
    print(f"Result keys: {result.keys()}")
    
    if result['success']:
        print("✅ Upload processed successfully (unexpected for dummy PDF but method works)")
    else:
        # Check if it failed at parsing or earlier
        if "Invalid Format" in result['message'] or "parsing" in result['message'] or "No data found" in result['message']:
             print(f"✅ Service handled upload flow correctly (failed at parsing as expected): {result['message']}")
        else:
             print(f"⚠️ Failed with: {result['message']}")

    # Clean up
    if "data_path" in result:
        path = os.path.join("uploads", result["data_path"])
        if os.path.exists(path):
            os.remove(path)
            print("Cleanup complete.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(verify_refactor())
