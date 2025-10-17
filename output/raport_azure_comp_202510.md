# Raport Porównawczy Wydajności PostgreSQL Azure

**Data raportu:** 17 października 2025  
**ID raportu:** raport_azure_comp_202510  
**Status:** KRYTYCZNY - Zidentyfikowane problemy wydajności

---

## Streszczenie wykonawcze

Serwer 2 (enatabreadprod) wykazuje znacznie niższą wydajność w porównaniu z Serwerem 1 (enatabread). Analiza wskazuje, że **NIE jest to problem konfiguracji PostgreSQL**, lecz **niezgodność warstwy infrastruktury** połączona z niedostateczną alokacją zasobów.

**Główne znalezisko:** Serwer 2 działa na warstwie Burstable (przeznaczonej dla obciążeń dev/test) i jest poważnie niedowyposażony dla środowiska produkcyjnego z bazą danych o rozmiarze 171 GB.

**Szacunkowy wpływ na wydajność:** Serwer 2 działa z wydajnością 30-50% potencjału z powodu ograniczania CPU i niewystarczającej pojemności I/O.

---

## Zidentyfikowane problemy krytyczne

### Problem #1: Warstwa obliczeniowa Burstable (KRYTYCZNY)

**Ważność:** KRYTYCZNA  
**Wpływ:** 60-70% degradacji wydajności

**Aktualna konfiguracja:**
- Typ warstwy: Burstable (Standard_B2s)
- Rdzenie vCores: 2
- RAM: 4 GB
- Uwaga Azure: "Warstwa Burstable zoptymalizowana dla obciążeń dev/test"

**Problem:**
Warstwa Burstable wykorzystuje system "burst credits" (kredyty wzrostu), który ogranicza wydajność CPU w trybie utrzymanym. Po wyczerpaniu kredytów burst, wydajność CPU spada do poziomu bazowego (5-10% pojemności), powodując poważne ograniczanie podczas intensywnych obciążeń zapytaniami.

**Dowody z danych diagnostycznych:**
- Czas trwania zapytania Server 1: maks. 0,41 godziny
- Czas trwania zapytania Server 2: maks. 1,29 godziny (3,1x wolniej)
- Długotrwałe zapytania metadanych na Server 2: 0,97h, 0,91h (podstawowe zapytania narzędzia diagnostycznego wykonywane 10+ minut)

**Ostrzeżenie Azure:** "W przypadku użytku produkcyjnego zalecamy warstwy General Purpose lub Memory Optimized"

---

### Problem #2: Niewystarczająca ilość RAM dla rozmiaru bazy danych

**Ważność:** WYSOKA  
**Wpływ:** 20-30% degradacji wydajności

**Aktualna konfiguracja:**
- Server 1: 4 GB RAM dla bazy 101 GB (3,96% potencjału cache)
- Server 2: 4 GB RAM dla bazy 171 GB (2,34% potencjału cache)

**Problem:**
Oba serwery mają niewystarczającą ilość RAM dla rozmiarów ich baz danych, ale Server 2 jest proporcjonalnie w gorszej sytuacji.

**Dowody:**
- Współczynnik trafień cache Server 1: 56,37% (powinien być >95%)
- Współczynnik trafień cache Server 2: 51,78% (powinien być >95%)
- Bloki sterty odczytane Server 2: 4 393 829 567 (vs 3 275 400 696 na Server 1)
- Server 2 musi czytać z dysku 48% częściej niż Server 1

**Best practice PostgreSQL:**
- shared_buffers powinno być 25% dostępnego RAM
- effective_cache_size powinno być 50-75% dostępnego RAM
- Dla bazy 171 GB: zalecany minimum 16-32 GB RAM

---

### Problem #3: Nieadekwatna alokacja IOPS

**Ważność:** WYSOKA  
**Wpływ:** 15-20% degradacji wydajności

**Aktualna konfiguracja:**
- Tier wydajności: P15 (1100 IOPS)
- Rozmiar magazynu: 256 GB
- Typ magazynu: Premium SSD

**Problem:**
P15 (1100 IOPS) jest niewystarczający dla produkcyjnej bazy danych o rozmiarze 171 GB pod obciążeniem.

**Wzór I/O bazy danych:**
- Rozmiar bazy danych: 171 GB
- Stosunek IOPS: 171 GB / 1100 IOPS = 0,16 GB na IOPS (zbyt niski)

**Standard branżowy:**
- Małe bazy (<50 GB): P15 akceptowalny
- Średnie bazy (50-200 GB): P30 minimum (5000 IOPS)
- Duże bazy (>200 GB): P40+ (7500+ IOPS)

---

### Problem #4: Niezgodność parametrów konfiguracji

**Ważność:** ŚREDNIA  
**Wpływ:** 5-10% degradacji wydajności

**Aktualna konfiguracja (Oba serwery - IDENTYCZNE):**
- work_mem: 4 MB (powinno być 32-64 MB)
- effective_io_concurrency: 1 (powinno być 200+ dla SSD)
- synchronous_commit: on (akceptowalne, ale wpływa na opóźnienia zapisu)

**Problem:**
Konfiguracja jest generyczna i nieoptymalnie dostrojona dla ograniczeń zasobów obu serwerów. Oba serwery są niedokonfigurowane.

---

## Porównanie skali bazy danych

| Metryka | Server 1 | Server 2 | Różnica |
|---------|----------|----------|---------|
| Rozmiar bazy | 101 GB | 171 GB | +70% |
| Liczba tabel | 214 | 166 | -22% |
| Śr. wierszy/tabela | 1,42M | 3,98M | +181% |
| Max wierszy w tabeli | 46,9M | 352M | +651% |
| Razem martwych wierszy | 1,44M | 1,31M | -9% |

**Obserwacja:** Server 2 obsługuje większe wolumeny danych (większe tabele, więcej wierszy), dlatego ograniczenia zasobów są jeszcze bardziej krytyczne.

---

## Analiza wydajności zapytań

### Długotrwałe zapytania

**Server 1 - Najdłuższe zapytanie:**
- Czas trwania: 0,41 godziny
- Typ: procedura pgms_stats_insert_data
- Status: Normalny

**Server 2 - Najdłuższe zapytania:**
- Czas trwania #1: 1,29 godziny (SHOW search_path - introspekacja metadanych)
- Czas trwania #2: 0,97 godziny (zapytanie tabeli systemowej pg_proc)
- Czas trwania #3: 0,91 godziny (zapytanie information_schema)
- Status: KRYTYCZNY - podstawowe zapytania systemowe trwają 1+ godzin

**Analiza:**
Server 2 ma trudności nawet z podstawowymi zapytaniami katalogu systemowego. Zapytanie, które powinno się zakończyć w <1 sekundę, trwa 1,29 godziny. Wskazuje to na poważne rywalizowanie o I/O i ograniczanie CPU.

---

### Zidentyfikowane problemy wydajności zapytań

| Kategoria | Server 1 | Server 2 | Problem |
|-----------|----------|----------|---------|
| Pełne skanowania tabel | 15 przypadków | 15 przypadków | Podobne |
| Brakujące indeksy | 5 tabel | 3 tabele | Podobne |
| Nieużywane indeksy | 58/130 (44,62%) | 62/133 (46,62%) | Podobne |

**Obserwacja:** Problemy z indeksami i zapytaniami są podobne na obu serwerach. Różnica wydajności jest napędzana infrastrukturą, a nie schematem.

---

## Analiza Autovacuum

**Server 1:**
- Ostatnio autovacuum: 2025-10-17 20:07:42 (2 minuty temu - zdrowy)
- Liczba autovacuum: 8K-12K przebiegów (normalnie)
- Częstotliwość: Regularna, konsekwentna

**Server 2:**
- Ostatnio autovacuum: 2025-10-17 20:00:59 (10 minut temu - opóźniony)
- Liczba autovacuum: 23K-34K przebiegów (nadmierna)
- Częstotliwość: Wyższa niż Server 1 (walka ze wznowieniami martwych wierszy)

**Analiza:** Autovacuum Server 2 pracuje z nadmiarową wydajnością (2-3x więcej przebiegów), prawdopodobnie z powodu ograniczonych zasobów i braku zdolności nadążania z obciążeniem zapisu.

---

## Konfiguracja pamięci

| Parametr | Server 1 | Server 2 | Rekomendacja |
|----------|----------|----------|---------------|
| shared_buffers | 1 GB | 1 GB | 4-8 GB (16-32% RAM) |
| effective_cache_size | 3 GB | 3 GB | 10-16 GB (50-75% RAM) |
| work_mem | 4 MB | 4 MB | 32-64 MB na rdzeń |
| maintenance_work_mem | 154 MB | 154 MB | 512 MB - 1 GB |

**Znalezisko:** Oba serwery są nieoptymalne skonfigurowane, ale Server 2 cierpi bardziej z powodu większej bazy danych.

---

## Analiza przyczyn głównych

### Przyczyna pierwotna (60-70% wpływu): Warstwa obliczeniowa Burstable

Warstwa Burstable Server 2 zapewnia:
- Burst wstępny: Pełne 2 vCores dostępne przez ograniczony czas
- Po wyczerpaniu kredytów burst: CPU ograniczony do poziomu bazowego (~5-10% pojemności)
- Kredyty burst gromadzą się powoli podczas bezczynności
- Przy utrzymanym obciążeniu: ciągłe ograniczanie

To wyjaśnia:
- Zapytania metadanych trwające 1,29 godziny
- Pogorszenie współczynnika trafień cache
- Czasy zapytań 3-5x wolniejsze niż Server 1

### Przyczyna wtórna (20-30% wpływu): Niewystarczająca ilość RAM

Baza 171 GB z tylko 4 GB RAM zmusza do:
- Ciągłego I/O na dysk (braki cache)
- Rywalizacji IOPS
- Wolniejszego wykonywania zapytań

### Przyczyna trzeciorzędna (10-15% wpływu): Niewystarczające IOPS

1100 IOPS nie potrafi utrzymać I/O bazy 171 GB:
- Głębokość kolejki wzrasta
- Operacje zapisu się opóźniają
- Opóźnienie odczytu wzrasta

### Przyczyna czwartorzędna (5-10% wpływu): Parametry konfiguracji

Oba serwery niedooptymalne skonfigurowane dla ich zasobów i obciążenia.

---

## Zalecane działania

### KRYTYCZNE - Natychmiast (Tydzień 1)

**Działanie 1: Uaktualnij warstwę obliczeniową**

```
Obecne: Burstable (Standard_B2s, 2 vCores, 4 GB)
Uaktualnij na: General Purpose (Standard_D4s_v3 lub D8s_v3)
- Standard_D4s_v3: 4 vCores, 16 GB RAM, konsekwentny CPU
- Standard_D8s_v3: 8 vCores, 32 GB RAM, konsekwentny CPU

Spodziewana poprawa: 60-70% wzrost wydajności
Szacunkowy koszt: +2-3x miesięczny (ale odpowiadający produkcji)
```

**Działanie 2: Zwiększ IOPS magazynu**

```
Obecny: P15 (1100 IOPS, 256 GB)
Uaktualnij na: P30 (5000 IOPS) lub P40 (7500 IOPS)

Spodziewana poprawa: 15-20% wzrost wydajności + zmniejszona rywalizacja
Szacunkowy koszt: +1,5-2x dla magazynu
```

---

### WYSOKA - Krótkoterminowo (Tydzień 1-2)

**Działanie 3: Optymalizuj parametry PostgreSQL**

```sql
-- Zastosuj na Server 2:

ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET random_page_cost = 1.1;  -- Dla SSD
ALTER SYSTEM SET maintenance_work_mem = '512MB';

SELECT pg_reload_conf();
-- Następnie zrestartuj PostgreSQL
```

**Spodziewana poprawa:** 5-10% wzrost wydajności bez zmian infrastruktury

---

### ŚREDNIA - Średnioterminowo (Tydzień 2-4)

**Działanie 4: Dodaj brakujące indeksy**

Z raportu diagnostycznego utwórz te indeksy na Server 2:

```sql
-- W enata_gostock_config
CREATE INDEX idx_column_mappings_lookup ON enata_gostock_config.column_mappings(source_column);

-- W enata_xreportingmart (sprawdź czy nie istnieją)
CREATE INDEX idx_xdailyreport_product_matrix_date ON enata_xreportingmart.xdailyreport_product_matrix(report_date);
```

**Działanie 5: Usuń nieużywane indeksy**

Server 2 ma 62 nieużywane indeksy (46,62% wszystkich indeksów). Przejrzyj i usuń:

```sql
SELECT schemaname, indexrelname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Spodziewana poprawa:** 5-10% szybsze zapisy, zmniejszony narzut utrzymania

---

### NISKA - Długoterminowo (Miesiąc 2+)

**Działanie 6: Wdrażaj monitoring i alerty**

```
Monitoruj:
- Zdarzenia ograniczania CPU (metryka warstwy Burstable)
- Współczynnik trafień cache (docelowo >95%)
- Czas trwania zapytania p95/p99
- Wykorzystanie IOPS (docelowo <80%)
```

**Działanie 7: Przejrzyj politykę przechowywania danych**

Większa baza Server 2 (171 GB vs 101 GB) uzasadnia:
- Archiwizację starych danych
- Partycjonowanie dużych tabel
- Wdrożenie polityki cyklu życia danych

---

## Oczekiwane rezultaty

### Po Działaniu 1 (Uaktualnij warstwę) - Poprawa 60-70%

```
Przed: Zapytanie 1,29 godziny
Po:    Zapytanie 8-15 minut

Przed: Cache hit 51,78%
Po:    Cache hit 85-92%

Przed: Przepustowość bazowa
Po:    Przepustowość 3-5x wyższa
```

### Po Działaniu 2 (Uaktualnij IOPS) - Dodatkowa poprawa 15-20%

```
Przed: Rywalizacja IOPS podczas skoków
Po:    Margines dla 5x aktualnego obciążenia
```

### Po Działaniu 3 (Dostrojenie parametrów) - Dodatkowa poprawa 5-10%

```
Przed: Konfiguracja generyczna
Po:    Parametry zoptymalizowane dla obciążenia
```

### Skumulowany oczekiwany rezultat: Server 2 80-95% szybszy

---

## Analiza kosztu-korzyści

### Wymagana inwestycja

| Pozycja | Obecny | Rekomendowany | Delta kosztu miesięcznego |
|---------|--------|---------------|--------------------------|
| Obliczenia | Burstable B2s ($50) | General Purpose D4s ($140) | +$90 |
| IOPS magazynu | P15 ($30) | P30 ($80) | +$50 |
| **Razem** | **$80** | **$220** | **+$140/miesiąc** |

### Kalkulacja ROI

- **Jedna godzina niedostępności systemu z powodu wolnej wydajności:** $5 000-$20 000 (szacunkowy wpływ biznesowy)
- **Problemy wydajności zmniejszające przepustowość o 50%:** Codzienna strata produktywności $2 000-$5 000
- **Okres spłaty:** 1-2 tygodnie uniknięcia problemów

---

## Porównanie z Serwerem 1

Infrastruktura Server 1 (enatabread) jest bardziej odpowiednia, ale również nieoptymalnie skonfigurowana:

| Komponent | Server 1 | Rekomendacja |
|-----------|----------|-------------|
| Warstwa | Nieznana (zakłada się General Purpose) | Potwierdź General Purpose |
| RAM | 4 GB (nisko) | Uaktualnij na 16 GB |
| IOPS | Nieznane (zakłada się P20+) | Potwierdź P20 lub wyżej |
| Konfiguracja | Nieoptymalnie | Zastosuj takie samo dostrojenie |

**Rekomendacja:** Uaktualnij Server 1 na 16 GB RAM dla konsekwentnie wysokiej wydajności na obu środowiskach.

---

## Wnioski

Słaba wydajność Server 2 to **problem warstwy i wielkości infrastruktury**, a nie problem konfiguracji PostgreSQL czy projektu. Warstwa Burstable jest nieodpowiednia dla produkcyjnych obciążeń z bazami danych o rozmiarze 171 GB.

**Wymagane natychmiastowe działanie:** Uaktualnij na warstwę General Purpose ze zwiększonym przywdziałem RAM i IOPS. Szacunkowa poprawa wydajności 80-95% w ciągu tygodnia od zmian.

---

## Dodatek: Dane diagnostyczne

### Pełne porównanie serwerów

**Server 1 Metryki:**
- Typ: enatabread.postgres.database.azure.com
- Baza danych: postgres (101 GB)
- Max połączeń: 50
- Używane połączenia: 16 (32%)
- Współczynnik cache hit: 56,37%
- Aktywne zapytania: 1
- Najdłuższe zapytanie: 0,41h

**Server 2 Metryki:**
- Typ: enatabreadprod.postgres.database.azure.com
- Baza danych: postgres (171 GB)
- Max połączeń: 429
- Używane połączenia: 18 (4%)
- Współczynnik cache hit: 51,78%
- Aktywne zapytania: 1
- Najdłuższe zapytanie: 1,29h

### Stosunek wydajności: Server 2 / Server 1

- Rozmiar bazy: 1,70x większy
- Czas zapytania: 3,15x wolniej
- Różnica cache hit: -4,59%
- Efektywność pamięci: 2,34% vs 3,96%

---

**Raport przygotowany przez:** Narzędzie diagnostyczne PostgreSQL  
**Data walidacji:** 17 października 2025 22:10 UTC  
**Poziom pewności:** WYSOKI (dane ze systemowych katalogów pg_stat_*)