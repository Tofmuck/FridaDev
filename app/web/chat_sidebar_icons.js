'use strict';

const SIDEBAR_ICON_NAMES = Object.freeze(new Set([
  'arrow-down',
  'arrow-up',
  'check',
  'chevron-down',
  'chevron-right',
  'chevron-up',
  'circle',
  'circle-dot',
  'download',
  'external-link',
  'file-output',
  'file-plus',
  'file-text',
  'grip-vertical',
  'image',
  'message-circle',
  'notebook-pen',
  'paperclip',
  'pencil',
  'plus',
  'rotate-ccw',
  'scan-text',
  'sparkles',
  'trash-2',
]));

function createSidebarIcon(documentObj, iconName, className = '') {
  if (!documentObj || !SIDEBAR_ICON_NAMES.has(iconName)) return null;
  const icon = documentObj.createElement('span');
  icon.className = `sidebar-icon${className ? ` ${className}` : ''}`;
  icon.setAttribute('aria-hidden', 'true');
  icon.setAttribute('data-sidebar-icon', iconName);
  return icon;
}

function setSidebarButtonIcon(button, documentObj, iconName) {
  if (!button) return null;
  button.textContent = '';
  const icon = createSidebarIcon(documentObj, iconName);
  if (icon) button.appendChild(icon);
  return icon;
}

const FridaChatSidebarIcons = Object.freeze({
  createSidebarIcon,
  setSidebarButtonIcon,
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = FridaChatSidebarIcons;
}

if (typeof window !== 'undefined') {
  window.FridaChatSidebarIcons = FridaChatSidebarIcons;
}
