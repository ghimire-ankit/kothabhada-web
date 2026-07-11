# Project Audit & Deep Scan Review: KothaBhada

This document outlines the detailed review and code inspection of the **KothaBhada Appication** project. We performed a comprehensive codebase analysis, resolved major functional bugs, addressed critical security concerns, and added missing interactive UX capabilities.

---

## 🔍 Executive Summary of Issues Detected & Addressed

| # | Bug / Issue Category | Description | Severity | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Supabase Client Authentication & RLS Bypass** | The Flask backend initializes the Supabase client using the public `anon` key from `.env`. Because Flask acts as the trusted backend proxy but does not pass user credentials/tokens to the database layer, all database requests execute with the guest/unauthenticated role. The database Row-Level Security (RLS) policies require `auth.uid() = id`/`provider_id = auth.uid()` for updates and selects, meaning backend inserts, updates, and user reads will either block or fail to return rows. | **CRITICAL** | **Identified (Mitigation Proposed)** |
| **2** | **Invalid Timestamp Insertion (`created_at`)** | In `app.py` `/register` and `/property` routes, `'created_at': 'now()'` was hardcoded in python dicts. Python's postgrest-py does not parse `'now()'` as a function and inserts it as a raw string, throwing an `invalid input syntax for type timestamp with time zone` database error. | **HIGH** | **RESOLVED** |
| **3** | **JSONB Double Serialization (`location` field)** | In `app.py` `/register`, user location was processed using `json.dumps(location_data)`. Postgrest-py automatically serializes dictionaries. Double-encoding it turned the database field value into a string literal inside the `JSONB` column, making key lookups (e.g. `location->>'city'`) return `NULL`. | **HIGH** | **RESOLVED** |
| **4** | **Geolocation Denied Permission Lockout** | In `static/js/auth.js`, if a user denied browser geolocation permission, the app showed a static error message and blocked them, failing to fallback to the manual street & city entry form. | **MEDIUM** | **RESOLVED** |
| **5** | **Non-Functional Search and Filters** | The dashboards contained HTML elements for search inputs (e.g. status, type, price), but they were entirely static: no JavaScript events were tied to them to search or filter properties. | **MEDIUM** | **RESOLVED** |
| **6** | **Leaflet Map Marker Crashes** | Leaflet marker code in both dashboards would fail with JavaScript exceptions and block map rendering if any property element returned `NaN` coordinates during `parseFloat(card.dataset.lat)`. | **MEDIUM** | **RESOLVED** |
| **7** | **PostgreSQL Schema Out-of-sync** | `database_schema.sql` (defining `latitude`/`longitude`, `updated_at`, and nullable fields) mismatch with `supabase_setup.sql`. | **LOW** | **Identified** |
| **8** | **Missing `updated_at` Trigger** | Schemas define `updated_at` but lack database triggers to auto-update the timestamp on modifications. | **LOW** | **Solution Provided** |

---

## 🛠️ Detailed Bug Walkthrough & Mitigation Plans

### 1. The Supabase & RLS Security Mismatch (High Security Priority)
- **Problem**: The Flask server utilizes:
  ```python
  SUPABASE_URL = os.getenv("SUPABASE_URL")
  SUPABASE_KEY = os.getenv("SUPABASE_KEY") # set to 'anon' key in .env
  ```
  Since the server makes database updates and reads directly using this `anon` key, the database treats requests as unauthenticated guest users.
  However, `supabase_setup.sql` secures tables using:
  ```sql
  CREATE POLICY "Users can view their own data" ON users FOR SELECT USING (auth.uid() = id);
  CREATE POLICY "Providers can insert their own properties" ON properties FOR INSERT WITH CHECK (provider_id = auth.uid());
  ```
  Since `auth.uid()` is `NULL` for the server, these policies block the server from selecting, updating, or deleting user-associated properties.
- **Recommended Solutions**:
  1. **Option A (Secure & Standard)**: Obtain the server's secret `service_role` key from your Supabase dashboard (**Project Settings -> API**). Update `.env`'s `SUPABASE_KEY` with this key. This bypasses RLS policies exclusively for server operations, ensuring the Flask backend can access and edit records.
  2. **Option B (Fast Bypass)**: If your Flask application is the sole gatekeeper of the database, you can disable RLS since authentication is already verified inside the endpoints:
     ```sql
     ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;
     ALTER TABLE public.properties DISABLE ROW LEVEL SECURITY;
     ```

---

### 2. Resolved: Timestamp & JSONB Serialization Bugs (`app.py`)
Both the timestamp crash and the JSONB string conversion bugs have been patched:
- **Before (Buggy `created_at` and `location` string)**:
  ```python
  user_data = {
      'location': json.dumps(location_data),
      'created_at': 'now()'
  }
  ```
- **After (Automated DB generation & Native dict)**:
  ```python
  user_data = {
      'location': location_data,  # Passes dict directly for proper JSONB serialization
  }
  # created_at is omitted to allow PostgreSQL's default column value (now()) to run
  ```

---

### 3. Resolved: Geolocation Fallback Flow (`auth.js`)
We modified `static/js/auth.js` so that if a user denies location access OR if GPS fails, the application automatically transitions the user to the manual address entry form to finish registration, printing a helpful status:
```javascript
if (error.code === error.PERMISSION_DENIED) {
    showSuccess('Fallback: Please enter your address manually.');
} else {
    showSuccess('Could not get GPS location. Please enter your address manually.');
}
document.getElementById('registration-form').style.display = 'none';
document.getElementById('location-form').style.display = 'block';
```

---

### 4. Resolved: Dynamic Dashboards, Map Sync, & Interactive Search
We replaced the placeholder input/filter buttons with active JavaScript handlers in:
- `templates/provider_dashboard.html`
- `templates/user_dashboard.html`

**Interactive Additions:**
1. **Interactive search inputs**: Dynamic title/location substring search updates visible cards in real time.
2. **Dynamic filters**: Dropdowns for price tiers (User: All, Under \$500, \$500-\$1000, Over \$1000) and statuses (Provider: All, Available, Rented) filter properties instantly.
3. **Map-Marker Sync**: Hiding a card automatically removes its marker from the Leaflet map; showing it places it back. The map auto-rescales (`fitBounds`) to only show active visible markers.
4. **NaN Coordinate Protection**: Leaflet will skip map generation for properties missing valid coordinate sets, preventing visual code halting.

---

### 5. Schema Out-Of-Sync and Database Trigger
To keep `updated_at` timestamps accurate, append this trigger code to your database setup:
```sql
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_modtime BEFORE UPDATE ON users FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
CREATE TRIGGER update_properties_modtime BEFORE UPDATE ON properties FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
```

Use `database_schema.sql` as the single source of truth since it contains the necessary latitude/longitude and updated_at column definitions needed by the dashboards.
