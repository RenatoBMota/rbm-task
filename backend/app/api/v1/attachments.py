import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.storage import upload_file, get_presigned_download_url, delete_file
from app.api.deps import get_current_user
from app.api.access import require_task_access
from app.crud.attachment import get_attachment, get_attachments, create_attachment, delete_attachment
from app.models.user import User
from app.schemas.attachment import AttachmentOut, AttachmentDownloadURL

router = APIRouter(prefix="/tasks/{task_id}/attachments", tags=["attachments"])


@router.get("", response_model=list[AttachmentOut])
def list_attachments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    return get_attachments(db, task_id)


@router.post("", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)

    data = await file.read()
    object_key = f"tasks/{task_id}/{uuid.uuid4()}_{file.filename}"
    upload_file(object_key, data, file.content_type)
    return create_attachment(
        db,
        task_id=task_id,
        uploaded_by_id=current_user.id,
        filename=file.filename,
        object_key=object_key,
        content_type=file.content_type,
        size_bytes=len(data),
    )


@router.get("/{attachment_id}/download-url", response_model=AttachmentDownloadURL)
def download_attachment(
    task_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    attachment = get_attachment(db, attachment_id)
    if not attachment or attachment.task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado")
    return AttachmentDownloadURL(url=get_presigned_download_url(attachment.object_key))


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_attachment(
    task_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_task_access(db, task_id, current_user.id)
    attachment = get_attachment(db, attachment_id)
    if not attachment or attachment.task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado")
    delete_file(attachment.object_key)
    delete_attachment(db, attachment)
