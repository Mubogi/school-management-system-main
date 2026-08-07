/**
 * Jordan School Hub — fault-tolerant offline image pipeline.
 * Preview via URL.createObjectURL · IndexedDB queue · multipart POST on reconnect.
 */
(function () {
  'use strict';

  const DB_NAME = 'JordanSchoolHubOffline';
  const STORE = 'pendingUploads';
  const SYNC_URL = '/api/offline-sync/';
  const PING_URL = '/api/offline-sync/ping/';

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 2);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  function getCsrfToken() {
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  async function queueItem(item) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).add({ ...item, createdAt: Date.now(), synced: false });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async function getAllPending() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async function clearQueue() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  function base64ToBlob(b64, mime) {
    const raw = atob(b64);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
    return new Blob([arr], { type: mime || 'application/octet-stream' });
  }

  async function syncViaMultipart(items) {
    const form = new FormData();
    const csrf = getCsrfToken();
    if (csrf) form.append('csrfmiddlewaretoken', csrf);

    items.forEach((item, idx) => {
      if (item.kind === 'image' && item.blob_base64) {
        const blob = item.blob
          ? item.blob
          : base64ToBlob(item.blob_base64, item.mime || 'image/jpeg');
        form.append('photo_' + idx, blob, item.filename || 'upload_' + idx + '.jpg');
        if (item.student_id) form.append('student_id', item.student_id);
      } else if (item.text) {
        form.append('text', item.text);
      }
      if (item.field) form.append('field', item.field);
    });

    const res = await fetch(SYNC_URL, {
      method: 'POST',
      body: form,
      credentials: 'same-origin',
      headers: csrf ? { 'X-CSRFToken': csrf } : {},
    });
    return res.ok;
  }

  async function syncViaJson(items) {
    const csrf = getCsrfToken();
    const res = await fetch(SYNC_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrf ? { 'X-CSRFToken': csrf } : {}),
      },
      credentials: 'same-origin',
      body: JSON.stringify({ items }),
    });
    return res.ok;
  }

  async function drainQueue() {
    if (!navigator.onLine) return;
    const items = await getAllPending();
    if (!items.length) return;

    const hasBlobs = items.some((i) => i.kind === 'image');
    let ok = false;
    try {
      ok = hasBlobs ? await syncViaMultipart(items) : await syncViaJson(items);
    } catch (_) {
      return;
    }
    if (ok) await clearQueue();
  }

  function interceptFileInput(input, previewEl, opts) {
    if (!input) return;
    opts = opts || {};
    input.addEventListener('change', function () {
      const file = input.files && input.files[0];
      if (!file) return;

      const previewUrl = URL.createObjectURL(file);
      if (previewEl) {
        if (file.type.startsWith('image/')) {
          previewEl.innerHTML =
            '<img src="' + previewUrl + '" alt="preview" class="max-w-full h-32 object-cover rounded-lg shadow"/>';
        } else {
          previewEl.textContent = file.name;
        }
      }

      file.arrayBuffer().then(function (buf) {
        const blob = new Blob([buf], { type: file.type });
        const item = {
          kind: 'image',
          filename: file.name,
          mime: file.type,
          blob: blob,
          blob_base64: arrayBufferToBase64(buf),
          previewUrl: previewUrl,
          student_id: opts.studentId || '',
          field: opts.field || input.name || 'photo',
        };
        return queueItem(item);
      }).then(function () {
        if (navigator.onLine) drainQueue();
      });
    });
  }

  function arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }

  function interceptForm(form, previewEl) {
    if (!form) return;
    form.addEventListener('submit', function (e) {
      if (!navigator.onLine) {
        e.preventDefault();
        const fileInput = form.querySelector('input[type=file]');
        if (fileInput && fileInput.files[0]) {
          interceptFileInput(fileInput, previewEl);
        }
      }
    });
    form.querySelectorAll('input[type=file]').forEach(function (inp) {
      interceptFileInput(inp, previewEl);
    });
  }

  window.JordanSchoolHubOffline = {
    queueItem,
    drainQueue,
    interceptFileInput,
    interceptForm,
    getAllPending,
  };

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-offline-photo]').forEach(function (input) {
      const preview = document.querySelector(input.getAttribute('data-preview') || '#offline-preview');
      interceptFileInput(input, preview, {
        studentId: input.getAttribute('data-student-id') || '',
        field: input.getAttribute('data-field') || 'photo',
      });
    });
  });

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    });
  }

  window.addEventListener('online', function () {
    fetch(PING_URL, { method: 'POST' }).finally(drainQueue);
  });
  setInterval(drainQueue, 15000);
})();
