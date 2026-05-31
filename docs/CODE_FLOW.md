# CO-PO Attainment Portal — Legacy code flow (Flask)

> **Note:** This document describes the **archived Flask portal** (`legacy/flask-portal/`). The production stack is FastAPI + React — see [ARCHITECTURE.md](ARCHITECTURE.md) and [WORKFLOW_A.md](WORKFLOW_A.md).

This document explains the architecture, data flow, and key components of the original CO-PO Attainment Portal application.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Key Modules](#key-modules)
6. [Route Flow](#route-flow)
7. [Data Processing Pipeline](#data-processing-pipeline)
8. [File Management](#file-management)
9. [Database Schema](#database-schema-in-memory)
10. [Error Handling](#error-handling)

---

## Architecture Overview

### Application Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (HTML/CSS/JS)                   │
│            (Templates: index.html, eval.html, etc.)         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Requests
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Flask Web Application (app.py)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Routes & Request Handlers                            │   │
│  │ - / (index)          - /eval (single evaluation)     │   │
│  │ - /eval/bulk         - /results/<id>                 │   │
│  │ - /api/* (REST API)  - /download_results/<id>        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ Uses
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Data Processing Module (ece_orignal_updated.py)     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ main_process()       - Core calculation engine       │   │
│  │ read_excel()         - Parse input files             │   │
│  │ normalize_data()     - Data transformation           │   │
│  │ calculate_metrics()  - Compute CO/PO attainment     │   │
│  │ generate_excel()     - Create output files           │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ Works with
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   External Files                            │
│  ├── Excel Files (.xlsx)                                    │
│  │   ├── Mapping: CO-PO relationship matrices              │
│  │   ├── Input: Student marks and CO assessments           │
│  │   └── Output: Generated results and reports             │
│  └── Temporary Files (/uploads folder)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
POA/
├── app.py                                      # Main Flask application
├── ece_orignal_updated.py                      # Core data processing engine
├── requirements.txt                            # Python dependencies
├── pm2.config.js                               # PM2 configuration (if using PM2)
│
├── static/                                     # Static files (CSS, JS, Images)
│   ├── style.css                               # Application styling
│   └── script.js                               # Frontend JavaScript
│
├── templates/                                  # HTML templates
│   ├── index.html                              # Home page & single evaluation
│   ├── eval.html                               # Evaluation form
│   ├── eval_bulk.html                          # Bulk evaluation form
│   ├── eval_results.html                       # Single evaluation results
│   ├── eval_bulk_results.html                  # Bulk evaluation results
│   └── results.html                            # Generic results page
│
├── uploads/                                    # Temporary uploaded files
│   ├── [temporary Excel files]
│   └── [auto-cleaned after 30 minutes]
│
├── logs/                                       # Application logs (created at runtime)
│   ├── error.log
│   ├── access.log
│   └── combined.log
│
├── Course, CO and PO mapping Nov 2025 (2).xlsx # Required: CO-PO mapping reference
├── indirect.xlsx                               # Required: Indirect assessment data
├── *.xlsx                                      # Sample course data files
│
└── .git/                                       # Version control (if using Git)
```

---

## Core Components

### 1. Flask Application (app.py)

**Purpose**: Web server and request router

**Key Responsibilities**:
- Handle HTTP requests from frontend
- Manage file uploads and downloads
- Coordinate data processing
- Cache and manage results
- Clean up temporary files

**Main Variables**:
```python
RESULT_CONTEXTS = {}          # Store evaluation results (max 30 min)
DOWNLOAD_CONTEXTS = {}        # Store downloadable files (max 30 min)
UPLOAD_FOLDER = './uploads'   # Directory for temporary uploads
DEFAULT_MAPPING_PATH          # Path to CO-PO mapping file
DEFAULT_INDIRECT_PATH         # Path to indirect assessment file
```

### 2. Data Processing Engine (ece_orignal_updated.py)

**Purpose**: Core calculation logic for CO/PO attainment

**Key Functions**:
- `main_process()` - Main entry point for evaluation
- `extract_course_co_po_mapping()` - Extract CO-PO relationship matrix
- `read_course_data()` - Parse student marks and COs
- `calculate_co_statistics()` - Compute CO attainment percentages
- `compute_po_pso_weighted_avg()` - Calculate program-level outcomes
- `generate_output_excel()` - Create result files

**Data Output**:
```python
{
    'unique_COs': ['CO1', 'CO2', 'CO3'],
    'CO_stats': {
        'pct_above': {'CO1': 85.5, 'CO2': 78.2, ...},
        'mean': {'CO1': 72.3, ...},
        'std': {'CO1': 12.5, ...}
    },
    'po_pso_attainment': {
        'PO1': 82.3, 'PO2': 79.1, ...,
        'PSO1': 88.5, 'PSO2': 85.2, 'PSO3': 86.0
    },
    'CO_PO_mapping': {...},
    'excel_path': '/path/to/results.xlsx'
}
```

### 3. Frontend (HTML Templates)

**index.html**
- Course selection dropdown
- File upload interface
- Quick evaluation launch

**eval.html**
- Single course evaluation form
- Student filtering options
- Mapping file selection
- Program and branch filters

**eval_bulk.html**
- Multiple course rows
- Batch file upload
- Bulk evaluation submission

**eval_results.html**
- CO attainment table
- PO/PSO weighted averages
- Comparison with expected values
- Download button

---

## Data Flow

### End-to-End User Flow

```
User Action                          System Response
───────────────────────────────────────────────────────────

1. Upload course file      ──────►  Save to /uploads
                                    Parse student data
                                    Extract COs and programs

2. Select CO-PO mapping    ──────►  Load mapping relationships
                                    Extract available courses

3. Select course & params  ──────►  Build evaluation parameters
                                    Prepare for calculation

4. Click "Evaluate"        ──────►  Call ece_orignal_updated.main_process()
                                    Calculate CO statistics
                                    Compute PO/PSO weighted averages
                                    Generate Excel output
                                    Store in RESULT_CONTEXTS

5. View results            ──────►  Retrieve from RESULT_CONTEXTS
                                    Display tables & metrics
                                    Show comparison if provided

6. Download Excel          ──────►  Stream file to user
                                    Auto-delete after download
                                    Clean up temporary files
```

### Data Processing Pipeline

```
Input Files
├── course.xlsx (student marks)
├── mapping.xlsx (CO-PO matrix)
└── indirect.xlsx (survey data)
          │
          ▼
┌─────────────────────────────────────┐
│   1. Data Parsing & Validation      │
│   ────────────────────────────────  │
│   - Read Excel sheets               │
│   - Normalize headers               │
│   - Extract metadata (CO, Roll No)  │
│   - Validate data types             │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│   2. CO Extraction & Mapping        │
│   ────────────────────────────────  │
│   - Identify COs from input         │
│   - Load CO-PO weight matrix        │
│   - Link student marks to COs       │
│   - Apply filters (program/branch)  │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│   3. Statistical Calculation        │
│   ────────────────────────────────  │
│   - Calculate mean marks per CO     │
│   - Calculate std dev per CO        │
│   - Apply threshold: max(50, μ-σ/2)│
│   - Count students above threshold  │
│   - Calculate % above threshold     │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│   4. PO/PSO Weighting              │
│   ────────────────────────────────  │
│   - Weighted sum using CO matrix    │
│   - PO[i] = Σ(CO_attainment * w[i])│
│   - Include PSO calculations        │
│   - 90% Direct + 10% Indirect       │
│   - Final PO/PSO % values           │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│   5. Excel Generation               │
│   ────────────────────────────────  │
│   - Create structured output        │
│   - Add CO statistics table         │
│   - Add PO/PSO averages             │
│   - Add comparison data (if provided)│
│   - Format cells & headers          │
│   - Save with timestamp             │
└─────────────────────────────────────┘
          │
          ▼
Output Excel File
├── CO Statistics (mean, std, % above threshold)
├── PO/PSO Attainment (weighted averages)
├── Direct Assessment Results
├── Indirect Assessment (if provided)
└── Final Assessment (90% + 10%)
```

---

## Key Modules

### Module 1: Flask Routes (app.py)

#### Route: `GET /`
**Purpose**: Home page and single evaluation form

```python
@app.route('/', methods=['GET', 'POST'])
def index():
    # GET: Display form with course options
    # POST: Validate and process single evaluation
```

**Flow**:
1. GET request → Display template with course dropdown
2. Form data collected from frontend
3. File validation
4. Call `prepare_results_payload()`
5. Store in `RESULT_CONTEXTS`
6. Redirect to results page

#### Route: `POST /eval`
**Purpose**: Detailed single course evaluation with options

```python
@app.route('/eval', methods=['GET', 'POST'])
def evaluate():
    # Process evaluation with program/branch filters
    # Compare with expected output file
```

**Parameters**:
```
course_file         - Student marks Excel
mapping_file        - CO-PO mapping (optional, uses default)
course_title        - Selected course name
programme_filters   - UG/PG/PhD filter
branch_filters      - ECE/CSE/etc filter
comparison_file     - Expected results for validation
co_cell_ref         - Cell reference for CO comparison
po_cell_ref         - Cell reference for PO comparison
```

#### Route: `POST /eval/bulk`
**Purpose**: Process multiple courses in bulk

```python
@app.route('/eval/bulk', methods=['GET', 'POST'])
def evaluate_bulk():
    # Process multiple course rows
    # Collect results for each row
    # Display summary results
```

**Bulk Parameters** (per row):
```
course_file_{n}     - Student file
course_title_{n}    - Course name
compare_file_{n}    - Comparison file
co_cell_{n}         - CO cell reference
po_cell_{n}         - PO cell reference
programmes_{n}      - Program filters (array)
branches_{n}        - Branch filters (array)
```

#### Route: `GET /results/<result_id>`
**Purpose**: Display stored evaluation results

```python
@app.route('/results/<result_id>', methods=['GET'])
def view_results(result_id):
    # Retrieve from RESULT_CONTEXTS
    # Render results template
    # Show CO and PO tables
```

#### Route: `GET /download_results/<download_id>`
**Purpose**: Stream Excel file to user

```python
@app.route('/download_results/<download_id>')
def download_results(download_id):
    # Retrieve file path from DOWNLOAD_CONTEXTS
    # Stream to user as attachment
    # Delete after download
```

### Module 2: API Routes (app.py)

#### API: `GET/POST /api/course_names`
**Purpose**: Get available courses from mapping file

```python
@app.route('/api/course_names', methods=['GET', 'POST'])
def api_course_names():
    # GET: Read from default mapping
    # POST: Read from uploaded mapping
    # Return: ['ECE-315', 'ECE-401', ...]
```

#### API: `POST /api/parse_students`
**Purpose**: Parse student file to extract programs and branches

```python
@app.route('/api/parse_students', methods=['POST'])
def api_parse_students():
    # Extract unique programs: UG, PG, PhD
    # Extract branches: ECE, CSE
    # Extract COs: CO1, CO2, CO3
    # Return: {programs: {...}, branches: {...}, cos: [...]}
```

#### API: `POST /api/course_cos`
**Purpose**: Get COs for a specific course and indirect values

```python
@app.route('/api/course_cos', methods=['POST'])
def api_course_cos():
    # Extract COs from CO-PO mapping
    # Lookup indirect attainment values
    # Return: {cos: ['CO1', 'CO2', ...], indirect: {...}}
```

#### API: `POST /api/clear_uploads`
**Purpose**: Clean uploaded files and result cache

```python
@app.route('/api/clear_uploads', methods=['POST'])
def api_clear_uploads():
    # Delete /uploads folder contents
    # Clear RESULT_CONTEXTS
    # Clear DOWNLOAD_CONTEXTS
    # Return: {removed: n, cleared_contexts: n}
```

### Module 3: Data Processing (ece_orignal_updated.py)

#### Function: `extract_course_co_po_mapping(mapping_path, course_pattern)`

**Purpose**: Extract CO-PO weight matrix from Excel

```python
def extract_course_co_po_mapping(mapping_path: str, course_pattern: str):
    # Input: Path to mapping file, course name pattern (e.g., "ECE-315")
    # Process:
    #   1. Read "Course outcome mapping UG" sheet
    #   2. Find course row matching pattern
    #   3. Extract CO rows below course
    #   4. Extract PO columns (1-12) and PSO columns (1-3)
    #   5. Build weight matrix
    # Output: pandas DataFrame
    #   Index: CO1, CO2, CO3, ...
    #   Columns: PO1-PO12, PSO1-PSO3
    #   Values: Weight (0.0 - 1.0)
```

**Example Output**:
```
        PO1   PO2   PO3   ...  PSO1  PSO2  PSO3
CO1    0.8   0.6   0.3   ...  0.5   0.4   0.3
CO2    0.9   0.5   0.2   ...  0.6   0.5   0.4
CO3    0.7   0.8   0.4   ...  0.7   0.6   0.5
```

#### Function: `main_process(course_path, mapping_path, course_title, included_rolls=None, target_value=50)`

**Purpose**: Main calculation engine

```python
def main_process(
    course_path: str,           # Path to student marks file
    mapping_path: str,          # Path to CO-PO mapping
    course_title: str,          # Course name (e.g., "ECE-315")
    included_rolls=None,        # List of roll numbers to include
    target_value=50             # Threshold for attainment (default 50)
):
    # Process Flow:
    # 1. Read course data (student marks, COs)
    # 2. Read CO-PO mapping matrix
    # 3. Filter students (if included_rolls provided)
    # 4. Calculate statistics per CO:
    #    - Mean marks
    #    - Std deviation
    #    - Threshold = max(target_value, mean - 0.5*std)
    #    - % above threshold
    # 5. Compute PO/PSO weighted averages
    # 6. Generate output Excel file
    # 7. Return results dictionary
```

**Return Value**:
```python
{
    'unique_COs': ['CO1', 'CO2', 'CO3'],
    'total_students': 45,
    'included_students': 42,  # After filtering
    'CO_stats': {
        'count': {'CO1': 42, 'CO2': 40, ...},
        'mean': {'CO1': 72.3, 'CO2': 68.5, ...},
        'std': {'CO1': 12.5, 'CO2': 14.2, ...},
        'threshold': {'CO1': 56.0, 'CO2': 54.3, ...},
        'above_threshold': {'CO1': 35, 'CO2': 28, ...},
        'pct_above': {'CO1': 83.3, 'CO2': 70.0, ...}
    },
    'CO_PO_mapping': {
        'CO1': {'PO1': 0.8, 'PO2': 0.6, ...},
        'CO2': {'PO1': 0.9, 'PO2': 0.5, ...},
        ...
    },
    'po_pso_attainment': {
        'PO1': 82.3, 'PO2': 79.1, ...,
        'PSO1': 88.5, 'PSO2': 85.2, 'PSO3': 86.0
    },
    'excel_path': '/uploads/results_xyz123.xlsx'
}
```

#### Function: `compute_po_pso_weighted_avg(co_attainment, co_po_mapping)`

**Purpose**: Calculate PO/PSO from CO attainment using weights

```python
def compute_po_pso_weighted_avg(co_attainment, co_po_mapping):
    # Input:
    #   co_attainment: {'CO1': 83.3, 'CO2': 70.0, ...}
    #   co_po_mapping: DataFrame with CO rows and PO/PSO columns
    # Formula:
    #   PO[i] = Σ(CO_attainment[j] * weight[j, i]) / Σ(weight[j, i])
    # Output: {'PO1': 82.3, 'PO2': 79.1, ..., 'PSO1': 88.5, ...}
```

**Mathematical Formula**:
$$PO_i = \frac{\sum_{j=1}^{n} (CO_{att,j} \times w_{j,i})}{\sum_{j=1}^{n} w_{j,i}}$$

Where:
- $CO_{att,j}$ = Attainment percentage for CO j
- $w_{j,i}$ = Weight of CO j for PO i
- $n$ = Total number of COs

### Module 4: Utility Functions (app.py)

#### Function: `parse_student_rolls(file_path)`

**Purpose**: Extract program/branch info and COs from student file

```python
def parse_student_rolls(file_path: str):
    # Output:
    {
        'cos': ['CO1', 'CO2', 'CO3'],
        'programmes': {'UG': 35, 'PG': 7},
        'branches': {
            'UG::ECE': {'count': 25, 'programme': 'UG', 'branch': 'ECE'},
            'UG::CSE': {'count': 10, 'programme': 'UG', 'branch': 'CSE'},
            'PG::ECE': {'count': 7, 'programme': 'PG', 'branch': 'ECE'}
        },
        'total_students': 42,
        'rolls_by_programme': {'UG': ['2201001', ...], 'PG': ['MT001', ...]},
        'rolls_by_branch': {
            'UG::ECE': ['2201001', '2201002', ...],
            'UG::CSE': ['2202001', ...],
            'PG::ECE': ['MT001', ...]
        }
    }
```

#### Function: `build_evaluation_payload(...)`

**Purpose**: Compare calculated vs expected results

```python
def build_evaluation_payload(
    course_path, mapping_path, course_title,
    compare_path, included_rolls=None,
    co_cell_ref=None, po_cell_ref=None,
    target_value=50
):
    # Output:
    {
        'intermediate': {...},  # Result from main_process()
        'co_table': {
            'title': '% > max(50, Mean - 0.5*Std)',
            'columns': ['CO1', 'CO2', ...],
            'rows': [
                {'label': 'Calculated', 'values': [83.3, 70.0, ...]},
                {'label': 'Read From Output', 'values': [82.5, 70.5, ...]},
                {'label': 'Delta', 'values': [0.8, -0.5, ...]}
            ]
        },
        'po_table': {...}  # Similar structure for PO/PSO
    }
```

#### Function: `store_result_context(payload)` / `get_result_context(result_id)`

**Purpose**: Temporary storage for evaluation results

```python
# Store
result_id = store_result_context({
    'course_title': 'ECE-315',
    'excel_path': '/uploads/results_xyz.xlsx',
    'intermediate': {...}
})
# Returns: UUID hex string (e.g., 'a1b2c3d4e5f6...')

# Retrieve
payload = get_result_context(result_id)
# Returns: Original payload or None if expired
```

**Auto-Cleanup**: Results expire after 30 minutes (FILE_MAX_AGE_SECONDS = 1800)

---

## Route Flow

### Route: POST /eval (Single Evaluation Flow)

```
User Submits Form
       │
       ▼
┌─────────────────────────────────────┐
│ 1. Validate Input Files             │
│    - Check course file exists       │
│    - Check mapping file             │
│    - Validate Excel format          │
└─────────────────────────────────────┘
       │ OK │
       ▼
┌─────────────────────────────────────┐
│ 2. Build Include Rolls List         │
│    - Parse student file             │
│    - Filter by program/branch       │
│    - Create included_rolls array    │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 3. Call main_process()              │
│    (ece_orignal_updated module)     │
│    - Normalize data                 │
│    - Calculate CO statistics        │
│    - Compute PO/PSO averages        │
│    - Generate Excel output          │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 4. Handle Comparison (if provided)  │
│    - Read expected CO/PO values     │
│    - Calculate deltas               │
│    - Build comparison tables        │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 5. Handle Indirect Attainment       │
│    - Lookup indirect.xlsx values    │
│    - Compute indirect PO/PSO        │
│    - Calculate final (90% + 10%)    │
│    - Update Excel with results      │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 6. Store Results                    │
│    - store_result_context()         │
│    - Create result_id               │
│    - Set 30-min expiry              │
└─────────────────────────────────────┘
       │
       ▼
Result Page with Tables & Download Link
```

### Route: POST /eval/bulk (Bulk Evaluation Flow)

```
User Submits Multiple Rows
       │
       ▼
┌─────────────────────────────────────┐
│ For Each Row (process_bulk_eval_row)│
│                                     │
│ 1. Validate files & parameters      │
│ 2. Build included rolls             │
│ 3. Call main_process()              │
│ 4. Collect result (success/error)   │
│ 5. Clean temporary files            │
│                                     │
│ Repeat for all rows                 │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Store Bulk Results                  │
│ - result_id for entire batch        │
│ - Array of row results              │
│ - Status: success/error per row     │
└─────────────────────────────────────┘
       │
       ▼
Bulk Results Page with Summary Table
```

---

## Data Processing Pipeline

### CO Attainment Calculation

**Threshold Formula**:
$$T = \max(50, \mu - 0.5 \times \sigma)$$

Where:
- $T$ = Threshold marks
- $\mu$ = Mean marks for CO
- $\sigma$ = Standard deviation

**Attainment Percentage**:
$$\text{Attainment} = \frac{\text{Number of students above threshold}}{\text{Total students}} \times 100$$

### PO/PSO Weighting

**Direct Assessment (from CO)**:
$$PO_i = \frac{\sum_{j=1}^{n} (CO_{att,j} \times w_{j,i})}{\sum_{j=1}^{n} w_{j,i}}$$

**Indirect Assessment (from survey/employer)**:
$$\text{Indirect}_i = \text{Average of indirect CO values weighted by } w_{j,i}$$

**Final Assessment**:
$$\text{Final}_i = (0.90 \times \text{Direct}_i) + (0.10 \times \text{Indirect}_i)$$

### Example Calculation

**Given**:
- CO1 attainment: 85%
- CO2 attainment: 72%
- CO3 attainment: 68%
- PO1 weights: CO1=0.8, CO2=0.5, CO3=0.3

**Calculation**:
$$PO1 = \frac{(85 \times 0.8) + (72 \times 0.5) + (68 \times 0.3)}{0.8 + 0.5 + 0.3}$$
$$PO1 = \frac{68 + 36 + 20.4}{1.6} = \frac{124.4}{1.6} = 77.75\%$$

---

## File Management

### Upload Workflow

```
User selects file
       │
       ▼
save_uploaded_file(uploaded_file, prefix)
       │
       ├─ Generate unique filename
       │  Format: {prefix}_{uuid}_{original_name}
       │
       └─ Save to /uploads
          Return: /uploads/eval_input_a1b2c3d_file.xlsx
```

### Cleanup Workflow

```
┌──────────────────────────────────────┐
│ _cleanup_old_files() (Background)    │
│ ────────────────────────────────────  │
│ Runs every 5 minutes                 │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Check Result Contexts                │
│ - Remove expired results (> 30 min)  │
│ - Delete associated Excel files      │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Check Download Contexts              │
│ - Remove expired downloads (> 30 min)│
│ - Delete associated files            │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ Check /uploads Folder                │
│ - Find files older than 30 minutes   │
│ - Delete old temporary files         │
│ - Log cleanup actions                │
└──────────────────────────────────────┘
```

### File Lifecycle

```
User uploads file
       │
       ▼
Saved in /uploads with UUID name
       │
       ├──► Used in processing
       │
       ▼
Result stored in memory with file reference
       │
       ├──► User downloads
       │    ├─ Stream file
       │    └─ Delete after download
       │
       └──► 30 minutes pass
            └─ Auto-deleted by cleanup thread
```

---

## Database Schema (In-Memory)

### RESULT_CONTEXTS Dictionary

```python
{
    'result_id_hex_string': {
        'created_at': 1700000000.0,  # Unix timestamp
        'payload': {
            'course_title': 'ECE-315',
            'course_filename': 'student_data.xlsx',
            'mapping_filename': 'CO-PO mapping.xlsx',
            'intermediate': {
                'unique_COs': ['CO1', 'CO2', 'CO3'],
                'total_students': 42,
                'CO_stats': {...},
                'po_pso_attainment': {...},
                'excel_path': '/uploads/results_xyz.xlsx'
            },
            'unique_COs': ['CO1', 'CO2', 'CO3'],
            'excel_path': '/uploads/results_xyz.xlsx'
        }
    },
    ...
}
```

### DOWNLOAD_CONTEXTS Dictionary

```python
{
    'download_id_hex_string': {
        'created_at': 1700000000.0,  # Unix timestamp
        'excel_path': '/uploads/results_xyz.xlsx'
    },
    ...
}
```

---

## Error Handling

### Error Categories

#### 1. File Errors

```python
# Missing file
if not os.path.exists(file_path):
    raise ValueError(f"File not found: {file_path}")

# Invalid format
if not allowed_file(filename):
    raise ValueError("Only .xlsx files are allowed")

# Corrupted Excel
try:
    df = pd.read_excel(file_path)
except Exception as e:
    raise ValueError(f"Cannot read Excel file: {e}")
```

#### 2. Data Validation Errors

```python
# Missing required columns
required_cols = ['Roll No.', 'CO', 'Max_Marks']
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

# Invalid CO format
if not re.match(r'^CO\d+$', co):
    raise ValueError(f"Invalid CO format: {co}")

# Mismatched roll numbers
if len(included_rolls) == 0:
    raise ValueError("No students match the selected criteria")
```

#### 3. Calculation Errors

```python
# Division by zero
if count == 0:
    result = None  # Handle gracefully
else:
    result = sum_value / count

# Invalid numeric data
try:
    value = float(cell_value)
except ValueError:
    raise ValueError(f"Invalid numeric value: {cell_value}")
```

#### 4. API Errors

```python
# Invalid request parameters
if not course_title:
    return jsonify({'error': 'Course title required'}), 400

# File upload error
if not file or not allowed_file(file.filename):
    return jsonify({'error': 'Invalid file'}), 400

# Processing error
try:
    result = process_data()
except Exception as e:
    return jsonify({'error': str(e)}), 500
```

### Error Response Format

```python
{
    'error': 'Descriptive error message',
    'status': 'error',
    'details': {
        'stage': 'calculation',  # Where error occurred
        'failed_file': 'course_file.xlsx',  # Which file caused it
        'timestamp': '2025-11-20 14:30:45'
    }
}
```

---

## Logging and Debugging

### Log Output Locations

```
gunicorn.log       - Web server logs
nohup.out          - Background process output
logs/error.log     - Application errors
logs/access.log    - HTTP access logs
logs/combined.log  - All logs
```

### Debug Messages Format

```
[timestamp] [module] [level] Message
Examples:
[2025-11-20 14:30:45] [cleanup] [INFO] Removed stale file: /uploads/tmp_123.xlsx
[2025-11-20 14:31:12] [main_process] [ERROR] Cannot read mapping file: FileNotFoundError
[2025-11-20 14:32:00] [api] [DEBUG] Parsed 42 students from file
```

### Common Debug Scenarios

**Debugging CO Calculation**:
```python
# Add to ece_orignal_updated.py
print(f"[debug] CO1 mean: {co_mean}, std: {co_std}, threshold: {threshold}")
print(f"[debug] Students above threshold: {above_count} / {total}")
print(f"[debug] Attainment %: {attainment_pct}")
```

**Debugging PO Weighting**:
```python
# In compute_po_pso_weighted_avg()
print(f"[debug] Calculating PO{i}")
print(f"[debug] CO weights: {weights}")
print(f"[debug] CO attainments: {co_values}")
print(f"[debug] Weighted sum: {weighted_sum}, divisor: {divisor}")
print(f"[debug] Final PO{i}: {result}")
```

---

## Performance Considerations

### Optimization Points

1. **Excel Reading**: Use `openpyxl` for large files (faster than pandas)
2. **Filtering**: Apply program/branch filters early to reduce data
3. **Caching**: Store mapping matrices to avoid re-reading
4. **Cleanup**: Auto-delete old files to manage disk usage
5. **Batch Processing**: Process multiple courses simultaneously

### Performance Metrics

```python
# Expected processing time by file size
File Size    Processing Time    Student Count
─────────────────────────────────────────────
< 1 MB       < 1 second         < 100 students
1-5 MB       1-5 seconds        100-500 students
5-10 MB      5-15 seconds       500-1000 students
> 10 MB      15-30 seconds      > 1000 students
```

---

## Integration Points

### External Dependencies

1. **Flask**: Web framework for routing and request handling
2. **Pandas**: Data manipulation and Excel reading
3. **OpenPyXL**: Advanced Excel operations
4. **NumPy**: Numerical calculations
5. **Gunicorn**: WSGI application server
6. **Nginx**: Reverse proxy and load balancer

### Extension Points

```python
# Add custom metrics calculation
def calculate_custom_metric(data):
    # Your custom logic here
    return result

# Add database persistence
from sqlalchemy import create_engine
db = create_engine('postgresql://user:password@localhost/poa')

# Add authentication
from flask_login import LoginManager
login_manager = LoginManager()
```

---

## Security Considerations

### Input Validation

```python
# Validate uploaded files
allowed_extensions = {'xlsx'}
if not '.' in filename or \
   filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
    raise ValueError("Invalid file type")

# Sanitize filenames
from werkzeug.utils import secure_filename
safe_filename = secure_filename(user_provided_filename)

# Validate cell references
import re
if not re.match(r'^[A-Z]+\d+$', cell_ref):
    raise ValueError("Invalid cell reference format")
```

### File Security

```python
# Use unique filenames to prevent overwrites
unique_name = f"{prefix}_{uuid.uuid4().hex}_{filename}"

# Auto-delete temporary files
remove_file_if_exists(path)

# Limit file size
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
```

---

## Summary

The CO-PO Attainment Portal is a comprehensive Flask-based application that:

1. **Accepts** student mark data and CO-PO mapping files
2. **Validates** input data for format and completeness
3. **Calculates** CO attainment using statistical thresholds
4. **Weights** PO/PSO values based on CO relationships
5. **Combines** direct (90%) and indirect (10%) assessments
6. **Generates** detailed Excel reports with results
7. **Manages** temporary files with automatic cleanup
8. **Compares** calculated vs. expected outcomes

The modular architecture allows for easy extension and integration with institutional assessment systems.

---

**Last Updated**: November 2025
**Version**: 1.0
