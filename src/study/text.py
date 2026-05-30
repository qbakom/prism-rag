"""Sklejanie pofragmentowanego tekstu z powrotem w ciągły materiał.

Chunker nakłada sąsiednie fragmenty o `chunk_overlap` znaków (domyślnie 200),
więc naiwne `"\\n\\n".join(chunks)` powtarza tekst na granicach fragmentów.
W trybie nauki (reader, materiał do quizu) to widoczne dublowanie zdań.

`stitch_overlapping` skleja fragmenty po kolei, wykrywając najdłuższy sufiks
dotychczasowego tekstu, który jest prefiksem kolejnego fragmentu, i pomija go.
"""


def stitch_overlapping(chunks: list[str], max_overlap: int = 400) -> str:
    """Sklej fragmenty w kolejności czytania, usuwając nakładający się tekst.

    Args:
        chunks: fragmenty już posortowane w kolejności czytania.
        max_overlap: górny limit szukanego nakładania (znaki). Trochę większy
            niż chunk_overlap, by złapać overlap rozjechany o białe znaki.
    """
    result = ""
    for raw in chunks:
        chunk = raw.strip()
        if not chunk:
            continue
        if not result:
            result = chunk
            continue

        # Szukamy najdłuższego nakładania: sufiks `result` == prefiks `chunk`.
        window = min(len(result), len(chunk), max_overlap)
        overlap = 0
        for size in range(window, 0, -1):
            if result[-size:] == chunk[:size]:
                overlap = size
                break

        addition = chunk[overlap:].lstrip() if overlap else chunk
        if addition:
            result += ("\n\n" if not overlap else "") + addition

    return result
