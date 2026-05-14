# OpenCode Instructions for student-110-system

## Architecture & Data Flow
- **Backend:** Flask with SQLite (`instance/student110.sqlite`).
- **Frontend:** Bootstrap 5, Tabulator for grid data.
- **Data Persistence:** `EventRecord` model stores the raw Excel row as a JSON string (`full_data`), alongside indexed columns (`event_no`, `school_name`, `department`). This preserves all original Excel columns dynamically without schema migrations.
- **Auth:** Two-tier role system. `admin` (global view, import, rule management) and `operator` (department-scoped view).

## Key Workflows
- **Excel Uploads (`/upload`):** Data is parsed with `dtype=str` to prevent scientific notation (e.g. ID numbers). Pandas replaces `\r` and `\n` globally and strips whitespace before storing.
- **School Auto-fill:** Runs during upload. It matches `SchoolRule` keywords against a concatenation of `处理结果` and `事件详情`.
- **Query View (`/query`):** Displays a subset of fields. Data editing opens a card view.
  - **Operator Restrictions:** Operators can only see records matching their `department`. When saving edits, operators can ONLY modify 10 specific target fields (defined by `allowed_prefixes` in `routes.py:update_record` and `query.html:openEditView`). Other fields are strictly read-only in UI and ignored in backend.
- **Export (`/export`):** Receives the filtered JSON records and the original column order (`originalColumns`) from the frontend to rebuild the exact original Excel schema.

## Development Quirks
- **Database Resets:** If modifying models, delete `instance/student110.sqlite` before restarting to recreate tables. An `admin` / `123456` user is auto-created on init.
- **Dependency Issues:** Pandas read/write requires `openpyxl >= 3.1.5` for recent versions.
- **Testing Scripts:** `generate_users.py` uses `pypinyin` to seed operator accounts from department names.

## File Locations
- **Routes:** `app/routes.py` (all API and view endpoints are here).
- **Models:** `app/models.py` (`User`, `SchoolRule`, `EventRecord`).
- **Templates:** `app/templates/` (look for Tabulator logic in `<script>` blocks of `index.html` and `query.html`).