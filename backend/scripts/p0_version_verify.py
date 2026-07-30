"""P0: Version management end-to-end verification via HTTP API."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
results: list[tuple[str, str, str]] = []


def req(method: str, path: str, data=None, token=None):
    url = BASE + path
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            detail = json.loads(raw)
        except Exception:
            detail = raw
        return e.code, detail
    except Exception as e:
        return 0, {"error": str(e)}


def ok(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    results.append((status, name, detail))
    suffix = f" — {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return cond


def main() -> int:
    print("=== P0 Version Management Verification ===")

    code, data = req("POST", "/auth/login", {"username": "admin", "password": "admin123"})
    token = data.get("access_token") if isinstance(data, dict) else None
    if not ok("login", code == 200 and bool(token), f"status={code}"):
        print(data)
        return 1

    kb_name = f"p0-version-{int(time.time())}"
    code, kb = req(
        "POST",
        "/knowledge-bases",
        {
            "name": kb_name,
            "description": "P0 version verification",
            "visibility": "private",
        },
        token,
    )
    kb_id = kb.get("id") if isinstance(kb, dict) else None
    if not ok("create_kb", code in (200, 201) and bool(kb_id), f"status={code} id={kb_id}"):
        print(kb)
        return 1

    code, doc_a = req(
        "POST",
        f"/knowledge-bases/{kb_id}/documents/push",
        {
            "filename": "doc_a.txt",
            "content": "Document A content for version v1 only base.",
            "metadata": {"tag": "A"},
        },
        token,
    )
    doc_a_id = doc_a.get("id") if isinstance(doc_a, dict) else None
    ok("push_doc_a", code in (200, 201) and bool(doc_a_id), f"status={code} id={doc_a_id}")

    code, v1 = req(
        "POST",
        f"/knowledge-bases/{kb_id}/versions",
        {"description": "v1 with doc A only", "tags": "v1,p0"},
        token,
    )
    v1_id = v1.get("id") if isinstance(v1, dict) else None
    v1_no = v1.get("version") if isinstance(v1, dict) else None
    ok("snapshot_v1", code in (200, 201) and bool(v1_id), f"status={code} version={v1_no}")

    code, doc_b = req(
        "POST",
        f"/knowledge-bases/{kb_id}/documents/push",
        {
            "filename": "doc_b.txt",
            "content": "Document B content added after v1.",
            "metadata": {"tag": "B"},
        },
        token,
    )
    doc_b_id = doc_b.get("id") if isinstance(doc_b, dict) else None
    ok("push_doc_b", code in (200, 201) and bool(doc_b_id), f"status={code} id={doc_b_id}")

    code, v2 = req(
        "POST",
        f"/knowledge-bases/{kb_id}/versions",
        {"description": "v2 with doc A and B", "tags": "v2,p0"},
        token,
    )
    v2_id = v2.get("id") if isinstance(v2, dict) else None
    v2_no = v2.get("version") if isinstance(v2, dict) else None
    ok("snapshot_v2", code in (200, 201) and bool(v2_id), f"status={code} version={v2_no}")

    code, vlist = req(
        "GET", f"/knowledge-bases/{kb_id}/versions?page=1&page_size=20", token=token
    )
    items = vlist.get("items", []) if isinstance(vlist, dict) else []
    ok("list_versions", code == 200 and len(items) >= 2, f"count={len(items)}")

    code, switched = req("POST", f"/versions/{v1_id}/switch", token=token)
    active = switched.get("is_active") if isinstance(switched, dict) else None
    ok("switch_to_v1", code == 200 and active is True, f"status={code} active={active}")

    code, docs = req(
        "GET", f"/knowledge-bases/{kb_id}/documents?page=1&page_size=50", token=token
    )
    doc_items = docs.get("items", []) if isinstance(docs, dict) else []
    names = sorted(d.get("file_name") for d in doc_items)
    only_a = names == ["doc_a.txt"]
    total = docs.get("total") if isinstance(docs, dict) else None
    ok("list_after_v1_switch", code == 200 and only_a, f"files={names} total={total}")

    code, all_docs = req(
        "GET",
        f"/knowledge-bases/{kb_id}/documents?page=1&page_size=50&include_inactive=true",
        token=token,
    )
    all_items = all_docs.get("items", []) if isinstance(all_docs, dict) else []
    all_names = sorted(d.get("file_name") for d in all_items)
    ok(
        "list_include_inactive",
        code == 200 and set(all_names) >= {"doc_a.txt", "doc_b.txt"},
        f"files={all_names}",
    )

    code, switched2 = req("POST", f"/versions/{v2_id}/switch", token=token)
    ok("switch_to_v2", code == 200 and switched2.get("is_active") is True, f"status={code}")

    code, docs2 = req(
        "GET", f"/knowledge-bases/{kb_id}/documents?page=1&page_size=50", token=token
    )
    doc_items2 = docs2.get("items", []) if isinstance(docs2, dict) else []
    names2 = sorted(d.get("file_name") for d in doc_items2)
    ok(
        "list_after_v2_switch",
        code == 200 and set(names2) == {"doc_a.txt", "doc_b.txt"},
        f"files={names2}",
    )

    code, cmp = req("GET", f"/versions/compare?v1={v1_id}&v2={v2_id}", token=token)
    summary = cmp.get("summary", {}) if isinstance(cmp, dict) else {}
    ok(
        "compare_versions",
        code == 200 and summary.get("added_count", 0) >= 1,
        f"summary={summary}",
    )

    code, stats = req("GET", f"/knowledge-bases/{kb_id}/stats", token=token)
    ok(
        "kb_stats",
        code == 200 and isinstance(stats, dict) and "document_count" in stats,
        f"stats={stats if isinstance(stats, dict) else None}",
    )

    print("---")
    failed = [r for r in results if r[0] == "FAIL"]
    print(f"Total={len(results)} PASS={len(results) - len(failed)} FAIL={len(failed)}")
    print(f"kb_id={kb_id}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
