import io
from PIL import Image
from werkzeug.datastructures import FileStorage
from app.services.upload_service import UploadService


def create_mock_image(format='PNG', size=(100, 100), color=(0, 229, 255)):
    """Creates a real in-memory image byte stream."""
    img_byte_arr = io.BytesIO()
    image = Image.new('RGB', size, color=color)
    image.save(img_byte_arr, format=format)
    img_byte_arr.seek(0)
    return img_byte_arr


def test_valid_image_upload_and_sanitization(app):
    """Tests that a valid image is verified, sanitized, and stored as WebP."""
    with app.app_context():
        img_stream = create_mock_image(format='PNG')
        file_obj = FileStorage(
            stream=img_stream,
            filename='proof_screenshot.png',
            content_type='image/png'
        )

        saved_filename, err = UploadService.validate_and_save_image(file_obj, user_id=1)
        assert err is None
        assert saved_filename is not None
        assert saved_filename.endswith('.webp')
        assert len(saved_filename) > 20  # UUID4 hex name

        # Cleanup
        UploadService.delete_image(saved_filename)


def test_invalid_extension_rejected(app):
    """Tests rejection of dangerous file extensions."""
    with app.app_context():
        stream = io.BytesIO(b"echo 'malicious script'")
        file_obj = FileStorage(stream=stream, filename='malicious.php')

        saved_filename, err = UploadService.validate_and_save_image(file_obj, user_id=1)
        assert saved_filename is None
        assert 'not supported' in err


def test_fake_image_magic_bytes_rejected(app):
    """Tests rejection of polyglot or non-image content masquerading with .png extension."""
    with app.app_context():
        fake_stream = io.BytesIO(b"<html><script>alert(1)</script></html>")
        file_obj = FileStorage(
            stream=fake_stream,
            filename='fake_image.png',
            content_type='image/png'
        )

        saved_filename, err = UploadService.validate_and_save_image(file_obj, user_id=1)
        assert saved_filename is None
        assert 'Invalid file signature' in err or 'failed' in err
