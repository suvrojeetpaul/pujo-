from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import ApiResponse, ImportRequest, ImportResult
from app.services.auth import get_current_admin
from app.services.import_service import execute_import, validate_import

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/routes/validate", response_model=ImportResult)
def validate_routes(
    payload: ImportRequest,
    _: User = Depends(get_current_admin),
) -> ImportResult:
    return validate_import(payload)


@router.post("/routes/import", response_model=ApiResponse)
def import_routes(
    payload: ImportRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ApiResponse:
    if payload.dry_run:
        return ApiResponse(data=validate_import(payload).model_dump(), message="Dry run completed")
    result = execute_import(payload, db)
    return ApiResponse(success=result["success"], data=result, message="Routes imported" if result["success"] else "Import failed")
