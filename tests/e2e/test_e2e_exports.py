"""
E2E Test - Export Functions
Tests CSV and XLSX export functionality
"""

import sys

sys.path.insert(0, r"c:\Users\Michael\Desktop\AquaForgeFinal")

from swim_ai_reflex.backend.services.export_service import export_service


def test_exports():
    print("=" * 60)
    print("E2E EXPORT TEST")
    print("=" * 60)

    # Mock optimization results
    results = [
        {
            "swimmer": "Lionel Martinez",
            "event": "100 Yard Freestyle",
            "time": 47.16,
            "team": "seton",
            "points": 8.0,
            "place": 1,
        },
        {
            "swimmer": "Bennett Ellis",
            "event": "100 Yard Freestyle",
            "time": 66.1,
            "team": "seton",
            "points": 2.0,
            "place": 6,
        },
        {
            "swimmer": "Caleb Fiala",
            "event": "100 Yard Freestyle",
            "time": 50.14,
            "team": "opponent",
            "points": 6.0,
            "place": 2,
        },
        {
            "swimmer": "Brenton Anderson",
            "event": "100 Yard Freestyle",
            "time": 53.75,
            "team": "opponent",
            "points": 5.0,
            "place": 3,
        },
    ]

    seton_score = 124
    opponent_score = 108

    print("\n1. Testing CSV Export...")
    try:
        csv_content = export_service.to_csv(
            results,
            seton_score,
            opponent_score,
            metadata={"Seton Team": "Seton", "Opponent Team": "Immanuel"},
        )
        print(f"CSV generated: {len(csv_content)} bytes")
        print(f"First 200 chars: {csv_content[:200]}...")
        print("✓ CSV export working")
    except Exception as e:
        print(f"✗ CSV export failed: {e}")

    print("\n2. Testing XLSX Export...")
    try:
        xlsx_data = export_service.to_xlsx(
            results,
            seton_score,
            opponent_score,
            seton_team_name="Seton",
            opponent_team_name="Immanuel",
        )
        if xlsx_data:
            print(f"XLSX generated: {len(xlsx_data)} bytes")
            print("✓ XLSX export working")
        else:
            print("! XLSX export returned empty")
    except Exception as e:
        print(f"✗ XLSX export failed: {e}")

    print("\n3. Testing HTML Export...")
    try:
        html_content = export_service.to_html_table(
            results, seton_score, opponent_score
        )
        print(f"HTML generated: {len(html_content)} bytes")
        print("✓ HTML export working")
    except Exception as e:
        print(f"✗ HTML export failed: {e}")

    print("\n" + "=" * 60)
    print("EXPORT TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_exports()
