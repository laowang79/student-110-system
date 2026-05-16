# OpenCode Instructions for student-110-system

## Architecture & Data Flow
- **Backend:** Flask with SQLite (`instance/student110.sqlite`).
- **Frontend:** Bootstrap 5, Tabulator, FontAwesome, SweetAlert2. All static assets are local (`app/static/`) for pure offline capability. No CDNs.
- **Data Persistence:** `EventRecord` model stores the raw Excel row as a JSON string (`full_data`), alongside indexed columns (`event_no`, `school_name`, `department`). This preserves all original Excel columns dynamically without schema migrations.
- **Auth:** Two-tier role system. `admin` (global view, import, rule management) and `operator` (department-scoped view).

## Key Workflows
- **Excel Uploads (`/upload`):** Data is parsed with `dtype=str` to prevent scientific notation. The original `序号` (Sequence Number) column is dropped. 
- **Query View (`/query`):** Displays data sorted descending by `接警时间` (Report Time) with a newly generated, dynamic `序号` starting at 1.
  - **Operator Restrictions:** Operators can only modify 10 specific target fields (defined by `allowed_prefixes`). Other fields are strictly read-only and ignored in backend.
  - **Modified Flagging:** When a record is edited, `_is_modified=True` is injected into `full_data`. Unmodified rows are rendered with a yellow background (`#fff3cd`) in Tabulator.
- **Export (`/export`):** Rebuilds the exact original Excel schema by respecting the column order from the first parsed row. Strips the internal `_is_modified` flag before generating the `.xlsx`.

## Offline Deployment & Network
- **Pure Offline Mode:** The system runs in a strict intranet environment. Dependencies are pre-downloaded in `offline_packages/`.
- **Install command:** `pip install --no-index --find-links=offline_packages -r requirements.txt` (Run inside a `venv`).
- **LAN Access:** `run.py` binds to `host='0.0.0.0'` to allow access across the local network via `http://<server-ip>:5000`.

## Development Quirks & Constraints
- **Spreadsheets:** NEVER commit `.xlsx`, `.xls`, or `.csv` files to the repository. They contain sensitive data and are ignored in `.gitignore`.
- **Database Resets:** If modifying models, delete `instance/student110.sqlite` before restarting to recreate tables. An `admin` / `123456` user is auto-created on init.
- **Dependency Issues:** Pandas read/write requires `openpyxl >= 3.1.5` for recent versions.
- **Testing Scripts:** `generate_users.py` uses `pypinyin` to seed operator accounts from department names.

## File Locations
- **Routes:** `app/routes.py` (all API and view endpoints).
- **Models:** `app/models.py` (`User`, `SchoolRule`, `EventRecord`).
- **Templates:** `app/templates/` (Tabulator logic and Glassmorphism/gradient styling resides here).
