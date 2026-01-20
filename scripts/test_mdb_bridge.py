import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

DB_PATH = "/Volumes/Miguel/swimdatadump/Database Backups/SSTdata.mdb"


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    print(f"Connecting to {DB_PATH}...")
    connector = MDBConnector(DB_PATH)

    try:
        tables = connector.get_tables()
        print(f"Found {len(tables)} tables:")
        print(", ".join(tables[:10]) + "...")

        # Try to find relevant tables
        meet_table = next(
            (t for t in tables if "meet" in t.lower() or "MEET" in t), None
        )

        if meet_table:
            print(f"\nReading table: {meet_table}")
            df = connector.read_table(meet_table)
            print(f"Shape: {df.shape}")
            print("Columns:", df.columns.tolist())
            print("\nHead:")
            print(df.head())

            # Check for Meet 512
            # Usually 'Meet' table has 'Meet Name' or similar
            # Iterate columns to find name
            name_col = next(
                (c for c in df.columns if "name" in c.lower() or "title" in c.lower()),
                None,
            )
            if name_col:
                meet_512 = df[
                    df[name_col].astype(str).str.contains("VCAC", case=False, na=False)
                ]
                if not meet_512.empty:
                    print(f"\nFound VCAC Meets ({len(meet_512)}):")
                    print(
                        meet_512[
                            [name_col]
                            + [c for c in df.columns if "date" in c.lower()][:2]
                        ]
                    )
        else:
            print("Could not find a 'Meet' table.")

    except Exception as e:
        print(f"Error accessing MDB: {e}")


if __name__ == "__main__":
    main()
