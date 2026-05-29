# Raport Projektowy: PRISM Study Mode (Faza 1 i 2)

Niniejszy dokument przedstawia wyniki badań nad nauką o uczeniu się oraz koncepcje trybów nauki dla systemu PRISM.

## 1. Techniki uczenia się

| Technika | Na czym polega | Dowód + Źródło | Jak w sofcie (PRISM) |
| :--- | :--- | :--- | :--- |
| **Active Recall (Aktywne Przypominanie)** | Zmuszanie mózgu do wydobycia informacji z pamięci zamiast pasywnego czytania. | Roediger & Karpicke (2006): Testowanie daje lepszą retencję długoterminową niż ponowne czytanie. | Ukrywanie fragmentów tekstu ("cloze deletion"), generowanie pytań otwartych przed wyświetleniem odpowiedzi. |
| **Spaced Repetition (Interwałowe Powtórki)** | Powtarzanie materiału w coraz większych odstępach czasu, tuż przed momentem zapomnienia. | Woźniak (1990) / Ye (2022): Algorytmy SM-2/FSRS optymalizują czas nauki o ~30% względem metod tradycyjnych. | Harmonogram powtórek oparty na algorytmie FSRS zintegrowany z bazą Qdrant dla każdego "atomu wiedzy". |
| **Interleaving (Przeplatanie)** | Mieszanie różnych tematów lub typów zadań podczas jednej sesji zamiast blokowej nauki jednego tematu. | Bjork (1994): "Desirable difficulties" — utrudnienie nauki w krótkim terminie zwiększa trwałość wiedzy. | Automatyczne wstrzykiwanie pytań z poprzednich rozdziałów do bieżącej sesji nauki, aby wymusić przełączanie kontekstu. |
| **Feynman Technique / Self-Explanation** | Wyjaśnianie złożonego tematu prostymi słowami, "jak dla 10-latka". | Chi et al. (1994): Uczniowie wyjaśniający sobie materiał budują głębsze modele mentalne (g=0.55). | Tryb "Sokratejski": LLM prosi użytkownika o wyjaśnienie pojęcia i punktuje "luki" w modelu (knowledge gaps). |
| **Dual Coding (Podwójne Kodowanie)** | Łączenie informacji werbalnej (tekst) z wizualną (obrazy/diagramy). | Paivio (1971): Przetwarzanie dwoma kanałami tworzy silniejsze ślady pamięciowe. | Wyświetlanie wyekstrahowanych z PDF wzorów LaTeX i tabel obok tekstu; generowanie diagramów Mermaid z treści. |
| **Cognitive Load Theory (Teoria Obciążenia Poz.)** | Projektowanie tak, by nie przeciążać pamięci operacyjnej (limit ~4-7 elementów). | Sweller (1988): Redukcja "extraneous load" (szumu) pozwala na "germane load" (budowanie schematów). | "Focus Mode": prezentacja tylko jednego "atomu wiedzy" na raz, progresywne ujawnianie szczegółów (chunking). |
| **SQ3R / Reading Strategies** | Systematyczny proces: Survey, Question, Read, Recite, Review. | Robinson (1946): Aktywne podejście do tekstu przed i po czytaniu znacząco podnosi zrozumienie. | Automatyczne generowanie pytań (Q) z nagłówków sekcji przed ich przeczytaniem (R). |
| **Elaboration (Opracowywanie)** | Łączenie nowej wiedzy z tym, co już wiemy; szukanie analogii. | Bisra et al. (2018): Generatywne przetwarzanie informacji wzmacnia ślady pamięciowe. | Funkcja "Connect": system prosi o wskazanie podobieństwa między nowym wzorem a tym z rozdziału 1. |

---

## 2. Koncepcje Study Mode

### Koncepcja A: "Scaffolded Discovery" (Cold Start)
*Filozofia: Redukcja lęku przed nowym materiałem poprzez budowę "szkieletu" wiedzy przed czytaniem.*

*   **Przepływ użytkownika:**
    1. System prezentuje "Wielką Mapę" (graf) rozdziałów wyekstrahowanych przez `structure.py`.
    2. Dla każdego węzła system pokazuje "Zalążek": 1 definicję, 1 kluczowy wzór i 1 analogię (Dual Coding).
    3. Użytkownik "odblokowuje" głębię (pełny tekst) dopiero po przejściu mini-testu sprawdzającego fundamenty.
    4. Minimalne pisanie: Użytkownik klika w węzły i ocenia swoje zrozumienie ("Znam to", "Wyjaśnij prościej").
*   **Ekstrakcja z książki:** Hierarchia nagłówków, słownik pojęć, kluczowe diagramy/tabele, zależności (rozdział A wymaga rozdziału B).
*   **Sekwencjonowanie:** Logiczne, "bottom-up" (od fundamentów do aplikacji).
*   **Techniki:** Cognitive Load Theory (chunking), Dual Coding, SQ3R (Survey).
*   **Active Recall:** "Bridge Quizzes" — 2-3 pytania sprawdzające, czy użytkownik jest gotowy na trudniejszy materiał.

### Koncepcja B: "Cram Catalyst" (Tryb Sesja)
*Filozofia: Maksymalna gęstość informacji w minimalnym czasie. Priorytetyzacja "High Impact".*

*   **Przepływ użytkownika:**
    1. Użytkownik podaje termin egzaminu i kluczowe zagadnienia.
    2. System analizuje książkę i wskazuje "Strefy Zagęszczenia" (rozdziały z największą ilością definicji i wzorów).
    3. System generuje "Cheat Sheets" (LaTeX + bullet points) z opcją "Blurting": użytkownik ma 2 minuty na napisanie wszystkiego, co pamięta o sekcji, system nanosi poprawki.
    4. Intensywne sesje Active Recall: system pyta tylko o najtrudniejsze fragmenty (interwały liczone w minutach, nie dniach).
*   **Ekstrakcja z książki:** Wzory LaTeX, pogrubione terminy, podsumowania rozdziałów, listy kroków/procedur.
*   **Sekwencjonowanie:** Według "Wagi Egzaminacyjnej" (LLM ocenia ważność na bazie struktury kursu/indeksu).
*   **Techniki:** Testing Effect, Spaced Repetition (przyspieszone), Cognitive Load Theory (usuwanie szumu).
*   **Active Recall:** "Blurting Mode" — użytkownik pisze "na brudno", system porównuje to z wektorami w Qdrant i pokazuje pominięte fakty.

### Koncepcja C: "The Feynman Partner" (Głębokie Zrozumienie)
*Filozofia: Nauka przez dialog i syntezę. System jako dociekliwy uczeń.*

*   **Przepływ użytkownika:**
    1. System wybiera złożony koncept (np. mechanika kwantowa) i prosi: "Wyjaśnij mi to, jakbym miał 10 lat".
    2. Użytkownik pisze/mówi wyjaśnienie. System analizuje je pod kątem błędów logicznych (Self-explanation).
    3. System stosuje "Interleaving": "Świetnie, a jak to się ma do termodynamiki, o której rozmawialiśmy wczoraj?"
    4. Progresywne podsumowanie: System generuje skrót, użytkownik go edytuje, system kompresuje jeszcze bardziej.
*   **Ekstrakcja z książki:** Łańcuchy dowodzenia (proofs), relacje międzykontekstowe, przykłady z życia (case studies).
*   **Sekwencjonowanie:** Przeplatane (Interleaved) — częste powroty do dawnych tematów w nowym kontekście.
*   **Techniki:** Feynman Technique, Interleaving, Elaboration.
*   **Active Recall:** "Socratic Chat" — system nie daje odpowiedzi, tylko zadaje pytania prowadzące do wniosku.
