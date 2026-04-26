/**
 * P7-02 / P7-03 — Persist failed generate-stream payloads for retry when back online.
 * Default: localStorage (max 5). Optional IndexedDB (max 30) when `NEXT_PUBLIC_OFFLINE_QUEUE_IDB=1`
 * for larger payloads / quota headroom. Migrates existing localStorage queue once on first IDB open.
 */

import type { GenerateRequestPayload } from "@/services/api";

const LS_KEY = "nyaya-generate-queue-v1";
const IDB_NAME = "nyayasetu-offline-queue";
const IDB_STORE = "pendingGenerates";
const IDB_VERSION = 1;

const MAX_LS = 5;
const MAX_IDB = 30;

export type QueuedGenerate = {
  id: string;
  createdAt: string;
  payload: GenerateRequestPayload;
};

function useIndexedDbQueue(): boolean {
  return (
    typeof window !== "undefined" &&
    process.env.NEXT_PUBLIC_OFFLINE_QUEUE_IDB === "1" &&
    typeof indexedDB !== "undefined"
  );
}

function maxItems(): number {
  return useIndexedDbQueue() ? MAX_IDB : MAX_LS;
}

function normalizePayload(p: Record<string, unknown>): GenerateRequestPayload | null {
  const ui = p.user_input;
  if (typeof ui !== "string" || !ui.trim()) return null;
  const rl = p.response_language;
  const response_language =
    rl === "hi" || rl === "en" || rl === "hi_latn" ? rl : undefined;
  const cm = p.client_mode;
  const client_mode = cm === "lawyer" || cm === "citizen" ? cm : undefined;
  return {
    user_input: ui.trim(),
    userId: typeof p.userId === "string" ? p.userId : p.userId === null ? null : undefined,
    full_name: typeof p.full_name === "string" ? p.full_name : undefined,
    address: typeof p.address === "string" ? p.address : undefined,
    city: typeof p.city === "string" ? p.city : undefined,
    phone: typeof p.phone === "string" ? p.phone : undefined,
    email: typeof p.email === "string" ? p.email : undefined,
    skip_clarification: p.skip_clarification === true ? true : undefined,
    response_language,
    client_mode,
  };
}

function safeParseLocalStorage(raw: string | null): QueuedGenerate[] {
  if (!raw) return [];
  try {
    const j = JSON.parse(raw) as unknown;
    if (!Array.isArray(j)) return [];
    const out: QueuedGenerate[] = [];
    for (const row of j) {
      if (!row || typeof row !== "object") continue;
      const o = row as Record<string, unknown>;
      const id = typeof o.id === "string" ? o.id : "";
      const createdAt = typeof o.createdAt === "string" ? o.createdAt : "";
      const p = o.payload;
      if (!id || !createdAt || !p || typeof p !== "object") continue;
      const pl = normalizePayload(p as Record<string, unknown>);
      if (!pl) continue;
      out.push({ id, createdAt, payload: pl });
    }
    return out;
  } catch {
    return [];
  }
}

function readQueuedFromLs(): QueuedGenerate[] {
  if (typeof window === "undefined") return [];
  return safeParseLocalStorage(window.localStorage.getItem(LS_KEY));
}

function writeQueuedToLs(list: QueuedGenerate[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LS_KEY, JSON.stringify(list));
}

let idbOpenPromise: Promise<IDBDatabase> | null = null;

function openIdb(): Promise<IDBDatabase> {
  if (idbOpenPromise) return idbOpenPromise;
  idbOpenPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, IDB_VERSION);
    req.onerror = () => reject(req.error ?? new Error("indexedDB open failed"));
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(IDB_STORE)) {
        db.createObjectStore(IDB_STORE, { keyPath: "id" });
      }
    };
  });
  return idbOpenPromise;
}

async function idbGetAll(db: IDBDatabase): Promise<QueuedGenerate[]> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readonly");
    const st = tx.objectStore(IDB_STORE);
    const r = st.getAll();
    r.onerror = () => reject(r.error);
    r.onsuccess = () => {
      const rows = (r.result as unknown[]) ?? [];
      const out: QueuedGenerate[] = [];
      for (const row of rows) {
        if (!row || typeof row !== "object") continue;
        const o = row as Record<string, unknown>;
        const id = typeof o.id === "string" ? o.id : "";
        const createdAt = typeof o.createdAt === "string" ? o.createdAt : "";
        const p = o.payload;
        if (!id || !createdAt || !p || typeof p !== "object") continue;
        const pl = normalizePayload(p as Record<string, unknown>);
        if (!pl) continue;
        out.push({ id, createdAt, payload: pl });
      }
      out.sort((a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0));
      resolve(out);
    };
  });
}

async function idbPutAll(db: IDBDatabase, list: QueuedGenerate[]): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readwrite");
    const st = tx.objectStore(IDB_STORE);
    st.clear();
    for (const item of list) {
      st.put(item);
    }
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error ?? new Error("idb tx aborted"));
  });
}

async function maybeMigrateLsToIdb(db: IDBDatabase): Promise<void> {
  const fromLs = readQueuedFromLs();
  if (fromLs.length === 0) return;
  const existing = await idbGetAll(db);
  if (existing.length > 0) return;
  await idbPutAll(db, fromLs.slice(0, maxItems()));
  window.localStorage.removeItem(LS_KEY);
}

async function readAllAsync(): Promise<QueuedGenerate[]> {
  if (!useIndexedDbQueue()) {
    return readQueuedFromLs();
  }
  const db = await openIdb();
  await maybeMigrateLsToIdb(db);
  return idbGetAll(db);
}

export async function getQueuedGenerateCountAsync(): Promise<number> {
  const q = await readAllAsync();
  return q.length;
}

export async function peekOldestQueuedGenerateAsync(): Promise<QueuedGenerate | null> {
  const q = await readAllAsync();
  return q.length ? q[q.length - 1]! : null;
}

export async function enqueueFailedGenerateAsync(payload: GenerateRequestPayload): Promise<void> {
  if (typeof window === "undefined") return;
  const cap = maxItems();
  const item: QueuedGenerate = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    createdAt: new Date().toISOString(),
    payload: { ...payload },
  };
  if (!useIndexedDbQueue()) {
    const list = readQueuedFromLs();
    list.unshift(item);
    while (list.length > cap) list.pop();
    writeQueuedToLs(list);
    return;
  }
  const db = await openIdb();
  await maybeMigrateLsToIdb(db);
  let list = await idbGetAll(db);
  list.unshift(item);
  while (list.length > cap) {
    list.pop();
  }
  await idbPutAll(db, list);
}

export async function removeQueuedGenerateByIdAsync(id: string): Promise<void> {
  if (typeof window === "undefined") return;
  if (!useIndexedDbQueue()) {
    writeQueuedToLs(readQueuedFromLs().filter((x) => x.id !== id));
    return;
  }
  const db = await openIdb();
  const list = (await idbGetAll(db)).filter((x) => x.id !== id);
  await idbPutAll(db, list);
}

export async function clearQueuedGeneratesAsync(): Promise<void> {
  if (typeof window === "undefined") return;
  if (!useIndexedDbQueue()) {
    window.localStorage.removeItem(LS_KEY);
    return;
  }
  const db = await openIdb();
  await idbPutAll(db, []);
}

/** @deprecated Use async APIs; kept for rare sync-only callers */
export function readQueuedGenerates(): QueuedGenerate[] {
  return readQueuedFromLs();
}

/** @deprecated */
export function getQueuedGenerateCount(): number {
  return readQueuedFromLs().length;
}

/** @deprecated */
export function enqueueFailedGenerate(payload: GenerateRequestPayload): void {
  void enqueueFailedGenerateAsync(payload);
}

/** @deprecated */
export function peekOldestQueuedGenerate(): QueuedGenerate | null {
  const q = readQueuedFromLs();
  return q.length ? q[q.length - 1]! : null;
}

/** @deprecated */
export function removeQueuedGenerateById(id: string): void {
  void removeQueuedGenerateByIdAsync(id);
}

/** @deprecated */
export function clearQueuedGenerates(): void {
  void clearQueuedGeneratesAsync();
}
