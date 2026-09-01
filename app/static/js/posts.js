/**
 * Shroud's Lockin Crib (SLC) - Posts & Uploads Client Script
 */
document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('postImagesInput');
  const previewContainer = document.getElementById('imagePreviewGrid');
  const privacySelect = document.getElementById('privacySelect');
  const privacyNotice = document.getElementById('privacyNotice');

  // Multi-image client preview
  if (fileInput && previewContainer) {
    fileInput.addEventListener('change', (e) => {
      previewContainer.innerHTML = '';
      const files = Array.from(e.target.files).slice(0, 5); // limit to 5

      files.forEach(file => {
        if (!file.type.startsWith('image/')) return;

        const reader = new FileReader();
        reader.onload = (event) => {
          const thumb = document.createElement('div');
          thumb.className = 'post-image-thumb';
          thumb.style.position = 'relative';
          thumb.innerHTML = `
            <img src="${event.target.result}" alt="Preview">
            <span style="position: absolute; bottom: 4px; right: 4px; background: rgba(0,0,0,0.7); font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; color: #fff;">
              ${(file.size / (1024 * 1024)).toFixed(1)}MB
            </span>
          `;
          previewContainer.appendChild(thumb);
        };
        reader.readAsDataURL(file);
      });
    });
  }

  // Dynamic privacy state notice
  if (privacySelect && privacyNotice) {
    privacySelect.addEventListener('change', () => {
      if (privacySelect.value === 'COMMUNITY') {
        privacyNotice.innerHTML = '🌐 <strong>COMMUNITY:</strong> This log will be publicly visible to other members on the community feed.';
        privacyNotice.className = 'form-hint alert alert-info';
      } else {
        privacyNotice.innerHTML = '🔒 <strong>PRIVATE:</strong> Only you (and community moderators for safety) can view this entry.';
        privacyNotice.className = 'form-hint alert alert-warning';
      }
    });
  }
});
