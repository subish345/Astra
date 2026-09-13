"""Export JSON schemas for qualification test data and procedures."""

import json
from pathlib import Path
from core.qualification.models import QualificationTelemetryFrame, TestProcedureSpec, NonconformanceRecord

SCHEMAS_DIR = Path("qualification/schemas")
SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

# 1. Test data schema
with open(SCHEMAS_DIR / "test_data_schema.json", "w", encoding="utf-8") as f:
    json.dump(QualificationTelemetryFrame.model_json_schema(), f, indent=2)

# 2. Test procedure schema
with open(SCHEMAS_DIR / "test_procedure_schema.json", "w", encoding="utf-8") as f:
    json.dump(TestProcedureSpec.model_json_schema(), f, indent=2)

# 3. Nonconformance schema
with open(SCHEMAS_DIR / "nonconformance_schema.json", "w", encoding="utf-8") as f:
    json.dump(NonconformanceRecord.model_json_schema(), f, indent=2)

print("Exported qualification JSON schemas to qualification/schemas/")
