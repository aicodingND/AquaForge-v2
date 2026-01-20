
import asyncio
from swim_ai_reflex.backend.services.data_service import data_service

async def verify_errors():
    print("Verifying DataService Error Handling...")
    
    # Test 1: File Not Found
    print("\nTest 1: Non-existent file")
    result = await data_service.load_roster_from_path("non_existent_file.csv")
    print(f"Result: {result}")
    if not result['success'] and "File not found" in result['message']:
        print("✅ Correctly handled file not found.")
    else:
        print("❌ Failed to handle file not found correctly.")

    # Test 2: Unsupported File Type
    print("\nTest 2: Unsupported extension")
    result = await data_service.load_roster_from_path("test.xyz")
    print(f"Result: {result}")
    if not result['success'] and "Unsupported file type" in result['message']:
        print("✅ Correctly handled unsupported file type.")
    else:
        print("❌ Failed to handle unsupported file type.")

    print("\nVerification Complete.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(verify_errors())
