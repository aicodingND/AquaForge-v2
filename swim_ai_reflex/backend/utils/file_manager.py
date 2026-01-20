import os
import pandas as pd
from werkzeug.utils import secure_filename
from swim_ai_reflex.backend.core.normalization import load_roster_file, load_first_two_sheets_as_standard

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf'}

class FileManager:
    def __init__(self, upload_dir):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def save_file(self, file_obj, prefix=''):
        if not getattr(file_obj, 'filename', None):
            raise ValueError('File object missing filename')
        if file_obj and self.allowed_file(file_obj.filename):
            import time
            import re
            
            # Get original filename
            original_filename = file_obj.filename
            print(f"[FileManager] Original filename: {original_filename}")
            
            # Sanitize filename - remove/replace problematic characters for Windows
            # Windows doesn't allow: < > : " / \ | ? *
            # Also remove any characters that might cause issues
            safe_name = secure_filename(original_filename)
            
            # Further sanitize - replace any remaining problematic chars
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', safe_name)
            
            # Add timestamp to avoid conflicts
            name_parts = safe_name.rsplit('.', 1)
            if len(name_parts) == 2:
                timestamp = str(int(time.time()))
                filename = f"{prefix}{name_parts[0]}_{timestamp}.{name_parts[1]}"
            else:
                filename = f"{prefix}{safe_name}_{int(time.time())}"
            
            print(f"[FileManager] Sanitized filename: {filename}")
            
            # Construct absolute path
            filepath = os.path.abspath(os.path.join(self.upload_dir, filename))
            print(f"[FileManager] Full filepath: {filepath}")
            
            # Verify upload directory exists
            if not os.path.exists(self.upload_dir):
                print(f"[FileManager] Creating upload directory: {self.upload_dir}")
                os.makedirs(self.upload_dir, exist_ok=True)
            
            try:
                print("[FileManager] Attempting to save file...")
                file_obj.save(filepath)
                print(f"[FileManager] File saved successfully: {filepath}")
                return filepath
            except Exception as e:
                print(f"[FileManager] ERROR saving file: {e}")
                print(f"[FileManager] Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                raise
        else:
            if not file_obj:
                print("[FileManager] No file object provided")
            elif not self.allowed_file(file_obj.filename):
                print(f"[FileManager] File type not allowed: {file_obj.filename}")
        return None

    def load_data(self, seton_path=None, opp_path=None, combined_path=None, filters=None):
        seton_std = None
        opp_std = None

        try:
            if combined_path:
                seton_std, opp_std = load_first_two_sheets_as_standard(combined_path, team_names=('seton', 'opponent'))
            else:
                if seton_path:
                    seton_std = load_roster_file(seton_path, 'seton')
                
                if opp_path:
                    opp_std = load_roster_file(opp_path, 'opponent')
                else:
                    # Create empty opponent if not provided, but only if seton exists
                    if seton_std is not None:
                        opp_std = pd.DataFrame(columns=seton_std.columns)
                    else:
                        opp_std = pd.DataFrame() # Fallback
            
            # Apply Filters
            if filters:
                print(f"[FileManager] Applying filters: {filters}")
                if seton_std is not None and not seton_std.empty:
                    seton_std = self.apply_filters(seton_std, filters)
                if opp_std is not None and not opp_std.empty:
                    opp_std = self.apply_filters(opp_std, filters)

            return seton_std, opp_std

        except Exception as e:
            raise ValueError(f"Failed to load data: {str(e)}")

    def apply_filters(self, df, filters):
        """
        Filters the dataframe based on:
        - genders: list of 'M', 'F'
        - category: string (substring match in event)
        - include_relays: bool
        - include_diving: bool
        - individual_events: list of event names (canonical)
        """
        if df is None or df.empty:
            return df
            
        print(f"[DEBUG] Rows before filter: {len(df)}")
        # 1. Gender Filter
        genders = filters.get('genders', [])
        if genders:
            # Normalize gender column just in case
            if 'gender' in df.columns and df['gender'].notna().any():
                df = df[df['gender'].isin(genders)]
            else:
                print("[DEBUG] Skipping gender filter due to missing/empty col")
        
        print(f"[DEBUG] Rows after gender: {len(df)}")

        # 2. Category Filter
        category = filters.get('category', '').strip()
        if category:
            # Case-insensitive substring match in event name
            df = df[df['event'].str.contains(category, case=False, na=False)]
            
        print(f"[DEBUG] Rows after category: {len(df)}")

        # 3. Event Type Filters
        include_relays = filters.get('include_relays', True)
        include_diving = filters.get('include_diving', True)
        individual_events = set(filters.get('individual_events', []))
        
        # We need to filter rows based on these rules
        # It's easier to iterate or use boolean masks
        
        keep_mask = pd.Series(False, index=df.index)
        
        # Relays
        if include_relays:
            keep_mask |= df['is_relay']
            
        # Diving
        if include_diving:
            keep_mask |= df['is_diving']
            
        # Individual Events
        # Rows that are NOT relay and NOT diving
        is_individual = (~df['is_relay']) & (~df['is_diving'])
        
        if individual_events:
            from swim_ai_reflex.backend.core.normalization import canonicalize_event_name
            
            # Helper to check if event matches any allowed individual event
            def matches_individual(row_event):
                canon = canonicalize_event_name(row_event)
                # print(f"[DEBUG] Filtering event: {row_event} -> {canon} in {individual_events}?")
                return canon in individual_events
            
            # Apply this check only to individual rows
            matched_individual = df['event'].apply(matches_individual)
            
            keep_mask |= (is_individual & matched_individual)
        else:
            # If no individual events selected, we don't keep any individual events
            pass
            
        print(f"[DEBUG] Mask sum: {keep_mask.sum()}")
        return df[keep_mask].reset_index(drop=True)

    def validate_rosters(self, seton_df, opp_df):
        # Basic validation
        if seton_df is None or seton_df.empty:
            raise ValueError("Seton roster is empty or failed to load.")
        
        required_cols = ['swimmer', 'event', 'time']
        for col in required_cols:
            if col not in seton_df.columns:
                 raise ValueError(f"Seton roster missing required column: {col}")
            if opp_df is not None and not opp_df.empty and col not in opp_df.columns:
                 raise ValueError(f"Opponent roster missing required column: {col}")
        
        return True

    def list_uploaded_files(self) -> list[str]:
        """Return a list of valid uploaded files (sorted by newest)."""
        files = []
        try:
            for f in os.listdir(self.upload_dir):
                if self.allowed_file(f):
                    files.append(f)
            # Sort by modification time (newest first)
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.upload_dir, x)), reverse=True)
        except Exception as e:
            print(f"[FileManager] Error listing files: {e}")
        return files