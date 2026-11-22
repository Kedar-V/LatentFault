import React, { createContext, useContext, useState, useCallback } from 'react';

// Every <E id="..."> text block can be edited in place when edit mode is on.
// Edits are kept in localStorage (per browser) and can be exported/imported as JSON.
const KEY = 'poster-edits-v1';
const Ctx = createContext({ edit: false, edits: {}, save: () => {} });

export function loadEdits() {
  try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { return {}; }
}
export function storeEdits(e) {
  try { localStorage.setItem(KEY, JSON.stringify(e)); } catch { /* storage unavailable */ }
}

export function EditProvider({ edit, edits, setEdits, children }) {
  const save = useCallback((id, html) => {
    setEdits((prev) => { const next = { ...prev, [id]: html }; storeEdits(next); return next; });
  }, [setEdits]);
  return <Ctx.Provider value={{ edit, edits, save }}>{children}</Ctx.Provider>;
}

export function E({ id, as: Tag = 'span', className, style, children }) {
  const { edit, edits, save } = useContext(Ctx);
  const override = edits[id];
  const props = {
    className: (className || '') + (edit ? ' is-editable' : ''),
    style,
    'data-edit-id': id,
    contentEditable: edit || undefined,
    suppressContentEditableWarning: true,
    spellCheck: edit,
    onBlur: edit ? (ev) => save(id, ev.currentTarget.innerHTML) : undefined,
  };
  if (override != null) return <Tag {...props} dangerouslySetInnerHTML={{ __html: override }} />;
  return <Tag {...props}>{children}</Tag>;
}

export function useEditState() {
  const [edits, setEdits] = useState(loadEdits);
  return [edits, setEdits];
}
