/**
 * Shroud's Lockin Crib (SLC) - Core Main Script
 */
document.addEventListener('DOMContentLoaded', () => {
  // Mobile Nav Toggle
  const mobileBtn = document.getElementById('mobileNavToggle');
  const navLinks = document.getElementById('navLinks');
  if (mobileBtn && navLinks) {
    mobileBtn.addEventListener('click', () => {
      navLinks.classList.toggle('open');
    });
  }

  // Auto-dismiss alert banners after 5 seconds
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-10px)';
      setTimeout(() => alert.remove(), 500);
    }, 6000);
  });

  // Setup CSRF header for all AJAX requests
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  window.csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

  // Setup reaction buttons
  document.querySelectorAll('.reaction-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const postId = btn.dataset.postId;
      const reactionType = btn.dataset.reaction;

      try {
        const res = await fetch(`/community/post/${postId}/react`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrfToken
          },
          body: JSON.stringify({ reaction_type: reactionType })
        });
        const data = await res.json();
        if (data.success) {
          btn.classList.toggle('active', data.toggled);
          const countSpan = btn.querySelector('.reaction-count');
          if (countSpan) {
            countSpan.textContent = data.counts[reactionType] || 0;
          }
        }
      } catch (err) {
        console.error('Reaction toggle failed:', err);
      }
    });
  });
});
