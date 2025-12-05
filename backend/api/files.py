"""
File Upload and Processing API Endpoints
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from backend.services.file_processing_service import get_file_processing_service
from backend.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    process: bool = Form(True),
    index_to_rag: bool = Form(True),
    user = Depends(get_current_user)
):
    """
    Upload a file and optionally process and index it.

    - **file**: File to upload (PDF, image, or text)
    - **process**: Whether to extract text from the file
    - **index_to_rag**: Whether to index to RAG system
    """
    file_service = get_file_processing_service()
    user_id = user["user_id"]

    try:
        # Validate file
        file_size = 0
        contents = await file.read()
        file_size = len(contents)
        await file.seek(0)  # Reset file pointer

        validation = file_service.validate_file(
            filename=file.filename,
            file_size=file_size
        )

        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["error"])

        # Upload file
        upload_result = await file_service.upload_file(
            file=contents,
            filename=file.filename,
            user_id=user_id,
            metadata={"original_filename": file.filename}
        )

        response = {
            "file_id": upload_result["file_id"],
            "filename": upload_result["filename"],
            "file_size": upload_result["file_size"],
            "file_type": validation["file_type"],
            "uploaded_at": upload_result["uploaded_at"],
        }

        # Process and index if requested
        if process and index_to_rag:
            processing_result = await file_service.process_and_index(
                file_id=upload_result["file_id"],
                file_path=upload_result["file_path"],
                file_type=validation["file_type"],
                user_id=user_id,
                filename=file.filename
            )

            response["processed"] = processing_result["indexed"]
            response["text_length"] = processing_result.get("text_length", 0)

            if not processing_result["indexed"]:
                response["processing_error"] = processing_result.get("error")

        logger.info(
            f"File uploaded: user={user_id}, file_id={upload_result['file_id']}, "
            f"size={file_size} bytes"
        )

        return JSONResponse(content=response, status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    process: bool = Form(True),
    index_to_rag: bool = Form(True),
    user = Depends(get_current_user)
):
    """
    Upload multiple files at once.

    - **files**: List of files to upload
    - **process**: Whether to extract text from files
    - **index_to_rag**: Whether to index to RAG system
    """
    file_service = get_file_processing_service()
    user_id = user["user_id"]

    results = []
    errors = []

    for file in files:
        try:
            # Read file
            contents = await file.read()
            file_size = len(contents)
            await file.seek(0)

            # Validate
            validation = file_service.validate_file(
                filename=file.filename,
                file_size=file_size
            )

            if not validation["valid"]:
                errors.append({
                    "filename": file.filename,
                    "error": validation["error"]
                })
                continue

            # Upload
            upload_result = await file_service.upload_file(
                file=contents,
                filename=file.filename,
                user_id=user_id
            )

            result = {
                "file_id": upload_result["file_id"],
                "filename": upload_result["filename"],
                "file_size": upload_result["file_size"],
                "file_type": validation["file_type"],
            }

            # Process and index
            if process and index_to_rag:
                processing_result = await file_service.process_and_index(
                    file_id=upload_result["file_id"],
                    file_path=upload_result["file_path"],
                    file_type=validation["file_type"],
                    user_id=user_id,
                    filename=file.filename
                )
                result["indexed"] = processing_result["indexed"]

            results.append(result)

        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {e}")
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })

    return {
        "uploaded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.get("/search")
async def search_files(
    query: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    user = Depends(get_current_user)
):
    """
    Search uploaded files using RAG.

    - **query**: Search query
    - **top_k**: Number of results to return (1-20)
    """
    file_service = get_file_processing_service()
    user_id = user["user_id"]

    try:
        results = await file_service.search_files(
            user_id=user_id,
            query=query,
            top_k=top_k
        )

        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"File search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats."""
    file_service = get_file_processing_service()

    return {
        "formats": file_service.SUPPORTED_TYPES,
        "max_sizes": file_service.MAX_FILE_SIZE
    }


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user = Depends(get_current_user)
):
    """
    Delete an uploaded file.

    - **file_id**: File identifier
    """
    file_service = get_file_processing_service()
    user_id = user["user_id"]

    try:
        result = await file_service.delete_file(
            file_id=file_id,
            user_id=user_id
        )

        logger.info(f"File deleted: user={user_id}, file_id={file_id}")
        return result

    except FileNotFoundError as e:
        logger.warning(f"File not found: {file_id}, user={user_id}")
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_id}"
        )
    except Exception as e:
        logger.error(f"File deletion error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting file: {str(e)}"
        )
