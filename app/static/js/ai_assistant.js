/**
 * Shroud's Lockin Crib (SLC) - AI Assistant Client
 */
document.addEventListener('DOMContentLoaded', () => {
  const aiForm = document.getElementById('aiPromptForm');
  const aiInput = document.getElementById('aiPromptInput');
  const aiSubmitBtn = document.getElementById('btnAiSubmit');
  const aiOutputCard = document.getElementById('aiPlanOutput');
  const quickChips = document.querySelectorAll('.ai-chip');

  if (!aiForm) return;

  // Quick chip click
  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      aiInput.value = chip.dataset.prompt;
      aiForm.dispatchEvent(new Event('submit'));
    });
  });

  aiForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = aiInput.value.trim();
    if (!query) return;

    aiSubmitBtn.disabled = true;
    aiSubmitBtn.innerHTML = '⚡ Formulating Strategy...';
    aiOutputCard.style.display = 'block';
    aiOutputCard.innerHTML = `
      <div style="text-align: center; padding: 2rem;">
        <div class="flame-pulse" style="font-size: 2rem;">🔥</div>
        <p style="color: var(--text-secondary); margin-top: 1rem;">Analyzing goal parameters and structuring high-impact lock-in plan...</p>
      </div>
    `;

    try {
      const res = await fetch('/ai/suggest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.csrfToken
        },
        body: JSON.stringify({ query: query })
      });

      const data = await res.json();
      if (data.success && data.plan) {
        renderPlan(data.plan);
      } else {
        aiOutputCard.innerHTML = `<div class="alert alert-danger">${data.error || 'Failed to generate plan.'}</div>`;
      }
    } catch (err) {
      aiOutputCard.innerHTML = `<div class="alert alert-danger">Network error connecting to AI engine.</div>`;
    } finally {
      aiSubmitBtn.disabled = false;
      aiSubmitBtn.innerHTML = '⚡ Generate Lock-In Plan';
    }
  });

  function renderPlan(plan) {
    let scheduleHtml = '';
    if (plan.schedule && plan.schedule.length > 0) {
      scheduleHtml = plan.schedule.map(item => `
        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 0.75rem; border-left: 4px solid var(--accent-cyan);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
            <span style="font-weight: 800; color: var(--accent-cyan); font-size: 0.85rem; text-transform: uppercase;">${item.phase || 'PHASE'}</span>
            <span class="badge-pill badge-rare">${item.duration_minutes} MINS</span>
          </div>
          <h4 style="font-size: 1.05rem; margin-bottom: 0.25rem;">${escapeHtml(item.title)}</h4>
          <p style="color: var(--text-secondary); font-size: 0.9rem;">${escapeHtml(item.description)}</p>
        </div>
      `).join('');
    }

    aiOutputCard.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <span class="badge-pill badge-uncommon" style="margin-bottom: 0.5rem;">${plan.topic || 'FOCUSED LOCK-IN'}</span>
          <h3 style="font-size: 1.4rem;">🎯 Tactical Lock-In Blueprint</h3>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 1.3rem; font-weight: 800; color: var(--accent-cyan); font-family: var(--font-mono);">${plan.total_hours_formatted || plan.total_minutes + 'm'}</div>
          <span style="font-size: 0.8rem; color: var(--text-muted);">${plan.pomodoro_cycles || ''}</span>
        </div>
      </div>

      <div style="margin-bottom: 1.5rem;">
        ${scheduleHtml}
      </div>

      <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.1) 0%, rgba(15, 23, 42, 0.9) 100%); border: 1px solid rgba(249, 115, 22, 0.3); border-radius: var(--radius-md); padding: 1rem 1.25rem;">
        <div style="font-size: 0.8rem; font-weight: 800; color: #fb923c; text-transform: uppercase; margin-bottom: 0.25rem;">DISCIPLINE MANDATE</div>
        <p style="font-style: italic; color: #f8fafc; font-size: 0.95rem;">"${escapeHtml(plan.motivation || 'Lock in and execute without compromise.')}"</p>
      </div>

      <div style="margin-top: 1.25rem; font-size: 0.75rem; color: var(--text-muted); text-align: right;">
        Engine: ${escapeHtml(plan.provider_used || 'SLC Heuristic Assistant')}
      </div>
    `;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
});
