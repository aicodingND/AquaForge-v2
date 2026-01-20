import logging
import shutil
import subprocess
from io import StringIO
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


class MDBConnector:
    """
    Bridge to read Microsoft Access (.mdb) databases using mdb-tools.

    Requirements:
        - 'mdb-export' command line tool must be installed (e.g. `brew install mdbtools`)
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._check_dependency()

    def _check_dependency(self):
        """Check if mdb-export is available."""
        if not shutil.which("mdb-export"):
            raise RuntimeError(
                "mdb-export not found. Please install mdbtools (e.g., `brew install mdbtools`)."
            )

    def get_tables(self) -> List[str]:
        """List all tables in the MDB database."""
        if not shutil.which("mdb-tables"):
            logger.warning("mdb-tables not found, cannot list tables.")
            return []

        try:
            result = subprocess.run(
                ["mdb-tables", "-1", self.db_path],
                capture_output=True,
                text=True,
                check=True,
            )
            return [t.strip() for t in result.stdout.splitlines() if t.strip()]
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list tables: {e}")
            raise

    def read_table(self, table_name: str) -> pd.DataFrame:
        """
        Read a table from the MDB database into a pandas DataFrame.

        Args:
            table_name: Name of the table to export.

        Returns:
            pd.DataFrame: The table data.
        """
        try:
            # Run mdb-export to dump table to CSV format
            # -I postgres: Insert statements (no)
            # Default is CSV
            cmd = ["mdb-export", self.db_path, table_name]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse CSV output directly into pandas
            # mdb-export outputs standard CSV
            csv_io = StringIO(result.stdout)
            df = pd.read_csv(csv_io)

            return df

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to export table '{table_name}': {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Error parsing table '{table_name}': {e}")
            raise

    def verify_connection(self) -> bool:
        """Verify that the database can be read."""
        try:
            tables = self.get_tables()
            return len(tables) > 0
        except Exception:
            return False
