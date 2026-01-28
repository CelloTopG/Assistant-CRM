frappe.ui.form.on('Survey Response', {
  refresh(frm) {
    // Enforce read-only on sentiment score in UI as an extra safeguard
    try {
      frm.set_df_property('sentiment_score', 'read_only', 1);
      // Hide raw JSON answers field from agents
      frm.set_df_property('answers', 'hidden', 1);
      // Render formatted answers
      render_formatted_answers(frm);
    } catch (e) {
      console.warn('Survey Response UI init warning:', e);
    }
  },

  after_save(frm) {
    // Re-render in case server recalculated something
    render_formatted_answers(frm);
  }
});

function render_formatted_answers(frm) {
  const field = frm.get_field('answers_display');
  if (!field || !field.$wrapper) return;

  let answers = [];
  try {
    const raw = frm.doc.answers;
    if (!raw) {
      field.$wrapper.html('<div class="text-muted">No responses yet.</div>');
      return;
    }
    answers = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (!Array.isArray(answers)) {
      field.$wrapper.html('<div class="text-muted">No responses yet.</div>');
      return;
    }
  } catch (e) {
    field.$wrapper.html('<div class="text-muted">Unable to parse responses.</div>');
    return;
  }

  const makeRow = (i, q, a) => `
    <div class="mb-3">
      <div class="fw-bold">Question ${i}: ${frappe.utils.escape_html(q)}</div>
      <div><span class="text-muted">Answer:</span> ${a}</div>
    </div>`;

  const fmtValue = (ans) => {
    const type = (ans.type || '').toLowerCase();
    const val = ans.value;

    if (type === 'rating') {
      const v = parseFloat(val || 0);
      const stars = Array.from({ length: 5 }, (_, i) => i < v ? '★' : '☆').join('');
      return `<span>${stars} <span class="text-muted">(${v})</span></span>`;
    }

    if (type === 'multiple_choice' || Array.isArray(val)) {
      const items = (Array.isArray(val) ? val : [])
        .map((x) => frappe.utils.escape_html(String(x)))
        .join(', ');
      return items || '<span class="text-muted">—</span>';
    }

    if (type === 'yes_no') {
      return String(val).toLowerCase() === 'true' || val === 1 || val === true ? 'Yes' : 'No';
    }

    // default: text or other
    return frappe.utils.escape_html(val == null ? '' : String(val)) || '<span class="text-muted">—</span>';
  };

  let html = '';
  answers.forEach((ans, idx) => {
    const i = idx + 1;
    const qText = ans.question || ans.question_text || ans.label || `Question ${i}`;
    const aHtml = fmtValue(ans);
    html += makeRow(i, qText, aHtml);
  });

  if (!html) {
    html = '<div class="text-muted">No responses yet.</div>';
  }

  field.$wrapper.html(`<div class="aw-answers">${html}</div>`);
}

