"""
Data Service
Handles file upload processing, validation, and data loading.
"""

from typing import Any

import pandas as pd

from swim_ai_reflex.backend.services.base_service import BaseService
from swim_ai_reflex.backend.utils.data_validator import validate_roster_data
from swim_ai_reflex.backend.utils.file_manager import FileManager


class DataService(BaseService):
    """
    Service for managing data ingestion and validation.
    """

    def __init__(self, upload_dir: str):
        super().__init__()
        self.file_manager = FileManager(upload_dir)

    def process_upload(
        self, seton_file, opp_file, combined_file, options: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Orchestrates file saving, loading, validation, and health reporting.

        Args:
            seton_file: UploadFile for Seton roster
            opp_file: UploadFile for Opponent roster
            combined_file: UploadFile for combined meet results
            options: Dictionary of loading options (filters, etc.)

        Returns:
            Standard service response with loaded data and health report
        """
        paths = {}

        try:
            # 1. Save Files
            if combined_file:
                paths["combined_path"] = self.file_manager.save_file(
                    combined_file, "combined_"
                )
                self.log_info(f"Saved combined file to {paths['combined_path']}")
            else:
                if seton_file:
                    paths["seton_path"] = self.file_manager.save_file(
                        seton_file, "seton_"
                    )
                    self.log_info(f"Saved Seton file to {paths['seton_path']}")
                if opp_file:
                    paths["opp_path"] = self.file_manager.save_file(opp_file, "opp_")
                    self.log_info(f"Saved Opponent file to {paths['opp_path']}")

            # 2. Load Data
            filters = options.get("filters")

            try:
                seton_df, opp_df = self.file_manager.load_data(
                    seton_path=paths.get("seton_path"),
                    opp_path=paths.get("opp_path"),
                    combined_path=paths.get("combined_path"),
                    filters=filters,
                )
            except Exception as e:
                return self._error(
                    f"Failed to load data: {str(e)}", code="DATA_LOAD_ERROR"
                )

            # 3. Validate & Health Report
            seton_report = validate_roster_data(seton_df)
            opp_report = (
                validate_roster_data(opp_df)
                if opp_df is not None and not opp_df.empty
                else {"warnings": [], "errors": []}
            )

            # Aggregate Report
            health_report = {
                "seton_warnings": seton_report.get("warnings", []),
                "seton_errors": seton_report.get("errors", []),
                "opponent_warnings": opp_report.get("warnings", []),
                "opponent_errors": opp_report.get("errors", []),
                "critical_error": False,
            }

            # Critical Check
            if health_report["seton_errors"]:
                health_report["critical_error"] = True
                self.log_warning(
                    f"Critical validation errors in Seton data: {health_report['seton_errors']}"
                )

            # 4. Construct Response Data
            response_data = {
                "seton": seton_df,
                "opponent": opp_df,
                "report": health_report,
                "paths": paths,
            }

            if health_report["critical_error"]:
                return self._error(
                    "Critical validation errors found in uploaded data",
                    code="VALIDATION_ERROR",
                    details=health_report,
                )

            return self._success(
                data=response_data,
                message="Files processed and data loaded successfully",
                metadata={"seton_count": len(seton_df) if seton_df is not None else 0},
            )

        except Exception as e:
            import traceback

            return self._error(
                f"Unexpected error during upload processing: {str(e)}",
                code="INTERNAL_ERROR",
                details=traceback.format_exc(),
            )

    async def process_raw_upload(
        self, filename: str, file_data: bytes
    ) -> dict[str, Any]:
        """
        Process a raw file upload: Save -> Validate -> Parse.
        Designed for Reflex UploadFile handling.
        """
        import os

        from swim_ai_reflex.backend.config import get_config
        from swim_ai_reflex.backend.utils.validation import (
            safe_join_path,
            sanitize_filename,
            validate_file_extension,
            validate_file_size,
        )

        config = get_config()

        try:
            # 1. Validate Extension
            if not validate_file_extension(
                filename, set(config.security.allowed_extensions)
            ):
                return self._error(
                    f"Invalid file type: {filename}", code="INVALID_FILE_TYPE"
                )

            # 2. Sanitize Filename
            safe_name = sanitize_filename(filename)
            if not safe_name:
                return self._error(
                    f"Invalid filename: {filename}", code="INVALID_FILENAME"
                )

            # 3. Safe Path Construction
            try:
                filepath = safe_join_path(self.file_manager.upload_dir, safe_name)
            except ValueError as e:
                return self._error(f"Security error: {str(e)}", code="SECURITY_ERROR")

            # 4. Save File
            os.makedirs(self.file_manager.upload_dir, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(file_data)

            # 5. Validate Size
            if not validate_file_size(filepath, config.security.max_file_size_mb):
                os.remove(filepath)
                return self._error(
                    f"File too large: {safe_name} (exceeds {config.security.max_file_size_mb}MB)",
                    code="FILE_TOO_LARGE",
                )

            # 6. Parse
            # Reuse existing load logic
            parse_result = await self.load_roster_from_path(filepath)

            # Attach filepath to result for UI reference
            if parse_result["success"]:
                parse_result["data_path"] = safe_name  # Return safe filename

            return parse_result

        except Exception as e:
            return self._error(
                f"Upload processing failed: {str(e)}", code="UPLOAD_ERROR"
            )

    async def load_roster_from_path(self, filepath: str) -> dict[str, Any]:
        """
        Load and parse a roster file from a local path.

        Args:
            filepath: Absolute path to the file

        Returns:
            Standard response with parsed data
        """
        try:
            # We can reuse FileManager.load_data but it expects specific keys
            # Or use the specific parser directly if we know the type
            # For now, let's keep it simple and support PDF/CSV

            if filepath.lower().endswith(".pdf"):
                import asyncio

                from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf

                # Parse in thread
                df = await asyncio.to_thread(parse_hytek_pdf, filepath)

                if df.empty:
                    return self._error(
                        f"No data found in {filepath}", code="EMPTY_ROSTER"
                    )

                # DEDUPLICATE: Remove duplicate entries (same swimmer + event from same meet)
                # Keep the BEST (fastest) time for each swimmer per event
                original_count = len(df)
                if (
                    "swimmer" in df.columns
                    and "event" in df.columns
                    and "time" in df.columns
                ):
                    # Sort by time (ascending = fastest first) before deduplication
                    df = df.sort_values("time", ascending=True)

                    # Keep first occurrence (fastest time) for each swimmer+event
                    df = df.drop_duplicates(subset=["swimmer", "event"], keep="first")
                    duplicates_removed = original_count - len(df)

                    if duplicates_removed > 0:
                        self.log_warning(
                            f"Removed {duplicates_removed} duplicate entries (kept best times)"
                        )

                return self._success(
                    data=df,
                    message=f"Successfully loaded {len(df)} entries from {filepath}"
                    + (
                        f" ({duplicates_removed} duplicates removed)"
                        if duplicates_removed > 0
                        else ""
                    ),
                )

            elif filepath.lower().endswith(".json"):
                # Handle JSON files - championship psych sheets have specific structure
                import json

                with open(filepath, encoding="utf-8") as f:
                    json_data = json.load(f)

                # Check if this is a championship psych sheet (has 'entries' array)
                if "entries" in json_data and isinstance(json_data["entries"], list):
                    entries = json_data["entries"]

                    if not entries:
                        return self._error(
                            f"No entries found in {filepath}", code="EMPTY_ROSTER"
                        )

                    # Use centralized entry schema for normalization
                    from swim_ai_reflex.backend.services.shared.entry_schema import (
                        normalize_entry_dict,
                    )

                    # Map entries using centralized normalization
                    mapped_entries = []
                    for entry in entries:
                        norm = normalize_entry_dict(entry)
                        mapped_entry = {
                            "swimmer": norm["swimmer"],
                            "event": norm["event"],
                            "time": norm["time"],
                            "team": norm["team"],  # Code
                            "team_name": norm.get("team_name", ""),
                            "grade": norm.get("grade"),
                            "gender": norm.get("gender"),
                            "is_diver": norm.get("is_diver", False),
                            "is_varsity": entry.get("is_varsity", True),  # Pass through
                        }
                        mapped_entries.append(mapped_entry)

                    df = pd.DataFrame(mapped_entries)

                    # Extract teams list for championship metadata
                    teams = json_data.get("teams", [])
                    meet_name = json_data.get("meet", "Championship")

                    self.log_info(
                        f"Championship psych sheet loaded: {len(df)} entries, {len(teams)} teams"
                    )

                    return self._success(
                        data=df,
                        message=f"Championship psych sheet loaded ({len(df)} entries from {len(teams)} teams)",
                        metadata={
                            "teams": teams,
                            "meet_name": meet_name,
                            "date": json_data.get("date"),
                            "total_entries": json_data.get("total_entries", len(df)),
                        },
                    )
                else:
                    # Fallback: assume array of entries or simple structure
                    if isinstance(json_data, list):
                        df = pd.DataFrame(json_data)
                    else:
                        return self._error(
                            f"Unsupported JSON structure in {filepath}",
                            code="INVALID_JSON_FORMAT",
                        )

                    return self._success(
                        data=df, message=f"JSON loaded successfully ({len(df)} entries)"
                    )

            elif filepath.lower().endswith(".csv"):
                df = pd.read_csv(filepath)
                self.log_info(f"DEBUG CSV: columns={df.columns.tolist()}")
                self.log_info(f"DEBUG CSV: rows={len(df)}")
                self.log_info(
                    f"DEBUG CSV: sample={df.head(1).to_dict('records') if len(df) > 0 else 'EMPTY'}"
                )

                # Map common column name variations to standard names
                column_mapping = {
                    "Swimmer": "swimmer",
                    "Name": "swimmer",
                    "SWIMMER": "swimmer",
                    "Event": "event",
                    "EVENT": "event",
                    "Time": "time",
                    "TIME": "time",
                    "Seed Time": "time",
                    "SeedTime": "time",
                    "Team": "team",
                    "TEAM": "team",
                    "School": "team",
                }

                # Apply column mapping
                df = df.rename(columns=column_mapping)
                self.log_info(f"DEBUG CSV: after mapping columns={df.columns.tolist()}")

                # Filter out duplicate header rows (where swimmer='swimmer')
                if "swimmer" in df.columns:
                    before_count = len(df)
                    df = df[df["swimmer"].astype(str).str.lower() != "swimmer"]
                    if len(df) < before_count:
                        self.log_info(
                            f"DEBUG CSV: filtered out {before_count - len(df)} duplicate header rows"
                        )

                # Extract teams metadata for championship mode (like JSON parser does)
                teams = []
                if "team" in df.columns and not df.empty:
                    # Get unique team codes
                    unique_teams = df["team"].dropna().unique().tolist()
                    teams = sorted([str(t) for t in unique_teams if str(t).strip()])
                    self.log_info(
                        f"Championship CSV: extracted {len(teams)} teams: {teams}"
                    )

                # Return with metadata if teams found (championship mode)
                if teams:
                    return self._success(
                        data=df,
                        message=f"Championship CSV loaded ({len(df)} entries from {len(teams)} teams)",
                        metadata={
                            "teams": teams,
                            "meet_name": "Championship",
                            "total_entries": len(df),
                        },
                    )
                else:
                    # Dual meet mode - no teams metadata
                    return self._success(
                        data=df, message=f"CSV loaded successfully ({len(df)} entries)"
                    )

            elif filepath.lower().endswith((".xlsx", ".xls")):
                # Use the dynamic Excel loader
                import asyncio

                from swim_ai_reflex.backend.utils.file_loader import load_file_dynamic

                df, diag = await asyncio.to_thread(load_file_dynamic, filepath)

                if df.empty:
                    return self._error(
                        f"No data found in {filepath}", code="EMPTY_ROSTER"
                    )

                self.log_info(
                    f"Excel loaded: sheet='{diag.get('chosen_sheet')}', cols={diag.get('cols')}"
                )

                # Extract teams metadata for championship mode (like CSV/JSON parsers do)
                teams = []
                if "team" in df.columns and not df.empty:
                    # Get unique team codes
                    unique_teams = df["team"].dropna().unique().tolist()
                    teams = sorted([str(t) for t in unique_teams if str(t).strip()])
                    self.log_info(
                        f"Championship Excel: extracted {len(teams)} teams: {teams}"
                    )

                # Return with metadata if teams found (championship mode)
                if teams:
                    return self._success(
                        data=df,
                        message=f"Championship Excel loaded ({len(df)} entries from {len(teams)} teams)",
                        metadata={
                            "teams": teams,
                            "meet_name": diag.get("chosen_sheet", "Championship"),
                            "total_entries": len(df),
                        },
                    )
                else:
                    return self._success(
                        data=df,
                        message=f"Excel loaded successfully ({len(df)} entries from sheet '{diag.get('chosen_sheet')}')",
                    )

            else:
                return self._error(
                    f"Unsupported file type: {filepath}", code="INVALID_FILE_TYPE"
                )

        except FileNotFoundError:
            return self._error(f"File not found: {filepath}", code="FILE_NOT_FOUND")
        except pd.errors.EmptyDataError:
            return self._error(
                f"The file appears to be empty: {filepath}", code="EMPTY_FILE"
            )
        except pd.errors.ParserError:
            return self._error(
                f"Could not parse file. Please ensure it is a valid CSV/PDF: {filepath}",
                code="PARSER_ERROR",
            )
        except Exception as e:
            return self._error(f"Error loading file: {str(e)}", code="LOAD_ERROR")


# Singleton instance
data_service = DataService(upload_dir="uploads")
