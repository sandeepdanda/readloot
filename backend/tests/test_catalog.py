"""Tests for catalog search, gated auto-import, and chapter mark-read."""

import time


class TestCatalogSearch:
    def test_search_returns_catalog(self, auth_client):
        resp = auth_client.get("/api/catalog/search")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert {"gutenberg_id", "title", "author"} <= data[0].keys()

    def test_search_filters_by_author(self, auth_client):
        resp = auth_client.get("/api/catalog/search", params={"q": "austen"})
        assert resp.status_code == 200
        titles = [b["title"] for b in resp.json()]
        assert any("Pride and Prejudice" in t for t in titles)

    def test_search_requires_auth(self, client):
        assert client.get("/api/catalog/search").status_code == 401


class TestImport:
    # A tiny fake book with two clear chapters; avoids hitting the network.
    # Three chapters: the splitter needs >=3 headings to trust them over the
    # chunk fallback.
    FAKE_TEXT = (
        "*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\n\n"
        "CHAPTER I.\n\n"
        + ("The intricate melancholy apprentice bewildered the recalcitrant "
           "ephemeral cog. ") * 6
        + "\n\nCHAPTER II.\n\n"
        + ("A perpetual inscrutable solitude enveloped the ubiquitous "
           "luminous village. ") * 6
        + "\n\nCHAPTER III.\n\n"
        + ("The tenacious sagacious mariner pondered the inexorable "
           "tumultuous voyage. ") * 6
        + "\n\n*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
    )

    def _wait_done(self, auth_client, gid, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            s = auth_client.get(f"/api/catalog/import/{gid}/status").json()
            if s["state"] in ("done", "error"):
                return s
            time.sleep(0.2)
        return {"state": "timeout"}

    def test_import_unknown_book_404(self, auth_client):
        assert auth_client.post("/api/catalog/import/99999999").status_code == 404

    def test_import_extracts_gated_words_then_unlock(self, auth_client, monkeypatch):
        from readloot import gutenberg
        monkeypatch.setattr(gutenberg, "fetch_book_text", lambda gid: self.FAKE_TEXT)

        gid = 1342  # Pride and Prejudice (in catalog)
        resp = auth_client.post(f"/api/catalog/import/{gid}")
        assert resp.status_code == 200

        status = self._wait_done(auth_client, gid)
        assert status["state"] == "done", status
        assert status["words"] > 0
        book_name = status["book_name"]

        # Chapters exist and are LOCKED (have auto-words, not yet read).
        chapters = auth_client.get(
            f"/api/catalog/books/{book_name}/chapters"
        ).json()
        assert len(chapters) >= 2
        assert all(c["is_locked"] for c in chapters)
        assert all(not c["is_read"] for c in chapters)

        # Locked words must NOT be due for review yet.
        due = auth_client.get("/api/review/due").json()
        assert due == []

        # Mark first chapter read -> unlocks its words + awards XP.
        ch1 = chapters[0]
        mr = auth_client.post(f"/api/catalog/chapters/{ch1['id']}/mark-read")
        assert mr.status_code == 200
        body = mr.json()
        assert body["newly_unlocked"] > 0
        assert body["already_read"] is False
        assert body["xp_earned"] == 15

        # Now some words are due, and they are tagged source='auto'.
        due = auth_client.get("/api/review/due").json()
        assert len(due) > 0
        assert all(w["source"] == "auto" for w in due)

        # Re-marking is idempotent.
        again = auth_client.post(f"/api/catalog/chapters/{ch1['id']}/mark-read").json()
        assert again["newly_unlocked"] == 0
        assert again["already_read"] is True

    def test_mark_read_unknown_chapter_404(self, auth_client):
        assert auth_client.post(
            "/api/catalog/chapters/999999/mark-read"
        ).status_code == 404
