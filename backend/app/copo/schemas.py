from pydantic import BaseModel, Field


class CourseNamesResponse(BaseModel):
    courses: list[str]


class ParseStudentsResponse(BaseModel):
    cos: list[str]
    programmes: dict
    branches: dict
    total_students: int
    upload_id: int
    has_branch_data: bool = False
    default_programmes: list[str] = Field(default_factory=list)
    default_branches: list[str] = Field(default_factory=list)
    parse_message: str = "File analyzed successfully"


class CourseCosResponse(BaseModel):
    cos: list[str]
    indirect_values: dict[str, float]
    found_in_file: bool


class EvaluateRequest(BaseModel):
    course_title: str
    upload_id: int | None = None
    use_default_mapping: bool = True
    programmes: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    indirect_attainment: dict[str, float] = Field(default_factory=dict)
    target_value: int = 50


class CompareEvaluateRequest(BaseModel):
    course_title: str
    upload_id: int
    use_default_mapping: bool = True
    programmes: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    co_attainment_cell: str = ""
    po_attainment_cell: str = ""
    target_value: int = 50


class BulkRowRequest(BaseModel):
    row_id: str
    course_title: str
    upload_id: int | None = None
    co_cell: str = ""
    po_cell: str = ""
    programmes: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)


class BulkEvaluateRequest(BaseModel):
    use_default_mapping: bool = True
    rows: list[BulkRowRequest]


class EvaluationResultResponse(BaseModel):
    public_id: str
    course_title: str
    course_filename: str | None = None
    mapping_filename: str | None = None
    scope_summary: str | None = None
    target_value: int | None = None
    unique_COs: list[str]
    intermediate: dict
    co_warnings: list[str] = Field(default_factory=list)
    download_token: str | None = None
    download_filename: str | None = None
    ephemeral: bool = False
    data_deleted: bool = False
    marks_cleared: bool = False


class AdminDataOverviewResponse(BaseModel):
    runs: list[dict]
    uploads: list[dict]
    archives: list[dict]


class AdminPurgeResponse(BaseModel):
    removed_files: int
    runs_deleted: bool
    message: str


class ComparisonSetup(BaseModel):
    input_sheet: str
    compare_filename: str
    mapping_filename: str
    scope_summary: str
    threshold_rule: str
    delta_note: str = (
        "Delta is shown as Calculated − Read. A zero delta means the recomputed output "
        "matches the uploaded comparison workbook for that value."
    )


class CompareResultResponse(BaseModel):
    course_title: str
    course_filename: str
    compare_filename: str
    mapping_filename: str
    target_value: int
    scope_summary: str
    threshold_rule: str = "max(50, Mean - 0.5*Std)"
    comparison_setup: ComparisonSetup | None = None
    co_warnings: list[str] = Field(default_factory=list)
    co_table: dict
    po_table: dict


class BulkResultResponse(BaseModel):
    results: list[dict]
    mapping_filename: str
    total_rows: int
    success_count: int
    error_count: int


class ClearUploadsResponse(BaseModel):
    removed_files: int
    cleared_sessions: int


class DeleteEvaluationDataResponse(BaseModel):
    removed_files: int
    run_deleted: bool
    message: str
