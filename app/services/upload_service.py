import os
import uuid
import io
from typing import Tuple, Optional
from werkzeug.datastructures import FileStorage
from PIL import Image
from flask import current_app


class UploadService:
    """Service handling secure image upload validation, sanitization, and storage."""

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    ALLOWED_MIMES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB per image limit

    # Known magic byte signatures for image formats
    MAGIC_SIGNATURES = {
        b'\x89PNG\r\n\x1a\n': 'png',
        b'\xff\xd8\xff': 'jpeg',
        b'RIFF': 'webp',
        b'GIF87a': 'gif',
        b'GIF89a': 'gif',
    }

    @classmethod
    def validate_and_save_image(cls, file_obj: FileStorage, user_id: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Validates, sanitizes, re-encodes, and saves an uploaded image.
        Returns (saved_filename, error_message).
        """
        if not file_obj or not file_obj.filename:
            return None, "No file selected."

        # 1. Extension check
        original_name = file_obj.filename
        ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
        if ext not in cls.ALLOWED_EXTENSIONS:
            return None, f"File type .{ext} is not supported. Allowed formats: PNG, JPG, WEBP, GIF."

        # 2. File size check
        file_obj.seek(0, os.SEEK_END)
        file_size = file_obj.tell()
        file_obj.seek(0)

        if file_size > cls.MAX_IMAGE_SIZE_BYTES:
            return None, f"File is too large ({file_size / (1024*1024):.1f}MB). Max allowed size is 5MB."
        if file_size < 12:
            return None, "File is empty or corrupted."

        # 3. Magic bytes check
        header = file_obj.read(12)
        file_obj.seek(0)

        is_valid_magic = False
        for sig in cls.MAGIC_SIGNATURES:
            if header.startswith(sig):
                is_valid_magic = True
                break

        if not is_valid_magic:
            return None, "Invalid file signature. Uploaded file is not a valid image."

        # 4. Deep image verification & sanitization with Pillow
        try:
            image_bytes = file_obj.read()
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()  # Verifies file integrity without executing code

            # Re-open for actual processing (verify closes/invalidates the stream)
            img = Image.open(io.BytesIO(image_bytes))

            # Convert RGBA / P modes to RGB if saving as WebP/JPEG, preserve alpha for WebP
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                processed_img = img.convert('RGBA')
            else:
                processed_img = img.convert('RGB')

            # Downscale overly large dimensions for performance (max 2000x2000)
            max_dimension = 2000
            if processed_img.width > max_dimension or processed_img.height > max_dimension:
                processed_img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            # Generate completely random, unguessable filename
            secure_filename = f"{uuid.uuid4().hex}.webp"

            # Determine storage folder
            upload_dir = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
            os.makedirs(upload_dir, exist_ok=True)

            target_path = os.path.join(upload_dir, secure_filename)

            # Save sanitized image as WebP (strips dangerous EXIF / scripts)
            processed_img.save(target_path, format='WEBP', quality=85, optimize=True)

            return secure_filename, None

        except Exception as e:
            return None, f"Image processing failed: Invalid or corrupt image data."

    @classmethod
    def delete_image(cls, filename: str) -> bool:
        """Safely removes an image file from storage."""
        if not filename or '/' in filename or '\\' in filename or '..' in filename:
            return False  # Prevent path traversal
        upload_dir = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
        target_path = os.path.join(upload_dir, filename)
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                return True
            except OSError:
                return False
        return False
