"""Testy sklejania pofragmentowanego tekstu (overlap-aware stitching)."""

from src.study.text import stitch_overlapping


class TestStitchOverlapping:
    def test_empty(self):
        assert stitch_overlapping([]) == ""

    def test_single(self):
        assert stitch_overlapping(["Ala ma kota."]) == "Ala ma kota."

    def test_removes_exact_overlap(self):
        # Chunker robi overlap: koniec chunk1 == początek chunk2.
        c1 = "Metoda Newtona iteruje x_{n+1} = x_n - f(x_n)/f'(x_n)."
        overlap = "x_n - f(x_n)/f'(x_n)."
        c2 = overlap + " Zbiega kwadratowo przy gładkiej f."
        out = stitch_overlapping([c1, c2])
        # Fragment overlapu pojawia się dokładnie raz.
        assert out.count("x_n - f(x_n)/f'(x_n).") == 1
        assert out.endswith("Zbiega kwadratowo przy gładkiej f.")

    def test_no_overlap_keeps_both_with_separator(self):
        out = stitch_overlapping(["Rozdział o FFT.", "Zupełnie inny temat."])
        assert "Rozdział o FFT." in out
        assert "Zupełnie inny temat." in out
        assert "\n\n" in out

    def test_skips_blank_chunks(self):
        out = stitch_overlapping(["Tekst.", "   ", "", "Dalej."])
        assert out == "Tekst.\n\nDalej."

    def test_full_duplicate_collapses(self):
        # Identyczny fragment (overlap == cały chunk) nie dubluje treści.
        chunk = "Dokładnie ten sam akapit."
        out = stitch_overlapping([chunk, chunk])
        assert out == chunk
