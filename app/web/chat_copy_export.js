'use strict';

const EXPORT_TITLE = 'Conversation avec Frida';
const EXPORT_USER_LABEL = 'Tof';
const EXPORT_ASSISTANT_LABEL = 'Frida';

function pad2(value) {
  return String(value).padStart(2, '0');
}

function toDate(value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value;
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatHumanDateTime(value) {
  const date = toDate(value);
  if (!date) return 'date inconnue';
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

function formatFilenameTimestamp(value) {
  const date = toDate(value) || new Date();
  return [
    date.getFullYear(),
    pad2(date.getMonth() + 1),
    pad2(date.getDate()),
    pad2(date.getHours()),
    pad2(date.getMinutes()),
  ].join('-');
}

function roleLabel(role) {
  if (role === 'assistant') return EXPORT_ASSISTANT_LABEL;
  if (role === 'user' || role === 'olive') return EXPORT_USER_LABEL;
  return String(role || 'Message');
}

function exportableMessages(messages) {
  return (Array.isArray(messages) ? messages : [])
    .filter((message) => message && (message.role === 'user' || message.role === 'assistant'))
    .map((message) => ({
      role: message.role,
      content: String(message.content || ''),
      timestamp: message.timestamp || null,
    }));
}

function buildConversationMarkdown({
  messages,
  exportedAt = new Date(),
  title = EXPORT_TITLE,
} = {}) {
  const lines = [
    `# ${String(title || EXPORT_TITLE).trim() || EXPORT_TITLE}`,
    '',
    `Exportée le ${formatHumanDateTime(exportedAt)}`,
    '',
  ];
  const exportedMessages = exportableMessages(messages);
  if (!exportedMessages.length) {
    lines.push('Aucun message à exporter.');
    lines.push('');
    return lines.join('\n');
  }

  for (const message of exportedMessages) {
    lines.push(`## ${roleLabel(message.role)} — ${formatHumanDateTime(message.timestamp)}`);
    lines.push('');
    lines.push(message.content);
    lines.push('');
  }
  return lines.join('\n');
}

function buildMarkdownFilename(value = new Date()) {
  return `frida-conversation-${formatFilenameTimestamp(value)}.md`;
}

async function copyTextToClipboard(text, { navigatorObj, documentObj } = {}) {
  const value = String(text || '');
  const nav = navigatorObj || (typeof navigator !== 'undefined' ? navigator : null);
  if (nav && nav.clipboard && typeof nav.clipboard.writeText === 'function') {
    await nav.clipboard.writeText(value);
    return true;
  }

  const doc = documentObj || (typeof document !== 'undefined' ? document : null);
  if (!doc || typeof doc.createElement !== 'function') return false;
  const textarea = doc.createElement('textarea');
  textarea.value = value;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  doc.body.appendChild(textarea);
  textarea.select();
  let ok = false;
  try {
    ok = typeof doc.execCommand === 'function' ? Boolean(doc.execCommand('copy')) : false;
  } finally {
    textarea.remove();
  }
  return ok;
}

function createCopyButton({ getText, copyText = copyTextToClipboard } = {}) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'msg-copy';
  button.title = 'Copier cette bulle';
  button.setAttribute('aria-label', 'Copier cette bulle');
  button.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
  button.addEventListener('click', async (event) => {
    event.preventDefault();
    event.stopPropagation();
    const text = typeof getText === 'function' ? getText() : '';
    try {
      const copied = await copyText(String(text || ''));
      button.dataset.copied = copied ? 'true' : 'false';
      button.title = copied ? 'Copié' : 'Copie indisponible';
      window.setTimeout(() => {
        delete button.dataset.copied;
        button.title = 'Copier cette bulle';
      }, 1300);
    } catch {
      button.dataset.copied = 'false';
      button.title = 'Copie indisponible';
    }
  });
  return button;
}

function downloadMarkdownFile({
  markdown,
  filename,
  documentObj,
  urlObj,
} = {}) {
  const doc = documentObj || (typeof document !== 'undefined' ? document : null);
  const urlApi = urlObj || (typeof URL !== 'undefined' ? URL : null);
  if (!doc || !urlApi || typeof Blob === 'undefined') return false;
  const blob = new Blob([String(markdown || '')], { type: 'text/markdown;charset=utf-8' });
  const objectUrl = urlApi.createObjectURL(blob);
  const link = doc.createElement('a');
  link.href = objectUrl;
  link.download = String(filename || buildMarkdownFilename());
  link.rel = 'noopener';
  doc.body.appendChild(link);
  link.click();
  link.remove();
  const defer = typeof window !== 'undefined' && typeof window.setTimeout === 'function'
    ? window.setTimeout.bind(window)
    : setTimeout;
  defer(() => urlApi.revokeObjectURL(objectUrl), 0);
  return true;
}

const FridaChatCopyExport = Object.freeze({
  EXPORT_TITLE,
  EXPORT_USER_LABEL,
  EXPORT_ASSISTANT_LABEL,
  formatHumanDateTime,
  formatFilenameTimestamp,
  roleLabel,
  exportableMessages,
  buildConversationMarkdown,
  buildMarkdownFilename,
  copyTextToClipboard,
  createCopyButton,
  downloadMarkdownFile,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaChatCopyExport;
}

if (typeof window !== 'undefined') {
  window.FridaChatCopyExport = FridaChatCopyExport;
}
