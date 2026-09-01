/**
 * Shroud's Lockin Crib (SLC) - Productivity Timer Engine
 */
class LockinTimer {
  constructor() {
    this.mode = 'POMODORO'; // POMODORO, CUSTOM, STOPWATCH
    this.category = 'STUDY';
    this.status = 'IDLE'; // IDLE, RUNNING, PAUSED
    this.targetSeconds = 25 * 60; // 25 mins
    this.elapsedSeconds = 0;
    this.sessionStartTime = null;
    this.timerInterval = null;
    this.totalCircleCircumference = 754; // 2 * PI * 120

    this.digitsEl = document.getElementById('timerDigits');
    this.statusEl = document.getElementById('timerStatus');
    this.circleProgress = document.getElementById('timerCircleProgress');
    this.btnStart = document.getElementById('btnTimerStart');
    this.btnPause = document.getElementById('btnTimerPause');
    this.btnReset = document.getElementById('btnTimerReset');
    this.btnSave = document.getElementById('btnTimerSave');
    this.categorySelect = document.getElementById('timerCategorySelect');
    this.notesInput = document.getElementById('timerNotesInput');

    this.initEvents();
    this.updateDisplay();
  }

  initEvents() {
    // Mode Buttons
    document.querySelectorAll('.timer-mode-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        if (this.status === 'RUNNING') {
          if (!confirm('Switching modes will reset your current timer. Continue?')) return;
        }
        document.querySelectorAll('.timer-mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.setMode(btn.dataset.mode);
      });
    });

    if (this.btnStart) this.btnStart.addEventListener('click', () => this.start());
    if (this.btnPause) this.btnPause.addEventListener('click', () => this.pause());
    if (this.btnReset) this.btnReset.addEventListener('click', () => this.reset());
    if (this.btnSave) this.btnSave.addEventListener('click', () => this.stopAndSave());
  }

  setMode(mode) {
    this.reset();
    this.mode = mode;
    if (mode === 'POMODORO') {
      this.targetSeconds = 25 * 60;
    } else if (mode === 'CUSTOM') {
      const mins = prompt('Enter custom duration in minutes:', '45');
      const parsed = parseInt(mins, 10);
      this.targetSeconds = (!isNaN(parsed) && parsed > 0) ? parsed * 60 : 45 * 60;
    } else if (mode === 'STOPWATCH') {
      this.targetSeconds = 0;
    }
    this.updateDisplay();
  }

  start() {
    if (this.status === 'RUNNING') return;
    if (this.status === 'IDLE') {
      this.sessionStartTime = new Date().toISOString();
    }
    this.status = 'RUNNING';
    this.btnStart.style.display = 'none';
    this.btnPause.style.display = 'inline-flex';
    if (this.btnSave) this.btnSave.disabled = false;

    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
      this.updateDisplay();

      // Pomodoro or countdown completed
      if (this.mode !== 'STOPWATCH' && this.elapsedSeconds >= this.targetSeconds) {
        this.pause();
        this.playAlarmSound();
        alert('🎯 Lock-In session complete! Great work. Save your session now.');
      }
    }, 1000);
  }

  pause() {
    if (this.status !== 'RUNNING') return;
    this.status = 'PAUSED';
    clearInterval(this.timerInterval);
    this.btnStart.style.display = 'inline-flex';
    this.btnPause.style.display = 'none';
    this.btnStart.innerHTML = '▶ Resume';
    this.updateDisplay();
  }

  reset() {
    this.pause();
    this.status = 'IDLE';
    this.elapsedSeconds = 0;
    this.sessionStartTime = null;
    this.btnStart.style.display = 'inline-flex';
    this.btnPause.style.display = 'none';
    this.btnStart.innerHTML = '▶ Start Lock-In';
    this.updateDisplay();
  }

  updateDisplay() {
    let displaySeconds = 0;
    if (this.mode === 'STOPWATCH') {
      displaySeconds = this.elapsedSeconds;
    } else {
      displaySeconds = Math.max(0, this.targetSeconds - this.elapsedSeconds);
    }

    const mins = Math.floor(displaySeconds / 60);
    const secs = displaySeconds % 60;
    const formatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    if (this.digitsEl) this.digitsEl.textContent = formatted;
    document.title = this.status === 'RUNNING' ? `(${formatted}) SLC Timer - Locked In` : "Shroud's Lockin Crib";

    if (this.statusEl) {
      if (this.status === 'RUNNING') this.statusEl.textContent = '🔥 LOCKED IN';
      else if (this.status === 'PAUSED') this.statusEl.textContent = '⏸ PAUSED';
      else this.statusEl.textContent = 'READY TO LOCK IN';
    }

    // Circular SVG progress bar
    if (this.circleProgress && this.mode !== 'STOPWATCH' && this.targetSeconds > 0) {
      const pct = Math.min(1, this.elapsedSeconds / this.targetSeconds);
      const offset = this.totalCircleCircumference * (1 - pct);
      this.circleProgress.style.strokeDashoffset = offset;
    }
  }

  playAlarmSound() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime); // A5 note
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      osc.start();
      osc.stop(ctx.currentTime + 0.6);
    } catch (e) {
      // AudioContext unavailable or blocked
    }
  }

  async stopAndSave() {
    if (this.elapsedSeconds < 60) {
      alert('You must lock in for at least 1 minute before saving.');
      return;
    }

    this.pause();
    const sessionEndTime = new Date().toISOString();
    const cat = this.categorySelect ? this.categorySelect.value : 'STUDY';
    const notes = this.notesInput ? this.notesInput.value : '';

    try {
      const res = await fetch('/timer/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.csrfToken
        },
        body: JSON.stringify({
          start_time: this.sessionStartTime || new Date(Date.now() - this.elapsedSeconds * 1000).toISOString(),
          end_time: sessionEndTime,
          duration_seconds: this.elapsedSeconds,
          mode: this.mode,
          category: cat,
          notes: notes
        })
      });

      const data = await res.json();
      if (data.success) {
        let msg = `✅ Saved ${data.duration_formatted} session! Today's total: ${data.today_hours}h.`;
        if (data.new_badges && data.new_badges.length > 0) {
          msg += `\n🏆 NEW BADGE UNLOCKED: ${data.new_badges.join(', ')}!`;
        }
        alert(msg);
        window.location.reload();
      } else {
        alert(`❌ Failed to save: ${data.error}`);
      }
    } catch (err) {
      alert('Network error saving timer session.');
      console.error(err);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('timerDigits')) {
    window.slcTimer = new LockinTimer();
  }
});
