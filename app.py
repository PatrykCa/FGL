import streamlit as st
import pandas as pd
import math
import io

st.set_page_config(page_title="System Projektowania", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny")
st.subheader("Kompletna Platforma Wymiarowania Linii, Reologii, Logistyki i Surowców")
st.markdown("---")

st.markdown("""
    <style>
    div[data-testid="stTabs"] {
        position: sticky;
        top: 2.875rem;
        background-color: white;
        z-index: 999;
        padding-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 0. STAŁE GLOBALNE (dawniej "magiczne liczby" rozsiane po kodzie)
# ==========================================
WORKING_DAYS_YEAR = 250          # dni robocze zakładu w roku
MONTHS_PER_YEAR = 12
OIL_FILL_FACTOR = 0.88           # współczynnik napełnienia silosu dla mediów olejowych
WATER_FILL_FACTOR = 1.00         # współczynnik napełnienia silosu dla wody DEMI
TANK_SAFETY_FILL = 0.85          # bufor bezpieczeństwa objętości silosu (85% pojemności nominalnej)
MAX_TANK_UTILIZATION_PCT = 85.0  # próg ostrzegawczy wykorzystania czasowego mieszalnika
MIN_TANK_VOLUME_M3 = 5.0         # minimalna pojemność mieszalnika akceptowana w fabryce
VELOCITY_MIN_MS = 0.5            # dolna granica prędkości przepływu w rurociągu
VELOCITY_MAX_MS = 2.5            # górna granica prędkości przepływu w rurociągu
LMTD_MIN_K = 15.0                # dolna granica "zdrowego" LMTD
LMTD_MAX_K = 60.0                # górna granica "zdrowego" LMTD
STEAM_LATENT_HEAT_KJKG = 2200.0  # ciepło skraplania pary nasyconej (~2 bar) [kJ/kg], wartość orientacyjna
G_ACCEL = 9.81
RAMPUP_YEARS = 5                 # horyzont symulacji rozruchu (Zakładka 2 + Zakładka 4)

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
# (Dawny zestaw FUCHS_PORTFOLIO z liniami marek - np. "Hydraulic Oils (RENOLIN)" - został
# usunięty. Jedyna taksonomia w apce to teraz 7 grup produktowych, patrz GENERIC_PORTFOLIO
# i GROUP_PHYSICAL_DEFAULTS niżej.)

PACK_CONFIGS = {
    "1l (Detal)": {"size_l": 1.0, "per_pallet": 480, "rate_szt_h": 2500},
    "4l (Karton)": {"size_l": 4.0, "per_pallet": 120, "rate_szt_h": 1200},
    "5l (Karton)": {"size_l": 5.0, "per_pallet": 96, "rate_szt_h": 1000},
    "10l (Kanister)": {"size_l": 10.0, "per_pallet": 40, "rate_szt_h": 600},
    "20l (Kanister)": {"size_l": 20.0, "per_pallet": 24, "rate_szt_h": 400},
    "60l (Beczka)": {"size_l": 60.0, "per_pallet": 9, "rate_szt_h": 150},
    "200l (Beczka)": {"size_l": 200.0, "per_pallet": 4, "rate_szt_h": 60},
    "1000l (IBC)": {"size_l": 1000.0, "per_pallet": 1, "rate_szt_h": 15}
}

AGITATOR_TYPES = {
    "Turbinowe (Rushton)": {"laminar_C": 70.0, "turbulent_Ne": 5.0},
    "Łapowe / Płatowe": {"laminar_C": 50.0, "turbulent_Ne": 2.5},
    "Propelerowe (Śmigłowe)": {"laminar_C": 35.0, "turbulent_Ne": 0.8}
}

MEDIA_PROCESOWE = {
    "Woda technologiczna": {"cp": 4.19, "t_max": 95.0, "t_min": 5.0, "steam": False},
    "Olej termiczny": {"cp": 2.00, "t_max": 300.0, "t_min": 40.0, "steam": False},
    "Para nasycona": {"cp": 2.15, "t_max": 180.0, "t_min": 100.0, "steam": True}
}

# Katalog testów laboratoryjnych oznaczonych jako "QC" (zwolnienie szarży) w dostarczonej
# liście testów. Testy oznaczone wyłącznie jako "R&D" (np. korozja, pianotwórczość, EP/AW,
# wielkość cząstek, tribologia, czystość ISO 4406) są pominięte - nie leżą na ścieżce
# krytycznej standardowego zwolnienia partii produkcyjnej.
# Czasy trwania [min] to orientacyjne wartości domyślne oparte na typowej praktyce
# laboratoryjnej - EDYTOWALNE bezpośrednio w Zakładce 7 (VSM), bo rzeczywisty czas zależy
# od obciążenia laboratorium i wprawy technika.
QC_TEST_CATALOG = {
    "Lepkość kinematyczna @40°C": {"duration_min": 20, "equipment": "Łaźnia wiskozymetryczna (Lauda / Koehler / Cannon)"},
    "Lepkość kinematyczna @100°C": {"duration_min": 25, "equipment": "Łaźnia wiskozymetryczna 100°C"},
    "Lepkość dynamiczna": {"duration_min": 10, "equipment": "Wiskozymetr Brookfield"},
    "Barwa ASTM": {"duration_min": 5, "equipment": "Kolorymetr"},
    "Temp. zapłonu - tygiel otwarty": {"duration_min": 45, "equipment": "Cleveland Open Cup"},
    "Temp. zapłonu - tygiel zamknięty": {"duration_min": 30, "equipment": "Koehler Closed Cup"},
    "Gęstość": {"duration_min": 10, "equipment": "Densimetr Koehler K86200"},
    "Zawartość wody (Karl Fischer)": {"duration_min": 15, "equipment": "Metrohm / 795 KFT Titrino"},
    "pH": {"duration_min": 5, "equipment": "pH-metr stołowy"},
    "Przewodność": {"duration_min": 5, "equipment": "Konduktometr"},
    "Demulgowalność": {"duration_min": 60, "equipment": "Koehler Water Separability Tester"},
    "Wskaźnik refrakcji": {"duration_min": 5, "equipment": "Refraktometr cyfrowy Atago"},
    "XRF": {"duration_min": 15, "equipment": "Spektrometr XRF Bruker"},
    "Punkt aniliny": {"duration_min": 20, "equipment": "Aniline Point Tester"},
    "Zawartość ciał stałych": {"duration_min": 30, "equipment": "Wagosuszarka"},
    "Spektroskopia FTIR": {"duration_min": 10, "equipment": "Spektrometr FT-IR Perkin Elmer"},
    "Krzywa chłodzenia (Cooling Curve)": {"duration_min": 20, "equipment": "Smart Quench SQ2"},
    "Zasadowość (Alkalinity)": {"duration_min": 20, "equipment": "Automatyczny tytrator potencjometryczny"},
}


# Lista surowców receptury produktowej (Zakładka 1 / Receptury) - dozowanie w kg na tonę
# produktu gotowego [kg/t], kolejność zgodna z szablonem Excel wgrywanym przez użytkownika.
RECIPE_RAW_MATERIALS = [
    "Base Oil Group I [kg/t]", "Base Oil Group II [kg/t]", "Base Oil Group III [kg/t]",
    "Base Oil Group IV (PAO) [kg/t]", "Base Oil Group V (Estry/PAG) [kg/t]",
    "RRBO (Re-refined) [kg/t]", "Bio-Base Oil (Ester/Vegetable) [kg/t]",
    "Modyfikator Lepkości (VI Improver) [kg/t]", "Depresator (PPD) [kg/t]",
    "Dodatek Smarnościowy / Anti-wear (AW) [kg/t]", "Dodatek Wysokociśnieniowy (EP) [kg/t]",
    "Inhibitor Utleniania (AO) [kg/t]", "Inhibitor Korozji / Pasywator [kg/t]",
    "Detergenty (TBN Boosters) [kg/t]", "Dyspergatory Bezpopiołowe [kg/t]",
    "Dodatek Przeciwpienny (Antifoam) [kg/t]", "Modyfikator Tarcia (FM) [kg/t]",
    "Deemulgatory / Emulgatory [kg/t]", "Modyfikator Uszczelek (Seal Swell) [kg/t]",
    "Pakiet Silnikowy (PCMO/HDDO) [kg/t]", "Pakiet Przekładniowy (Gear) [kg/t]",
    "Pakiet Hydrauliczny (Hydraulic) [kg/t]", "Zagęszczacz Mydłowy (Li/Ca/Complex) [kg/t]",
    "Zagęszczacz Niemydłowy (Polyurea/Bentonit) [kg/t]", "Smar Stały: MoS2 / Grafit [kg/t]",
    "Smar Stały: PTFE / Boron Nitride [kg/t]", "Barwnik / Znacznik / Zapach [kg/t]",
    "Woda Demineralizowana [kg/t]", "Biocyd / Fungicyd [kg/t]",
]

# Grupy produktowe do wyboru (lista rozwijana w szablonie Excel + walidacja przy imporcie).
RECIPE_PRODUCT_GROUPS = ["Cleaners", "Engine Oils", "Glycols", "Greases", "Hydraulic Oils", "Watermiscibles", "Waxes",
                          "Preservative Oils", "Coolants", "Cutting Oils"]

# Domyślne właściwości fizykochemiczne i procesowe per grupa produktowa - używane do
# automatycznego zasilenia floty (Zakładka 2) danymi z wgranej receptury (Zakładka 1),
# tam gdzie receptura sama nie precyzuje danej wartości (np. materiał zbiornika, cp).
# Gęstość NIE jest tu potrzebna - ta zawsze pochodzi z konkretnego wiersza receptury.
GROUP_PHYSICAL_DEFAULTS = {
    "Cleaners": {"material": "Stal nierdzewna", "density": 1.01, "cp": 3.9, "oil_group": "Brak (Specjalistyczne)", "water_content": 0.85, "cycle_h": 4},
    "Engine Oils": {"material": "Stal zwykła", "density": 0.87, "cp": 2.1, "oil_group": "Syntetyczne (Gr. III/IV)", "water_content": 0.0, "cycle_h": 5},
    "Glycols": {"material": "Stal nierdzewna", "density": 1.05, "cp": 2.4, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.3, "cycle_h": 4},
    "Greases": {"material": "Stal zwykła", "density": 0.90, "cp": 2.0, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0, "cycle_h": 6},
    "Hydraulic Oils": {"material": "Stal zwykła", "density": 0.88, "cp": 2.0, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0, "cycle_h": 4},
    "Watermiscibles": {"material": "Stal nierdzewna", "density": 0.99, "cp": 3.8, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.65, "cycle_h": 6},
    "Waxes": {"material": "Stal zwykła", "density": 0.91, "cp": 2.2, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0, "cycle_h": 5},
    "Preservative Oils": {"material": "Stal zwykła", "density": 0.85, "cp": 1.95, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0, "cycle_h": 4},
    "Coolants": {"material": "Stal nierdzewna", "density": 1.02, "cp": 3.9, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.85, "cycle_h": 5},
    "Cutting Oils": {"material": "Stal zwykła", "density": 0.89, "cp": 1.95, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0, "cycle_h": 5},
}

# Zestaw startowy active_portfolio - JEDYNA taksonomia w apce, wspólna dla trybu ręcznego i
# recepturowego: 7 grup produktowych z GROUP_PHYSICAL_DEFAULTS, bez osobnych, zaszytych w
# kodzie linii marek (dawne FUCHS_PORTFOLIO z nazwami typu "Hydraulic Oils (RENOLIN)") - to
# było źródłem dublowania się nazewnictwa, gdy obok wbudowanych linii pojawiały się grupy
# z wgranej receptury o niemal identycznej nazwie.
GENERIC_PORTFOLIO = {
    name: {"material": d["material"], "density": d["density"], "cycle_h": d["cycle_h"],
           "cp": d["cp"], "oil_group": d["oil_group"], "water_content": d["water_content"]}
    for name, d in GROUP_PHYSICAL_DEFAULTS.items()
}

# Arkusz opakowań (opcjonalny, w tym samym pliku co receptury) - pozwala predefiniować
# typy opakowań i ich pojemności w Excelu; po wgraniu nadpisują/uzupełniają wbudowane
# domyślne wartości (PACK_CONFIGS), a dalej pozostają w pełni edytowalne w samej aplikacji.
PACKAGING_SHEET_NAME = "Opakowania"
PACKAGING_NAME_COL = "Nazwa Opakowania"
PACKAGING_SIZE_COL = "Pojemność [L]"
PACKAGING_PER_PALLET_COL = "Sztuk na Palecie"
PACKAGING_RATE_COL = "Wydajność 1 głowicy [kg/min]"
PACKAGING_NOZZLES_COL = "Liczba głowic (domyślna)"

RECIPE_GROUP_COL = "Grupa Produktowa"
RECIPE_PRODUCT_COL = "Produkt"
RECIPE_ANNUAL_COL = "Roczne Zapotrzebowanie Produktu [tony]"
RECIPE_SUM_COL = "Suma Udziałów Składników [kg]"
RECIPE_DENSITY_COL = "Gęstość 15°C [g/cm³]"
RECIPE_LOSS_COL = "Szacowane Straty Procesowe [%]"
RECIPE_RAW_DEMAND_COL = "Roczne Zapotrzebowanie Surowcowe [tony]"
RECIPE_NOTES_COL = "Uwagi Technologiczne / Status QA"

# Sposób pozyskania produktu: na starcie część produktów bywa IMPOROWANA (z innego zakładu/od
# dostawcy) zamiast produkowana lokalnie, a dopiero po jakimś czasie zaczyna się produkcja
# własna. Przejście modelowane jest jako NAGŁE, w jednym pełnym roku symulacji rozruchu
# (Zakładka 2/4) - przed rokiem przejścia produkt w 100% importowany, od tego roku w 100%
# produkowany lokalnie. "Nigdy" = produkt na stałe pozostaje importowany (nigdy nie trafia do
# floty mieszalników - typowy przypadek dla niszowego SKU, którego produkcja lokalna się nie
# opłaca nawet w dojrzałości).
RECIPE_SOURCING_COL = "Sposób Pozyskania"
RECIPE_SOURCING_OPTIONS = ["Produkcja własna", "Import"]
RECIPE_IMPORT_TRANSITION_COL = "Rok Przejścia na Produkcję Własną"
RECIPE_IMPORT_TRANSITION_OPTIONS = ["Rok 1", "Rok 2", "Rok 3", "Rok 4", "Rok 5", "Nigdy (stały import)"]
RECIPE_IMPORT_FREQ_COL = "Częstotliwość Dostawy Importowej [dni]"
RECIPE_IMPORT_LOT_COL = "Wielkość 1 Dostawy Importowej [tony]"
RECIPE_IMPORT_SAFETY_DAYS_COL = "Bufor Bezpieczeństwa Importu [dni]"

# Opcjonalna kolumna: kilka produktów może współdzielić JEDEN fizyczny mieszalnik (produkcja
# kampanijna) zamiast dostawać każdy swój dedykowany zbiornik. Puste = własny zbiornik (jak
# dotychczas); te samo ID w kilku wierszach TEJ SAMEJ grupy produktowej = wspólny zbiornik.
RECIPE_TANK_ID_COL = "ID Zbiornika (opcjonalnie - te samo ID = wspólny mieszalnik)"
RECIPE_SHARED_UTIL_COL = "Suma Wykorzystania Zbiornika Współdzielonego [%]"

# Wymiarowanie mieszalnika i szacowane wykorzystanie zdolności produkcyjnej - wpisywane
# bezpośrednio w Excelu, żeby dać natychmiastową (choć uproszczoną) informację zwrotną, zanim
# w ogóle dojdzie do konfiguracji floty w Zakładce 1/2 (tam wykorzystanie liczone jest w pełni,
# z rzeczywistą hydrauliką/bilansem cieplnym - to tutaj to szybki szacunek wstępny).
RECIPE_MIXER_VOL_COL = "Pojemność Mieszalnika [m³]"
RECIPE_CYCLE_COL = "Szacowany Cykl Szarży [h]"
RECIPE_AVAIL_HOURS_COL = "Dostępne Godziny Pracy / Rok [h]"
RECIPE_BATCH_MASS_COL = "Masa Szarży [kg]"
RECIPE_BATCHES_YEAR_COL = "Szarż / Rok"
RECIPE_UTILIZATION_COL = "Wykorzystanie Mieszalnika [%]"
RECIPE_UTILIZATION_WARN_PCT = 85.0  # spójne z MAX_TANK_UTILIZATION_PCT w Zakładce 1

# Rozbicie procentowe na typy opakowań - kolumny generowane dynamicznie z aktualnej listy
# opakowań (domyślne PACK_CONFIGS lub to, co użytkownik ma w arkuszu 'Opakowania').
RECIPE_PACK_SUM_COL = "Suma % Opakowań (kontrola)"

# Docelowa suma dozowania składników na tonę produktu - 1000 kg/t (1 tona), z tolerancją na
# zaokrąglenia ręcznego wpisywania receptur.
RECIPE_TARGET_SUM_KG = 1000.0
RECIPE_SUM_TOLERANCE_KG = 50.0


def recipe_pack_pct_col(pack_name):
    """Nazwa kolumny procentowego udziału danego opakowania w arkuszu receptur."""
    return f"Opak: {pack_name} [%]"


RAMPUP_YEAR_TARGET_SENTINEL = 9999  # "Docelowa (100%)" = pełna dojrzałość, po wszystkich przejściach z importu


def is_product_imported_in_year(sourcing, transition_label, year_idx):
    """
    Czy dany produkt jest w danym roku symulacji (year_idx, 0-based; RAMPUP_YEAR_TARGET_SENTINEL
    = widok docelowy/100%) nadal importowany, czy już produkowany lokalnie. Przejście jest
    NAGŁE (patrz komentarz przy RECIPE_SOURCING_COL) - przed rokiem przejścia 100% import, od
    tego roku 100% produkcja własna. "Nigdy" = zawsze import, nawet w widoku docelowym.
    """
    if sourcing != "Import":
        return False
    if transition_label == "Nigdy (stały import)" or not transition_label:
        return True
    if year_idx == RAMPUP_YEAR_TARGET_SENTINEL:
        return False  # widok docelowy = pełna dojrzałość = po przejściu (chyba że "Nigdy", obsłużone wyżej)
    try:
        transition_year = int(transition_label.split(" ")[1])
    except (IndexError, ValueError):
        transition_year = 1
    return (year_idx + 1) < transition_year

# Informacja, czy dany surowiec nadaje się fizycznie/praktycznie do magazynowania
# w zbiorniku (płyn luzem) czy zawsze zostaje w beczkach/IBC/workach - niezależnie od
# wolumenu (ciała stałe, bardzo niskie dozowania, ograniczona trwałość po otwarciu itp.).
# To jest orientacyjna reguła inżynierska do podpowiedzi w aplikacji, nie sztywna norma -
# użytkownik może ją zignorować dla konkretnego przypadku.
RAW_MATERIAL_STORAGE_INFO = {
    "Base Oil Group I [kg/t]": {"bulk_eligible": True, "note": "Baza mineralna - standardowo magazynowana luzem w zbiornikach."},
    "Base Oil Group II [kg/t]": {"bulk_eligible": True, "note": "Baza mineralna - standardowo magazynowana luzem w zbiornikach."},
    "Base Oil Group III [kg/t]": {"bulk_eligible": True, "note": "Baza syntetyczna - standardowo magazynowana luzem w zbiornikach."},
    "Base Oil Group IV (PAO) [kg/t]": {"bulk_eligible": True, "note": "PAO - magazynowanie luzem możliwe, zwykle droższe medium więc warto pilnować rotacji."},
    "Base Oil Group V (Estry/PAG) [kg/t]": {"bulk_eligible": True, "note": "Estry/PAG - higroskopijne, magazynowanie luzem OK, ale zbiornik wymaga osuszania/inertyzacji i krótszej rotacji."},
    "RRBO (Re-refined) [kg/t]": {"bulk_eligible": True, "note": "Baza re-refinowana - magazynowanie luzem jak dla baz mineralnych."},
    "Bio-Base Oil (Ester/Vegetable) [kg/t]": {"bulk_eligible": True, "note": "Podatna na utlenianie - luzem możliwe, ale przy niższej rotacji zalecana krótsza autonomia zapasu."},
    "Modyfikator Lepkości (VI Improver) [kg/t]": {"bulk_eligible": True, "note": "Przy dużym wolumenie opłacalny zbiornik dedykowany; przy małym - beczki/IBC."},
    "Depresator (PPD) [kg/t]": {"bulk_eligible": True, "note": "Zwykle niskie dozowanie - zbiornik opłacalny dopiero przy dużym wolumenie."},
    "Dodatek Smarnościowy / Anti-wear (AW) [kg/t]": {"bulk_eligible": True, "note": "Zbiornik opłacalny przy dużym wolumenie."},
    "Dodatek Wysokociśnieniowy (EP) [kg/t]": {"bulk_eligible": True, "note": "Zbiornik opłacalny przy dużym wolumenie (typowo oleje przekładniowe)."},
    "Inhibitor Utleniania (AO) [kg/t]": {"bulk_eligible": True, "note": "Zbiornik opłacalny przy dużym wolumenie."},
    "Inhibitor Korozji / Pasywator [kg/t]": {"bulk_eligible": True, "note": "Zbiornik opłacalny przy dużym wolumenie."},
    "Detergenty (TBN Boosters) [kg/t]": {"bulk_eligible": True, "note": "Przy wysokowolumenowych olejach silnikowych zbiornik dedykowany jest standardem branżowym."},
    "Dyspergatory Bezpopiołowe [kg/t]": {"bulk_eligible": True, "note": "Zbiornik opłacalny przy dużym wolumenie."},
    "Dodatek Przeciwpienny (Antifoam) [kg/t]": {"bulk_eligible": False, "note": "Bardzo niskie dozowanie (dziesiąte części %) - zawsze beczki/małe pojemniki, precyzja dozowania ważniejsza niż koszt logistyki."},
    "Modyfikator Tarcia (FM) [kg/t]": {"bulk_eligible": True, "note": "Zbiornik opłacalny dopiero przy dużym wolumenie, zwykle beczki/IBC."},
    "Deemulgatory / Emulgatory [kg/t]": {"bulk_eligible": True, "note": "Zbiornik opłacalny przy dużym wolumenie."},
    "Modyfikator Uszczelek (Seal Swell) [kg/t]": {"bulk_eligible": False, "note": "Niskie dozowanie i wysoka cena jednostkowa - zwykle beczki/IBC nawet przy większych wolumenach."},
    "Pakiet Silnikowy (PCMO/HDDO) [kg/t]": {"bulk_eligible": True, "note": "Gotowy pakiet dodatków - przy wysokim wolumenie standardowo dedykowany zbiornik (dostawy cysternami)."},
    "Pakiet Przekładniowy (Gear) [kg/t]": {"bulk_eligible": True, "note": "Gotowy pakiet dodatków - zbiornik opłacalny przy dużym wolumenie."},
    "Pakiet Hydrauliczny (Hydraulic) [kg/t]": {"bulk_eligible": True, "note": "Gotowy pakiet dodatków - zbiornik opłacalny przy dużym wolumenie."},
    "Zagęszczacz Mydłowy (Li/Ca/Complex) [kg/t]": {"bulk_eligible": False, "note": "Pasta/proszek do produkcji smarów - magazynowany w beczkach/workach, nie w zbiorniku cieczy."},
    "Zagęszczacz Niemydłowy (Polyurea/Bentonit) [kg/t]": {"bulk_eligible": False, "note": "Ciało stałe/proszek - beczki/worki, nie zbiornik cieczy."},
    "Smar Stały: MoS2 / Grafit [kg/t]": {"bulk_eligible": False, "note": "Proszek stały - zawsze worki/beczki, nie nadaje się do zbiornika."},
    "Smar Stały: PTFE / Boron Nitride [kg/t]": {"bulk_eligible": False, "note": "Proszek stały - zawsze worki/beczki, nie nadaje się do zbiornika."},
    "Barwnik / Znacznik / Zapach [kg/t]": {"bulk_eligible": False, "note": "Śladowe dozowanie - zawsze małe pojemniki/beczki, zbiornik nieopłacalny przy żadnym wolumenie."},
    "Woda Demineralizowana [kg/t]": {"bulk_eligible": True, "note": "Zawsze warto trzymać w zbiorniku/cysternie - tani, wysokowolumenowy nośnik."},
    "Biocyd / Fungicyd [kg/t]": {"bulk_eligible": False, "note": "Ograniczona trwałość i niskie dozowanie - zalecane beczki/IBC z szybką rotacją, nie długie magazynowanie luzem."},
}

# Typy pojemników dla surowców NIE magazynowanych luzem (beczki/IBC/worki) - do przeliczenia
# rocznego zużycia [t/rok] na liczbę pojemników/palet/miejsc magazynowych w Zakładce 5, żeby
# te surowce trafiły do tego samego bilansu powierzchni magazynowej co wyroby gotowe (Zakładka
# 4) - w końcu wszystko, co nie trafia do zbiornika, musi stanąć w magazynie. Pojemność podana
# w kg (nie L), bo dla surowców pracujemy na masie, nie na objętości/gęstości.
RM_CONTAINER_TYPES = {
    "Beczka 200 kg (ciecz)": {"capacity_kg": 200.0, "per_pallet": 4},
    "IBC 1000 kg (ciecz)": {"capacity_kg": 1000.0, "per_pallet": 1},
    "Worek 25 kg (ciało stałe, na palecie)": {"capacity_kg": 25.0, "per_pallet": 40},
    "Big Bag 500 kg (ciało stałe)": {"capacity_kg": 500.0, "per_pallet": 1},
}


def default_rm_container_for(material_name, info):
    """Sensowna domyślna propozycja pojemnika na podstawie opisu surowca w RAW_MATERIAL_STORAGE_INFO."""
    note_lower = (info.get("note", "") + " " + material_name).lower()
    if "worki" in note_lower or "proszek" in note_lower or "pasta" in note_lower:
        return "Worek 25 kg (ciało stałe, na palecie)"
    return "Beczka 200 kg (ciecz)"


def generate_recipe_template_bytes():
    """
    Buduje w pamięci szablon Excel (openpyxl) do uzupełnienia przez użytkownika: grupa
    produktowa, nazwa produktu, roczne zapotrzebowanie na produkt [tony], wstępny dobór
    mieszalnika (pojemność/cykl/dostępne godziny -> wyliczone wykorzystanie zdolności
    produkcyjnej w %), dozowanie surowców [kg/t] (29 pozycji), gęstość, szacowane straty
    procesowe, wyliczone roczne zapotrzebowanie surowcowe, rozbicie procentowe na typy
    opakowań, oraz pole na uwagi technologiczne/status QA.
    Kolumny wyliczane (Masa Szarży, Szarż/Rok, Wykorzystanie Mieszalnika, Suma Udziałów
    Składników, Roczne Zapotrzebowanie Surowcowe, Suma % Opakowań) są formułami Excela (nie
    sztywnymi wartościami z Pythona), żeby przeliczały się po edycji w arkuszu.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.formatting.rule import CellIsRule, FormulaRule
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Receptury"

    header_font = Font(bold=True, name="Arial", size=10, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E78")
    input_fill = PatternFill("solid", fgColor="DDEBF7")
    computed_fill = PatternFill("solid", fgColor="F2F2F2")
    example_font = Font(name="Arial", size=10, italic=True, color="0000FF")
    normal_font = Font(name="Arial", size=10)
    wrap_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    try:
        current_pack_defaults = st.session_state.get("pack_configs", PACK_CONFIGS)
    except Exception:
        current_pack_defaults = PACK_CONFIGS
    pack_names = list(current_pack_defaults.keys())
    pack_pct_cols = [recipe_pack_pct_col(n) for n in pack_names]

    headers = ([RECIPE_GROUP_COL, RECIPE_PRODUCT_COL, RECIPE_ANNUAL_COL,
                RECIPE_SOURCING_COL, RECIPE_IMPORT_TRANSITION_COL, RECIPE_IMPORT_FREQ_COL,
                RECIPE_IMPORT_LOT_COL, RECIPE_IMPORT_SAFETY_DAYS_COL,
                RECIPE_MIXER_VOL_COL, RECIPE_CYCLE_COL, RECIPE_AVAIL_HOURS_COL,
                RECIPE_BATCH_MASS_COL, RECIPE_BATCHES_YEAR_COL, RECIPE_UTILIZATION_COL] +
               RECIPE_RAW_MATERIALS +
               [RECIPE_SUM_COL, RECIPE_DENSITY_COL, RECIPE_LOSS_COL, RECIPE_RAW_DEMAND_COL] +
               pack_pct_cols + [RECIPE_PACK_SUM_COL, RECIPE_TANK_ID_COL, RECIPE_SHARED_UTIL_COL, RECIPE_NOTES_COL])

    n_fixed_left = 3                      # Grupa, Produkt, Roczne Zapotrzebowanie Produktu
    sourcing_col = n_fixed_left + 1
    transition_col = sourcing_col + 1
    import_freq_col = transition_col + 1
    import_lot_col = import_freq_col + 1
    import_safety_col = import_lot_col + 1
    mixer_vol_col = import_safety_col + 1
    cycle_col = mixer_vol_col + 1
    avail_hours_col = cycle_col + 1
    batch_mass_col = avail_hours_col + 1
    batches_year_col = batch_mass_col + 1
    utilization_col = batches_year_col + 1
    n_materials = len(RECIPE_RAW_MATERIALS)
    first_mat_col = utilization_col + 1
    last_mat_col = first_mat_col + n_materials - 1
    sum_col = last_mat_col + 1
    density_col = sum_col + 1
    loss_col = density_col + 1
    raw_demand_col = loss_col + 1
    first_pack_col = raw_demand_col + 1
    last_pack_col = first_pack_col + len(pack_names) - 1
    pack_sum_col = last_pack_col + 1
    tank_id_col = pack_sum_col + 1
    shared_util_col = tank_id_col + 1
    notes_col = shared_util_col + 1

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = wrap_center
    ws.freeze_panes = get_column_letter(n_fixed_left + 1) + "2"
    ws.row_dimensions[1].height = 50

    ws_info = wb.create_sheet("Instrukcja")
    info_lines = [
        "INSTRUKCJA WYPEŁNIANIA:",
        "1. Nie zmieniaj nazw ani kolejności kolumn w arkuszu 'Receptury'.",
        f"2. '{RECIPE_GROUP_COL}' - wybierz z listy rozwijanej: {', '.join(RECIPE_PRODUCT_GROUPS)}.",
        f"3. '{RECIPE_ANNUAL_COL}' - roczny wolumen produkcji GOTOWEGO produktu (bez strat procesowych).",
        f"4. '{RECIPE_MIXER_VOL_COL}', '{RECIPE_CYCLE_COL}', '{RECIPE_AVAIL_HOURS_COL}' - wstępny dobór mieszalnika; "
        f"'{RECIPE_UTILIZATION_COL}' liczy się sama (formuła) i podświetla na czerwono powyżej {RECIPE_UTILIZATION_WARN_PCT:.0f}% "
        "(przeciążenie) - to szybki szacunek, w Zakładce 2/3 aplikacji policzysz to dokładnie z rzeczywistą hydrauliką.",
        "5. Kolumny surowcowe [kg/t] - ile kg danego surowca zużywa się na 1 tonę GOTOWEGO produktu.",
        f"6. '{RECIPE_SUM_COL}' liczy się sama (formuła) - powinna wynosić ok. 1000 kg (tolerancja +/-{RECIPE_SUM_TOLERANCE_KG:.0f} kg).",
        f"7. '{RECIPE_DENSITY_COL}' i '{RECIPE_LOSS_COL}' wpisz ręcznie dla każdego produktu.",
        f"8. '{RECIPE_RAW_DEMAND_COL}' liczy się sama (formuła) = zapotrzebowanie produktu / (1 - straty%)"
        " - to ILE SUROWCA trzeba faktycznie zakupić, uwzględniając straty procesowe.",
        f"9. Kolumny 'Opak: ... [%]' - opcjonalne, jeśli chcesz z góry rozbić produkt na opakowania; "
        f"'{RECIPE_PACK_SUM_COL}' liczy się sama i powinna wynosić 100%, jeśli używasz tego rozbicia (możesz zostawić 0, jeśli nie dotyczy).",
        "10. Puste komórki w kolumnach surowcowych/opakowaniowych są traktowane jako 0.",
        "11. Dodaj tyle wierszy produktów, ile potrzebujesz - przeciągnij formuły w dół.",
        "12. Przykładowe wiersze (niebieska kursywa) pokazują format - usuń je lub nadpisz własnymi danymi.",
        f"13. '{RECIPE_TANK_ID_COL}' - zostaw puste, jeśli każdy produkt ma mieć własny, dedykowany mieszalnik "
        "(domyślne zachowanie). Jeśli KILKA produktów TEJ SAMEJ grupy produktowej ma współdzielić JEDEN fizyczny "
        "mieszalnik (produkcja kampanijna - różne produkty na przemian na tym samym reaktorze), wpisz im "
        "IDENTYCZNY identyfikator, np. 'R-01'. Aplikacja policzy wtedy jeden zbiornik z łącznym wykorzystaniem "
        "czasowym (suma szarż x cykl każdego produktu), dobierając pojemność pod największą recepturę spośród nich. "
        "Ustaw też tę SAMĄ pojemność mieszalnika dla wszystkich wierszy ze wspólnym ID - to fizycznie jeden zbiornik.",
        f"14. '{RECIPE_SHARED_UTIL_COL}' liczy się sama (formuła) - dla wierszy ze wspólnym ID Zbiornika sumuje ich "
        "indywidualne wykorzystania (orientacyjnie, każde liczone tak, jakby miało cały zbiornik dla siebie), "
        f"żeby wykryć przeciążenie WSPÓLNEGO zbiornika już tutaj, przed wgraniem do aplikacji - podświetla się na "
        f"czerwono powyżej {RECIPE_UTILIZATION_WARN_PCT:.0f}%.",
        f"15. '{RECIPE_SOURCING_COL}' - 'Produkcja własna' (domyślne) albo 'Import'. Produkty importowane NIE trafiają "
        f"do floty mieszalników, dopóki nie nadejdzie ich '{RECIPE_IMPORT_TRANSITION_COL}' (Rok 1-5, zgodnie z 5-letnią "
        "symulacją rozruchu w Zakładce 2) - przejście jest NAGŁE, w jednym pełnym roku. Wybierz 'Nigdy (stały import)', "
        "jeśli produkt ma zawsze pozostać importowany (nigdy nie dostanie własnego mieszalnika, nawet w widoku "
        f"docelowym). '{RECIPE_IMPORT_FREQ_COL}', '{RECIPE_IMPORT_LOT_COL}' i '{RECIPE_IMPORT_SAFETY_DAYS_COL}' "
        "opisują rytm dostaw - używane w Zakładce 4 do wyliczenia miejsc magazynowych na produkt importowany "
        "(analogicznie do bufora surowców w Zakładce 5, ale liczone z rytmu dostaw, nie z cyklu produkcji).",
    ]
    for i, line in enumerate(info_lines, start=1):
        c = ws_info.cell(row=i, column=1, value=line)
        c.font = Font(bold=(i == 1), name="Arial", size=11)
    ws_info.column_dimensions["A"].width = 110

    example_rows = [
        {
            RECIPE_GROUP_COL: "Hydraulic Oils", RECIPE_PRODUCT_COL: "Przykład: Hydraulic Oil 46",
            RECIPE_ANNUAL_COL: 500, RECIPE_MIXER_VOL_COL: 15, RECIPE_CYCLE_COL: 4, RECIPE_AVAIL_HOURS_COL: 2000,
            RECIPE_DENSITY_COL: 0.876, RECIPE_LOSS_COL: 1.5,
            RECIPE_SOURCING_COL: "Import", RECIPE_IMPORT_TRANSITION_COL: "Rok 3",
            RECIPE_IMPORT_FREQ_COL: 21, RECIPE_IMPORT_LOT_COL: 20, RECIPE_IMPORT_SAFETY_DAYS_COL: 10,
            RECIPE_NOTES_COL: "Receptura referencyjna - status QA: zatwierdzona. Importowana do Roku 3, od Roku 3 produkcja własna.",
            "Base Oil Group II [kg/t]": 965, "Depresator (PPD) [kg/t]": 5,
            "Inhibitor Utleniania (AO) [kg/t]": 8, "Inhibitor Korozji / Pasywator [kg/t]": 3,
            "Dodatek Przeciwpienny (Antifoam) [kg/t]": 1, "Deemulgatory / Emulgatory [kg/t]": 18,
            recipe_pack_pct_col("5l (Karton)"): 30, recipe_pack_pct_col("200l (Beczka)"): 40,
            recipe_pack_pct_col("1000l (IBC)"): 30,
        },
        {
            RECIPE_GROUP_COL: "Engine Oils", RECIPE_PRODUCT_COL: "Przykład: Engine Oil 5W-30",
            RECIPE_ANNUAL_COL: 800, RECIPE_MIXER_VOL_COL: 20, RECIPE_CYCLE_COL: 5, RECIPE_AVAIL_HOURS_COL: 2000,
            RECIPE_DENSITY_COL: 0.855, RECIPE_LOSS_COL: 2.0, RECIPE_TANK_ID_COL: "R-01",
            RECIPE_NOTES_COL: "Receptura referencyjna - status QA: w walidacji. Współdzieli mieszalnik R-01 z Engine Oil 10W-40 poniżej.",
            "Base Oil Group III [kg/t]": 820, "Modyfikator Lepkości (VI Improver) [kg/t]": 80,
            "Depresator (PPD) [kg/t]": 3, "Dodatek Smarnościowy / Anti-wear (AW) [kg/t]": 10,
            "Inhibitor Utleniania (AO) [kg/t]": 12, "Inhibitor Korozji / Pasywator [kg/t]": 5,
            "Pakiet Silnikowy (PCMO/HDDO) [kg/t]": 68, "Dodatek Przeciwpienny (Antifoam) [kg/t]": 1,
            "Modyfikator Tarcia (FM) [kg/t]": 1,
            recipe_pack_pct_col("5l (Karton)"): 60, recipe_pack_pct_col("1000l (IBC)"): 40,
        },
        {
            RECIPE_GROUP_COL: "Engine Oils", RECIPE_PRODUCT_COL: "Przykład: Engine Oil 10W-40 (współdzielony mieszalnik)",
            RECIPE_ANNUAL_COL: 150, RECIPE_MIXER_VOL_COL: 20, RECIPE_CYCLE_COL: 5, RECIPE_AVAIL_HOURS_COL: 2000,
            RECIPE_DENSITY_COL: 0.86, RECIPE_LOSS_COL: 2.0, RECIPE_TANK_ID_COL: "R-01",
            RECIPE_NOTES_COL: "Współdzieli mieszalnik R-01 z Engine Oil 5W-30 powyżej (produkcja kampanijna - "
                               "ten sam reaktor, na przemian).",
            "Base Oil Group III [kg/t]": 850, "Modyfikator Lepkości (VI Improver) [kg/t]": 60,
            "Depresator (PPD) [kg/t]": 3, "Dodatek Smarnościowy / Anti-wear (AW) [kg/t]": 10,
            "Inhibitor Utleniania (AO) [kg/t]": 12, "Inhibitor Korozji / Pasywator [kg/t]": 5,
            "Pakiet Silnikowy (PCMO/HDDO) [kg/t]": 58, "Dodatek Przeciwpienny (Antifoam) [kg/t]": 1,
            "Modyfikator Tarcia (FM) [kg/t]": 1,
            recipe_pack_pct_col("5l (Karton)"): 60, recipe_pack_pct_col("1000l (IBC)"): 40,
        },
    ]

    start_data_row = 2
    n_blank_rows = 20
    total_rows = len(example_rows) + n_blank_rows
    annual_col_letter = get_column_letter(n_fixed_left)
    mixer_vol_letter = get_column_letter(mixer_vol_col)
    cycle_letter = get_column_letter(cycle_col)
    avail_hours_letter = get_column_letter(avail_hours_col)
    batch_mass_letter = get_column_letter(batch_mass_col)
    batches_year_letter = get_column_letter(batches_year_col)
    utilization_letter = get_column_letter(utilization_col)
    first_mat_letter = get_column_letter(first_mat_col)
    last_mat_letter = get_column_letter(last_mat_col)
    sum_col_letter = get_column_letter(sum_col)
    density_col_letter = get_column_letter(density_col)
    loss_col_letter = get_column_letter(loss_col)
    raw_demand_col_letter = get_column_letter(raw_demand_col)
    first_pack_letter = get_column_letter(first_pack_col) if pack_names else None
    last_pack_letter = get_column_letter(last_pack_col) if pack_names else None
    pack_sum_col_letter = get_column_letter(pack_sum_col)
    tank_id_col_letter = get_column_letter(tank_id_col)
    shared_util_col_letter = get_column_letter(shared_util_col)

    group_dv = DataValidation(type="list", formula1='"' + ",".join(RECIPE_PRODUCT_GROUPS) + '"', allow_blank=True)
    ws.add_data_validation(group_dv)
    sourcing_dv = DataValidation(type="list", formula1='"' + ",".join(RECIPE_SOURCING_OPTIONS) + '"', allow_blank=True)
    ws.add_data_validation(sourcing_dv)
    transition_dv = DataValidation(type="list", formula1='"' + ",".join(RECIPE_IMPORT_TRANSITION_OPTIONS) + '"', allow_blank=True)
    ws.add_data_validation(transition_dv)

    for r_offset in range(total_rows):
        row = start_data_row + r_offset
        is_example = r_offset < len(example_rows)
        font_to_use = example_font if is_example else normal_font

        if is_example:
            data = example_rows[r_offset]
            ws.cell(row=row, column=1, value=data.get(RECIPE_GROUP_COL, "")).font = font_to_use
            ws.cell(row=row, column=2, value=data.get(RECIPE_PRODUCT_COL, "")).font = font_to_use
            ws.cell(row=row, column=3, value=data.get(RECIPE_ANNUAL_COL, "")).font = font_to_use
            ws.cell(row=row, column=sourcing_col, value=data.get(RECIPE_SOURCING_COL, "Produkcja własna")).font = font_to_use
            ws.cell(row=row, column=transition_col, value=data.get(RECIPE_IMPORT_TRANSITION_COL, "")).font = font_to_use
            ws.cell(row=row, column=import_freq_col, value=data.get(RECIPE_IMPORT_FREQ_COL, "")).font = font_to_use
            ws.cell(row=row, column=import_lot_col, value=data.get(RECIPE_IMPORT_LOT_COL, "")).font = font_to_use
            ws.cell(row=row, column=import_safety_col, value=data.get(RECIPE_IMPORT_SAFETY_DAYS_COL, "")).font = font_to_use
            ws.cell(row=row, column=mixer_vol_col, value=data.get(RECIPE_MIXER_VOL_COL, "")).font = font_to_use
            ws.cell(row=row, column=cycle_col, value=data.get(RECIPE_CYCLE_COL, "")).font = font_to_use
            ws.cell(row=row, column=avail_hours_col, value=data.get(RECIPE_AVAIL_HOURS_COL, "")).font = font_to_use
            for m_idx, mat in enumerate(RECIPE_RAW_MATERIALS, start=first_mat_col):
                ws.cell(row=row, column=m_idx, value=data.get(mat, 0)).font = font_to_use
            ws.cell(row=row, column=density_col, value=data.get(RECIPE_DENSITY_COL, "")).font = font_to_use
            ws.cell(row=row, column=loss_col, value=data.get(RECIPE_LOSS_COL, "")).font = font_to_use
            for p_idx, pname in enumerate(pack_names, start=first_pack_col):
                ws.cell(row=row, column=p_idx, value=data.get(recipe_pack_pct_col(pname), 0)).font = font_to_use
            ws.cell(row=row, column=tank_id_col, value=data.get(RECIPE_TANK_ID_COL, "")).font = font_to_use
            ws.cell(row=row, column=notes_col, value=data.get(RECIPE_NOTES_COL, "")).font = font_to_use
        else:
            prod_num = r_offset - len(example_rows) + 1
            ws.cell(row=row, column=1).font = normal_font
            ws.cell(row=row, column=1).fill = input_fill
            ws.cell(row=row, column=2, value=f"Product {prod_num}").font = normal_font
            ws.cell(row=row, column=2).fill = input_fill
            for col_idx in [3, mixer_vol_col, cycle_col, avail_hours_col]:
                ws.cell(row=row, column=col_idx).font = normal_font
                ws.cell(row=row, column=col_idx).fill = input_fill
            ws.cell(row=row, column=sourcing_col, value="Produkcja własna").font = normal_font
            ws.cell(row=row, column=sourcing_col).fill = input_fill
            for col_idx in [transition_col, import_freq_col, import_lot_col, import_safety_col]:
                ws.cell(row=row, column=col_idx).font = normal_font
                ws.cell(row=row, column=col_idx).fill = input_fill
            for col_idx in range(first_mat_col, last_mat_col + 1):
                cell = ws.cell(row=row, column=col_idx)
                cell.font = normal_font
                cell.fill = input_fill
            ws.cell(row=row, column=density_col).fill = input_fill
            ws.cell(row=row, column=loss_col).fill = input_fill
            for col_idx in range(first_pack_col, last_pack_col + 1) if pack_names else []:
                cell = ws.cell(row=row, column=col_idx)
                cell.font = normal_font
                cell.fill = input_fill
            ws.cell(row=row, column=tank_id_col).fill = input_fill
            ws.cell(row=row, column=notes_col).fill = input_fill
            group_dv.add(f"A{row}")
            sourcing_dv.add(ws.cell(row=row, column=sourcing_col).coordinate)
            transition_dv.add(ws.cell(row=row, column=transition_col).coordinate)

        # Masa Szarży [kg] = pojemność [m3] * 1000 (L/m3) * gęstość [kg/L, liczbowo = g/cm3]
        batch_mass_formula = f"=IF(OR({mixer_vol_letter}{row}<=0,{density_col_letter}{row}<=0),0,{mixer_vol_letter}{row}*1000*{density_col_letter}{row})"
        bm_cell = ws.cell(row=row, column=batch_mass_col, value=batch_mass_formula)
        bm_cell.font = font_to_use
        bm_cell.number_format = '#,##0" kg"'
        bm_cell.fill = computed_fill

        # Szarż / Rok = (roczne zapotrzebowanie [t] * 1000) / masa szarży [kg]
        batches_year_formula = f"=IF({batch_mass_letter}{row}<=0,0,{annual_col_letter}{row}*1000/{batch_mass_letter}{row})"
        by_cell = ws.cell(row=row, column=batches_year_col, value=batches_year_formula)
        by_cell.font = font_to_use
        by_cell.number_format = '0.0'
        by_cell.fill = computed_fill

        # Wykorzystanie Mieszalnika [%] = Szarż/Rok * Cykl [h] / Dostępne godziny/rok * 100
        util_formula = f"=IF({avail_hours_letter}{row}<=0,0,{batches_year_letter}{row}*{cycle_letter}{row}/{avail_hours_letter}{row}*100)"
        util_cell = ws.cell(row=row, column=utilization_col, value=util_formula)
        util_cell.font = font_to_use
        util_cell.number_format = '0.0"%"'
        util_cell.fill = computed_fill

        # Suma wykorzystania dla wspólnego ID Zbiornika - jeśli kilka produktów współdzieli
        # jeden fizyczny mieszalnik, ich pojedyncze % wykorzystania (każdy liczony tak, jakby
        # miał zbiornik tylko dla siebie) trzeba zsumować, żeby zobaczyć REALNE łączne
        # obciążenie. Dla pustego ID (własny zbiornik) to po prostu to samo co Wykorzystanie.
        tank_id_range = f"${tank_id_col_letter}${start_data_row}:${tank_id_col_letter}${start_data_row + total_rows - 1}"
        util_range = f"${utilization_letter}${start_data_row}:${utilization_letter}${start_data_row + total_rows - 1}"
        shared_util_formula = (f'=IF({tank_id_col_letter}{row}="",{utilization_letter}{row},'
                                f'SUMIF({tank_id_range},{tank_id_col_letter}{row},{util_range}))')
        shared_cell = ws.cell(row=row, column=shared_util_col, value=shared_util_formula)
        shared_cell.font = font_to_use
        shared_cell.number_format = '0.0"%"'
        shared_cell.fill = computed_fill

        sum_formula = f"=SUM({first_mat_letter}{row}:{last_mat_letter}{row})"
        sum_cell = ws.cell(row=row, column=sum_col, value=sum_formula)
        sum_cell.font = font_to_use
        sum_cell.number_format = '0.0" kg"'
        sum_cell.fill = computed_fill

        raw_demand_formula = (f'=IF({loss_col_letter}{row}>=100,"błąd: straty>=100%",'
                               f'{annual_col_letter}{row}/(1-{loss_col_letter}{row}/100))')
        rd_cell = ws.cell(row=row, column=raw_demand_col, value=raw_demand_formula)
        rd_cell.font = font_to_use
        rd_cell.number_format = '0.00" t"'
        rd_cell.fill = computed_fill

        if pack_names:
            pack_sum_formula = f"=SUM({first_pack_letter}{row}:{last_pack_letter}{row})"
            ps_cell = ws.cell(row=row, column=pack_sum_col, value=pack_sum_formula)
            ps_cell.font = font_to_use
            ps_cell.number_format = '0.0"%"'
            ps_cell.fill = computed_fill

    red_fill = PatternFill("solid", fgColor="FFC7CE")
    rng = f"{sum_col_letter}{start_data_row}:{sum_col_letter}{start_data_row + total_rows - 1}"
    ws.conditional_formatting.add(
        rng,
        FormulaRule(formula=[f"ABS({sum_col_letter}{start_data_row}-{RECIPE_TARGET_SUM_KG})>{RECIPE_SUM_TOLERANCE_KG}"], fill=red_fill)
    )

    util_rng = f"{utilization_letter}{start_data_row}:{utilization_letter}{start_data_row + total_rows - 1}"
    ws.conditional_formatting.add(util_rng, CellIsRule(operator="greaterThan", formula=[str(RECIPE_UTILIZATION_WARN_PCT)], fill=red_fill))

    shared_util_rng = f"{shared_util_col_letter}{start_data_row}:{shared_util_col_letter}{start_data_row + total_rows - 1}"
    ws.conditional_formatting.add(shared_util_rng, CellIsRule(operator="greaterThan", formula=[str(RECIPE_UTILIZATION_WARN_PCT)], fill=red_fill))

    if pack_names:
        pack_sum_rng = f"{pack_sum_col_letter}{start_data_row}:{pack_sum_col_letter}{start_data_row + total_rows - 1}"
        ws.conditional_formatting.add(
            pack_sum_rng,
            FormulaRule(formula=[f"AND({pack_sum_col_letter}{start_data_row}<>0,ABS({pack_sum_col_letter}{start_data_row}-100)>0.5)"], fill=red_fill)
        )

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions[get_column_letter(sourcing_col)].width = 16
    ws.column_dimensions[get_column_letter(transition_col)].width = 18
    ws.column_dimensions[get_column_letter(import_freq_col)].width = 16
    ws.column_dimensions[get_column_letter(import_lot_col)].width = 16
    ws.column_dimensions[get_column_letter(import_safety_col)].width = 16
    for letter in [mixer_vol_letter, cycle_letter, avail_hours_letter, batch_mass_letter, batches_year_letter, utilization_letter]:
        ws.column_dimensions[letter].width = 14
    for col_idx in range(first_mat_col, last_mat_col + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 13
    ws.column_dimensions[sum_col_letter].width = 14
    ws.column_dimensions[density_col_letter].width = 12
    ws.column_dimensions[loss_col_letter].width = 12
    ws.column_dimensions[raw_demand_col_letter].width = 16
    if pack_names:
        for col_idx in range(first_pack_col, last_pack_col + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 14
    ws.column_dimensions[pack_sum_col_letter].width = 14
    ws.column_dimensions[get_column_letter(tank_id_col)].width = 16
    ws.column_dimensions[get_column_letter(shared_util_col)].width = 16
    ws.column_dimensions[get_column_letter(notes_col)].width = 30

    # --- Arkusz 'Opakowania' (opcjonalny) - predefiniowanie typów opakowań i pojemności ---
    ws_pack = wb.create_sheet(PACKAGING_SHEET_NAME)
    pack_headers = [PACKAGING_NAME_COL, PACKAGING_SIZE_COL, PACKAGING_PER_PALLET_COL, PACKAGING_RATE_COL, PACKAGING_NOZZLES_COL]
    for col_idx, h in enumerate(pack_headers, start=1):
        cell = ws_pack.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = wrap_center
    ws_pack.row_dimensions[1].height = 32

    pack_row = 2
    for name, cfg in current_pack_defaults.items():
        is_small_pack = "5l" in name.lower() or "1l" in name.lower() or "4l" in name.lower()
        default_nozzles = 4 if is_small_pack else 1
        default_rate_kg_min = 15.0 if is_small_pack else 60.0
        ws_pack.cell(row=pack_row, column=1, value=name).fill = input_fill
        ws_pack.cell(row=pack_row, column=2, value=cfg.get("size_l", 0)).fill = input_fill
        ws_pack.cell(row=pack_row, column=3, value=cfg.get("per_pallet", 0)).fill = input_fill
        ws_pack.cell(row=pack_row, column=4, value=default_rate_kg_min).fill = input_fill
        ws_pack.cell(row=pack_row, column=5, value=default_nozzles).fill = input_fill
        pack_row += 1
    for col, w in zip("ABCDE", [22, 16, 16, 20, 20]):
        ws_pack.column_dimensions[col].width = w

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.getvalue()


def parse_recipe_excel(uploaded_file):
    """
    Wczytuje wgrany plik Excel z arkusza 'Receptury' (lub pierwszego arkusza, jeśli nazwa
    inna) i zwraca (df_czysty, lista_bledow). Waliduje: obecność wymaganych kolumn, brak
    wartości ujemnych, brak pustego produktu/rocznego zapotrzebowania, poprawność grupy
    produktowej, oraz sumę dozowania surowców w tolerancji wokół 1000 kg/t. Kolumny
    wyliczane ('Suma Udziałów Składników', 'Roczne Zapotrzebowanie Surowcowe') są PRZELICZANE
    w Pythonie (nie czytane z formuł Excela), żeby działać niezależnie od tego, czy plik był
    wcześniej przeliczony przez Excel/LibreOffice.
    """
    errors = []
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = "Receptury" if "Receptury" in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet_name)
    except Exception as exc:
        return None, [f"Nie udało się odczytać pliku Excel: {exc}"]

    required_cols = [RECIPE_GROUP_COL, RECIPE_PRODUCT_COL, RECIPE_ANNUAL_COL] + RECIPE_RAW_MATERIALS + [
        RECIPE_DENSITY_COL, RECIPE_LOSS_COL]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        return None, [f"W pliku brakuje wymaganych kolumn: {', '.join(missing_cols)}. "
                       f"Pobierz i użyj oficjalnego szablonu, nie zmieniając nazw kolumn."]

    if RECIPE_NOTES_COL not in df.columns:
        df[RECIPE_NOTES_COL] = ""
    if RECIPE_TANK_ID_COL not in df.columns:
        df[RECIPE_TANK_ID_COL] = ""
    else:
        df[RECIPE_TANK_ID_COL] = df[RECIPE_TANK_ID_COL].fillna("").astype(str).str.strip()

    # Sposób pozyskania (Import/Produkcja własna) - opcjonalne kolumny, dla zgodności wstecznej
    # z plikami wygenerowanymi starszą wersją szablonu (bez tych kolumn -> wszystko "Produkcja
    # własna", zero zmiany zachowania).
    if RECIPE_SOURCING_COL not in df.columns:
        df[RECIPE_SOURCING_COL] = "Produkcja własna"
    else:
        df[RECIPE_SOURCING_COL] = df[RECIPE_SOURCING_COL].fillna("Produkcja własna").astype(str).str.strip()
        invalid_sourcing = df[~df[RECIPE_SOURCING_COL].isin(RECIPE_SOURCING_OPTIONS)]
        if not invalid_sourcing.empty:
            bad = invalid_sourcing[RECIPE_PRODUCT_COL].tolist()
            errors.append(f"Nieznany '{RECIPE_SOURCING_COL}' (musi być jednym z: {', '.join(RECIPE_SOURCING_OPTIONS)}) dla: "
                           f"{', '.join(map(str, bad))} - przyjęto 'Produkcja własna'.")
            df.loc[~df[RECIPE_SOURCING_COL].isin(RECIPE_SOURCING_OPTIONS), RECIPE_SOURCING_COL] = "Produkcja własna"
    if RECIPE_IMPORT_TRANSITION_COL not in df.columns:
        df[RECIPE_IMPORT_TRANSITION_COL] = ""
    else:
        df[RECIPE_IMPORT_TRANSITION_COL] = df[RECIPE_IMPORT_TRANSITION_COL].fillna("").astype(str).str.strip()
        import_mask = df[RECIPE_SOURCING_COL] == "Import"
        invalid_transition = df[import_mask & ~df[RECIPE_IMPORT_TRANSITION_COL].isin(RECIPE_IMPORT_TRANSITION_OPTIONS)]
        if not invalid_transition.empty:
            bad = invalid_transition[RECIPE_PRODUCT_COL].tolist()
            errors.append(f"Produkty importowane bez poprawnego '{RECIPE_IMPORT_TRANSITION_COL}' (jeden z: "
                           f"{', '.join(RECIPE_IMPORT_TRANSITION_OPTIONS)}): {', '.join(map(str, bad))} - przyjęto 'Rok 1'.")
            bad_idx = invalid_transition.index
            df.loc[bad_idx, RECIPE_IMPORT_TRANSITION_COL] = "Rok 1"
    for col in [RECIPE_IMPORT_FREQ_COL, RECIPE_IMPORT_LOT_COL, RECIPE_IMPORT_SAFETY_DAYS_COL]:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df = df[df[RECIPE_PRODUCT_COL].notna()].copy()
    df = df[~df[RECIPE_PRODUCT_COL].astype(str).str.startswith("Przykład")].copy()

    if df.empty:
        return None, ["Plik nie zawiera żadnych wierszy produktów poza przykładami."]

    import_no_lot = df[(df[RECIPE_SOURCING_COL] == "Import") & (df[RECIPE_IMPORT_LOT_COL] <= 0)]
    if not import_no_lot.empty:
        bad = import_no_lot[RECIPE_PRODUCT_COL].tolist()
        errors.append(f"Produkty importowane bez podanej '{RECIPE_IMPORT_LOT_COL}' (>0): {', '.join(map(str, bad))} - "
                       f"bufor magazynowy importu w Zakładce 4 dla nich nie policzy się poprawnie, dopóki nie uzupełnisz tej wartości.")

    for mat in RECIPE_RAW_MATERIALS:
        df[mat] = pd.to_numeric(df[mat], errors="coerce").fillna(0.0)

    df[RECIPE_ANNUAL_COL] = pd.to_numeric(df[RECIPE_ANNUAL_COL], errors="coerce")
    missing_annual = df[df[RECIPE_ANNUAL_COL].isna()][RECIPE_PRODUCT_COL].tolist()
    if missing_annual:
        errors.append(f"Brak / niepoprawne roczne zapotrzebowanie dla: {', '.join(map(str, missing_annual))}.")
        df = df[df[RECIPE_ANNUAL_COL].notna()].copy()

    df[RECIPE_DENSITY_COL] = pd.to_numeric(df[RECIPE_DENSITY_COL], errors="coerce")
    missing_density = df[df[RECIPE_DENSITY_COL].isna()][RECIPE_PRODUCT_COL].tolist()
    if missing_density:
        errors.append(f"Brak / niepoprawna gęstość dla: {', '.join(map(str, missing_density))} - przyjęto 0.88 g/cm³.")
        df[RECIPE_DENSITY_COL] = df[RECIPE_DENSITY_COL].fillna(0.88)

    df[RECIPE_LOSS_COL] = pd.to_numeric(df[RECIPE_LOSS_COL], errors="coerce").fillna(0.0)
    invalid_loss = df[(df[RECIPE_LOSS_COL] < 0) | (df[RECIPE_LOSS_COL] >= 100)][RECIPE_PRODUCT_COL].tolist()
    if invalid_loss:
        errors.append(f"Nieprawidłowe straty procesowe (muszą być 0-99.9%) dla: {', '.join(map(str, invalid_loss))} - przyjęto 0%.")
        df.loc[(df[RECIPE_LOSS_COL] < 0) | (df[RECIPE_LOSS_COL] >= 100), RECIPE_LOSS_COL] = 0.0

    # Wymiarowanie mieszalnika (opcjonalne - pliki wygenerowane starszą wersją szablonu mogą
    # nie mieć tych kolumn; wtedy wykorzystanie po prostu nie jest liczone dla tych wierszy).
    for col in [RECIPE_MIXER_VOL_COL, RECIPE_CYCLE_COL, RECIPE_AVAIL_HOURS_COL]:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Rozbicie na opakowania (opcjonalne, dynamiczne - dowolna liczba kolumn 'Opak: ... [%]').
    pack_cols_found = [c for c in df.columns if c.startswith("Opak: ") and c.endswith(" [%]")]
    for c in pack_cols_found:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        negative_pack = df[df[c] < 0][RECIPE_PRODUCT_COL].tolist()
        if negative_pack:
            errors.append(f"Ujemny udział opakowania '{c}' dla: {', '.join(map(str, negative_pack))} - przyjęto 0%.")
            df.loc[df[c] < 0, c] = 0.0
    if pack_cols_found:
        df[RECIPE_PACK_SUM_COL] = df[pack_cols_found].sum(axis=1)
        bad_pack_sum = df[(df[RECIPE_PACK_SUM_COL] != 0) & ((df[RECIPE_PACK_SUM_COL] - 100).abs() > 0.5)]
        if not bad_pack_sum.empty:
            details = ", ".join(f"{r[RECIPE_PRODUCT_COL]} ({r[RECIPE_PACK_SUM_COL]:.0f}%)" for _, r in bad_pack_sum.iterrows())
            errors.append(f"Suma % opakowań różni się od 100% dla: {details} - rozbicie na opakowania dla tych wierszy zignorowane "
                           f"(produkcja nadal zaliczona), popraw jeśli chcesz z niego korzystać.")
    else:
        df[RECIPE_PACK_SUM_COL] = 0.0

    unknown_group_mask = ~df[RECIPE_GROUP_COL].astype(str).isin(RECIPE_PRODUCT_GROUPS)
    if unknown_group_mask.any():
        bad = df.loc[unknown_group_mask, RECIPE_PRODUCT_COL].tolist()
        errors.append(f"Nieznana/brakująca grupa produktowa (musi być jedną z: {', '.join(RECIPE_PRODUCT_GROUPS)}) dla: "
                       f"{', '.join(map(str, bad))}. Wiersze pominięte.")
        df = df[~unknown_group_mask].copy()

    negative_mask = (df[RECIPE_RAW_MATERIALS] < 0).any(axis=1)
    if negative_mask.any():
        bad = df.loc[negative_mask, RECIPE_PRODUCT_COL].tolist()
        errors.append(f"Ujemne wartości dozowania [kg/t] dla: {', '.join(map(str, bad))}.")
        df = df[~negative_mask].copy()

    df[RECIPE_SUM_COL] = df[RECIPE_RAW_MATERIALS].sum(axis=1)
    bad_sum_mask = (df[RECIPE_SUM_COL] - RECIPE_TARGET_SUM_KG).abs() > RECIPE_SUM_TOLERANCE_KG
    if bad_sum_mask.any():
        bad_rows = df.loc[bad_sum_mask, [RECIPE_PRODUCT_COL, RECIPE_SUM_COL]]
        details = ", ".join(f"{r[RECIPE_PRODUCT_COL]} ({r[RECIPE_SUM_COL]:.0f} kg/t)" for _, r in bad_rows.iterrows())
        errors.append(f"Suma dozowania surowców odbiega od 1000 kg/t o więcej niż {RECIPE_SUM_TOLERANCE_KG:.0f} kg dla: "
                       f"{details}. Te wiersze zostały pominięte.")
        df = df[~bad_sum_mask].copy()

    dup_mask = df[RECIPE_PRODUCT_COL].duplicated(keep=False)
    if dup_mask.any():
        dups = sorted(set(df.loc[dup_mask, RECIPE_PRODUCT_COL].astype(str)))
        errors.append(f"Zduplikowane nazwy produktów (potraktowane jako oddzielne pozycje): {', '.join(dups)}.")

    if df.empty:
        return None, errors

    # Roczne zapotrzebowanie surowcowe = zapotrzebowanie na GOTOWY produkt / (1 - straty%) -
    # ile surowca faktycznie trzeba zakupić, żeby po stratach procesowych uzyskać zakładany
    # wolumen produktu. Liczone w Pythonie, nie czytane z formuły Excela (patrz docstring).
    df[RECIPE_RAW_DEMAND_COL] = df[RECIPE_ANNUAL_COL] / (1.0 - df[RECIPE_LOSS_COL] / 100.0)

    # Masa Szarży [kg] = pojemność mieszalnika [m3] * 1000 (L/m3) * gęstość [kg/L] - liczone
    # w Pythonie tak samo jak w Excelu, z zabezpieczeniem przed dzieleniem przez zero.
    df[RECIPE_BATCH_MASS_COL] = df[RECIPE_MIXER_VOL_COL] * 1000.0 * df[RECIPE_DENSITY_COL]
    df[RECIPE_BATCHES_YEAR_COL] = 0.0
    has_batch_mass = df[RECIPE_BATCH_MASS_COL] > 0
    df.loc[has_batch_mass, RECIPE_BATCHES_YEAR_COL] = (
        df.loc[has_batch_mass, RECIPE_ANNUAL_COL] * 1000.0 / df.loc[has_batch_mass, RECIPE_BATCH_MASS_COL])

    df[RECIPE_UTILIZATION_COL] = 0.0
    has_avail_hours = df[RECIPE_AVAIL_HOURS_COL] > 0
    df.loc[has_avail_hours, RECIPE_UTILIZATION_COL] = (
        df.loc[has_avail_hours, RECIPE_BATCHES_YEAR_COL] * df.loc[has_avail_hours, RECIPE_CYCLE_COL]
        / df.loc[has_avail_hours, RECIPE_AVAIL_HOURS_COL] * 100.0)

    overloaded = df[df[RECIPE_UTILIZATION_COL] > RECIPE_UTILIZATION_WARN_PCT]
    if not overloaded.empty:
        details = ", ".join(f"{r[RECIPE_PRODUCT_COL]} ({r[RECIPE_UTILIZATION_COL]:.0f}%)" for _, r in overloaded.iterrows())
        errors.append(f"⚠️ Wykorzystanie mieszalnika powyżej {RECIPE_UTILIZATION_WARN_PCT:.0f}% (przeciążenie) dla: {details}.")

    return df.reset_index(drop=True), errors


def parse_packaging_excel(uploaded_file):
    """
    Wczytuje opcjonalny arkusz 'Opakowania' z tego samego pliku Excel co receptury.
    Zwraca (dict_opakowan, lista_bledow). dict_opakowan ma strukturę zgodną z PACK_CONFIGS
    (size_l, per_pallet, rate_szt_h) rozszerzoną o domyślne nozzles/speed_kg_min do
    prekonfiguracji sekcji rozlewu w Zakładce 3. Jeśli arkusz nie istnieje w pliku, zwraca
    (None, []) po cichu - to pole jest opcjonalne, nie każdy plik musi go zawierać.
    """
    try:
        xls = pd.ExcelFile(uploaded_file)
    except Exception as exc:
        return None, [f"Nie udało się odczytać pliku Excel (opakowania): {exc}"]

    if PACKAGING_SHEET_NAME not in xls.sheet_names:
        return None, []

    try:
        df = pd.read_excel(xls, sheet_name=PACKAGING_SHEET_NAME)
    except Exception as exc:
        return None, [f"Nie udało się odczytać arkusza '{PACKAGING_SHEET_NAME}': {exc}"]

    required_cols = [PACKAGING_NAME_COL, PACKAGING_SIZE_COL, PACKAGING_PER_PALLET_COL]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        return None, [f"Arkusz '{PACKAGING_SHEET_NAME}' istnieje, ale brakuje kolumn: {', '.join(missing_cols)}. Pominięto import opakowań."]

    df = df[df[PACKAGING_NAME_COL].notna()].copy()
    if df.empty:
        return None, []

    errors = []
    df[PACKAGING_SIZE_COL] = pd.to_numeric(df[PACKAGING_SIZE_COL], errors="coerce")
    df[PACKAGING_PER_PALLET_COL] = pd.to_numeric(df[PACKAGING_PER_PALLET_COL], errors="coerce")
    if PACKAGING_RATE_COL in df.columns:
        df[PACKAGING_RATE_COL] = pd.to_numeric(df[PACKAGING_RATE_COL], errors="coerce")
    if PACKAGING_NOZZLES_COL in df.columns:
        df[PACKAGING_NOZZLES_COL] = pd.to_numeric(df[PACKAGING_NOZZLES_COL], errors="coerce")

    bad_rows = df[df[PACKAGING_SIZE_COL].isna() | df[PACKAGING_PER_PALLET_COL].isna() |
                  (df[PACKAGING_SIZE_COL] <= 0) | (df[PACKAGING_PER_PALLET_COL] <= 0)]
    if not bad_rows.empty:
        bad_names = bad_rows[PACKAGING_NAME_COL].astype(str).tolist()
        errors.append(f"Pominięto opakowania z brakującą/niepoprawną pojemnością lub liczbą sztuk na palecie: {', '.join(bad_names)}.")
        df = df.drop(bad_rows.index)

    packaging_dict = {}
    filling_defaults = {}
    for _, row in df.iterrows():
        name = str(row[PACKAGING_NAME_COL])
        packaging_dict[name] = {
            "size_l": float(row[PACKAGING_SIZE_COL]),
            "per_pallet": int(row[PACKAGING_PER_PALLET_COL]),
            "rate_szt_h": 0,
        }
        rate = row.get(PACKAGING_RATE_COL) if PACKAGING_RATE_COL in df.columns else None
        nozzles = row.get(PACKAGING_NOZZLES_COL) if PACKAGING_NOZZLES_COL in df.columns else None
        filling_defaults[name] = {
            "speed_kg_min": float(rate) if pd.notna(rate) else 30.0,
            "nozzles": float(nozzles) if pd.notna(nozzles) else 1.0,
        }

    return {"pack_configs": packaging_dict, "filling_defaults": filling_defaults}, errors

# Cennik / Standardowa Instalacja (BOM) - osobny, aktualizowalny arkusz per grupa produktowa,
# z ceną jednostkową komponentu; źródłem treści jest zwykle istniejący P&ID danej instalacji
# standardowej (użytkownik przepisuje stamtąd listę urządzeń, nie generujemy P&ID w apce).
EQUIPMENT_SHEET_NAME = "Cennik Instalacji"
EQUIPMENT_GROUP_COL = "Grupa Produktowa"
EQUIPMENT_COMPONENT_COL = "Komponent"
EQUIPMENT_MODEL_COL = "Typ / Model"
EQUIPMENT_SUPPLIER_COL = "Dostawca"
EQUIPMENT_QTY_COL = "Ilość na instalację [szt]"
EQUIPMENT_UNIT_PRICE_COL = "Cena jednostkowa"
EQUIPMENT_CURRENCY_COL = "Waluta"
EQUIPMENT_NOTES_COL = "Uwagi"
EQUIPMENT_LINE_TOTAL_COL = "Wartość pozycji"


def generate_equipment_template_bytes():
    """
    Buduje w pamięci szablon Excel (openpyxl) do zdefiniowania cennika standardowej instalacji
    per grupa produktowa: komponent, typ/model, dostawca, ilość na instalację, cena
    jednostkowa, waluta, uwagi. 'Wartość pozycji' to formuła (ilość x cena), przeliczana po
    edycji w arkuszu. Wypełniony przykładowymi wierszami dla instalacji silnikowej (Borger
    PL200, czujniki E+H, zawory/elektrozawory Metalwork) jako wzór formatu.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = EQUIPMENT_SHEET_NAME

    header_font = Font(bold=True, name="Arial", size=10, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E78")
    input_fill = PatternFill("solid", fgColor="DDEBF7")
    computed_fill = PatternFill("solid", fgColor="F2F2F2")
    example_font = Font(name="Arial", size=10, italic=True, color="0000FF")
    normal_font = Font(name="Arial", size=10)
    wrap_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    headers = [EQUIPMENT_GROUP_COL, EQUIPMENT_COMPONENT_COL, EQUIPMENT_MODEL_COL, EQUIPMENT_SUPPLIER_COL,
               EQUIPMENT_QTY_COL, EQUIPMENT_UNIT_PRICE_COL, EQUIPMENT_CURRENCY_COL, EQUIPMENT_LINE_TOTAL_COL,
               EQUIPMENT_NOTES_COL]
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = wrap_center
    ws.freeze_panes = "C2"
    ws.row_dimensions[1].height = 32

    ws_info = wb.create_sheet("Instrukcja")
    info_lines = [
        "INSTRUKCJA WYPEŁNIANIA:",
        "1. Nie zmieniaj nazw ani kolejności kolumn.",
        f"2. '{EQUIPMENT_GROUP_COL}' - wybierz z listy rozwijanej: {', '.join(RECIPE_PRODUCT_GROUPS)}.",
        "3. Jeden wiersz = jeden typ komponentu standardowej instalacji dla danej grupy (np. pompa, czujnik, zawór) - "
        "przepisz listę ze swojego P&ID danej instalacji standardowej.",
        f"4. '{EQUIPMENT_QTY_COL}' - ile sztuk tego komponentu jest w JEDNEJ instalacji (np. 2 czujniki temperatury).",
        f"5. '{EQUIPMENT_LINE_TOTAL_COL}' liczy się sama (formuła) = ilość x cena jednostkowa.",
        f"6. Aktualizuj '{EQUIPMENT_UNIT_PRICE_COL}' wraz ze zmianami cen dostawców - to jest właśnie po to, żeby "
        "nie trzeba było grzebać w kodzie aplikacji przy każdej zmianie cennika.",
        "7. W aplikacji (Zakładka 6) podajesz, ile takich instalacji planujesz dla danej grupy - CAPEX przelicza się automatycznie.",
    ]
    for i, line in enumerate(info_lines, start=1):
        c = ws_info.cell(row=i, column=1, value=line)
        c.font = Font(bold=(i == 1), name="Arial", size=11)
    ws_info.column_dimensions["A"].width = 110

    example_rows = [
        {"grp": "Engine Oils", "comp": "Pompa rozładunkowa", "model": "Borger PL200", "sup": "Borger",
         "qty": 1, "price": 18500, "cur": "PLN", "notes": "Pompa wyporowa do rozładunku cystern"},
        {"grp": "Engine Oils", "comp": "Czujnik ciśnienia", "model": "Cerabar PMC21", "sup": "Endress+Hauser",
         "qty": 3, "price": 2400, "cur": "PLN", "notes": ""},
        {"grp": "Engine Oils", "comp": "Czujnik temperatury", "model": "TC10/iTHERM", "sup": "Endress+Hauser",
         "qty": 2, "price": 1800, "cur": "PLN", "notes": ""},
        {"grp": "Engine Oils", "comp": "Zawór z siłownikiem pneumatycznym", "model": "Standard DN50", "sup": "Metalwork",
         "qty": 4, "price": 3200, "cur": "PLN", "notes": ""},
        {"grp": "Engine Oils", "comp": "Elektrozawór sterujący", "model": "Standard 24VDC", "sup": "Metalwork",
         "qty": 4, "price": 650, "cur": "PLN", "notes": ""},
    ]

    group_dv = DataValidation(type="list", formula1='"' + ",".join(RECIPE_PRODUCT_GROUPS) + '"', allow_blank=True)
    ws.add_data_validation(group_dv)

    start_row = 2
    n_blank_rows = 30
    total_rows = len(example_rows) + n_blank_rows

    for r_offset in range(total_rows):
        row = start_row + r_offset
        is_example = r_offset < len(example_rows)
        font_to_use = example_font if is_example else normal_font

        if is_example:
            d = example_rows[r_offset]
            ws.cell(row=row, column=1, value=d["grp"]).font = font_to_use
            ws.cell(row=row, column=2, value=d["comp"]).font = font_to_use
            ws.cell(row=row, column=3, value=d["model"]).font = font_to_use
            ws.cell(row=row, column=4, value=d["sup"]).font = font_to_use
            ws.cell(row=row, column=5, value=d["qty"]).font = font_to_use
            ws.cell(row=row, column=6, value=d["price"]).font = font_to_use
            ws.cell(row=row, column=7, value=d["cur"]).font = font_to_use
            ws.cell(row=row, column=9, value=d["notes"]).font = font_to_use
        else:
            for col_idx in [1, 2, 3, 4, 5, 6, 7, 9]:
                cell = ws.cell(row=row, column=col_idx)
                cell.font = normal_font
                cell.fill = input_fill
            group_dv.add(f"A{row}")

        total_formula = f"=E{row}*F{row}"
        tot_cell = ws.cell(row=row, column=8, value=total_formula)
        tot_cell.font = font_to_use
        tot_cell.number_format = '#,##0.00'
        tot_cell.fill = computed_fill

    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 10
    ws.column_dimensions["H"].width = 16
    ws.column_dimensions["I"].width = 30

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.getvalue()


def parse_equipment_excel(uploaded_file):
    """
    Wczytuje plik Excel z arkusza 'Cennik Instalacji' (lub pierwszego arkusza) i zwraca
    (df_czysty, lista_bledow). Waliduje: wymagane kolumny, poprawność grupy produktowej,
    nieujemne ilości/ceny. 'Wartość pozycji' PRZELICZANA w Pythonie (nie czytana z formuły).
    """
    errors = []
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = EQUIPMENT_SHEET_NAME if EQUIPMENT_SHEET_NAME in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet_name)
    except Exception as exc:
        return None, [f"Nie udało się odczytać pliku Excel: {exc}"]

    required_cols = [EQUIPMENT_GROUP_COL, EQUIPMENT_COMPONENT_COL, EQUIPMENT_QTY_COL, EQUIPMENT_UNIT_PRICE_COL]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        return None, [f"W pliku brakuje wymaganych kolumn: {', '.join(missing_cols)}. "
                       f"Pobierz i użyj oficjalnego szablonu, nie zmieniając nazw kolumn."]

    for c in [EQUIPMENT_MODEL_COL, EQUIPMENT_SUPPLIER_COL, EQUIPMENT_CURRENCY_COL, EQUIPMENT_NOTES_COL]:
        if c not in df.columns:
            df[c] = ""

    df = df[df[EQUIPMENT_COMPONENT_COL].notna()].copy()
    if df.empty:
        return None, ["Plik nie zawiera żadnych wierszy komponentów."]

    df[EQUIPMENT_QTY_COL] = pd.to_numeric(df[EQUIPMENT_QTY_COL], errors="coerce")
    df[EQUIPMENT_UNIT_PRICE_COL] = pd.to_numeric(df[EQUIPMENT_UNIT_PRICE_COL], errors="coerce")

    bad_rows = df[df[EQUIPMENT_QTY_COL].isna() | df[EQUIPMENT_UNIT_PRICE_COL].isna() |
                  (df[EQUIPMENT_QTY_COL] < 0) | (df[EQUIPMENT_UNIT_PRICE_COL] < 0)]
    if not bad_rows.empty:
        bad_names = bad_rows[EQUIPMENT_COMPONENT_COL].astype(str).tolist()
        errors.append(f"Pominięto komponenty z brakującą/ujemną ilością lub ceną: {', '.join(bad_names)}.")
        df = df.drop(bad_rows.index)

    unknown_group_mask = ~df[EQUIPMENT_GROUP_COL].astype(str).isin(RECIPE_PRODUCT_GROUPS)
    if unknown_group_mask.any():
        bad = df.loc[unknown_group_mask, EQUIPMENT_COMPONENT_COL].tolist()
        errors.append(f"Nieznana/brakująca grupa produktowa (musi być jedną z: {', '.join(RECIPE_PRODUCT_GROUPS)}) dla: "
                       f"{', '.join(map(str, bad))}. Wiersze pominięte.")
        df = df[~unknown_group_mask].copy()

    if df.empty:
        return None, errors

    df[EQUIPMENT_LINE_TOTAL_COL] = df[EQUIPMENT_QTY_COL] * df[EQUIPMENT_UNIT_PRICE_COL]

    return df.reset_index(drop=True), errors



# ==========================================
# FUNKCJE POMOCNICZE (wydzielone z pętli UI, aby dało się je testować niezależnie)
# ==========================================

def reynolds_number(velocity_ms, diameter_m, viscosity_cst):
    """Liczba Reynoldsa dla przepływu w rurze kołowej."""
    viscosity_m2s = viscosity_cst * 1e-6
    if viscosity_m2s <= 0 or diameter_m <= 0:
        return 0.0
    return (velocity_ms * diameter_m) / viscosity_m2s


def friction_factor(re):
    """
    Współczynnik oporów liniowych.
    - Re <= 2320: przepływ laminarny, wzór Hagen-Poiseuille (64/Re).
    - Re > 2320: przepływ turbulentny, korelacja Blasiusa (ważna dla Re < ~1e5,
      co pokrywa typowe warunki przetłaczania olejów/emulsji w tej instalacji).
    """
    if re <= 0:
        return 0.0
    if re <= 2320:
        return 64.0 / re
    return 0.316 * (re ** -0.25)


def compute_hydraulics(q_m3h, pipe_dn_mm, pipe_length_m, delta_h_m, viscosity_cst,
                        density_kgm3, zeta_sum, pump_efficiency):
    """Zwraca (Re, opór całkowity [bar], moc pompy [kW], prędkość [m/s])."""
    q_m3s = q_m3h / 3600.0
    d_m = pipe_dn_mm / 1000.0
    area_m2 = math.pi * (d_m ** 2) / 4.0
    velocity = q_m3s / area_m2 if area_m2 > 0 else 0.0

    dynamic_pressure = density_kgm3 * (velocity ** 2) / 2.0
    p_hydrostatic = density_kgm3 * G_ACCEL * delta_h_m

    re = reynolds_number(velocity, d_m, viscosity_cst)
    lam = friction_factor(re)

    p_loss_lin = lam * (pipe_length_m / d_m) * dynamic_pressure if d_m > 0 else 0.0
    tot_p_pa = p_loss_lin + (zeta_sum * dynamic_pressure) + p_hydrostatic
    tot_p_bar = tot_p_pa / 100000.0
    power_kw = (q_m3s * tot_p_pa) / pump_efficiency / 1000.0 if pump_efficiency > 0 else 0.0

    return re, tot_p_bar, power_kw, velocity


def compute_agitator_power(agitator_type, rpm, impeller_d_m, density_kgm3, viscosity_cst):
    """
    Szacunkowa moc mieszania na podstawie liczby Reynoldsa mieszania.
    Reżim laminarny:  P = C * mu * N^2 * D^3
    Reżim turbulentny: P = Ne * rho * N^3 * D^5
    Zwraca (Re_mix, reżim, moc [kW]).
    """
    cfg = AGITATOR_TYPES.get(agitator_type)
    if cfg is None or rpm <= 0 or impeller_d_m <= 0:
        return 0.0, "brak danych", 0.0

    n_rps = rpm / 60.0
    mu_pas = (viscosity_cst * 1e-6) * density_kgm3  # cSt -> m2/s -> Pa*s

    re_mix = (density_kgm3 * n_rps * (impeller_d_m ** 2)) / mu_pas if mu_pas > 0 else 1e9

    if re_mix <= 10:
        regime = "laminarny"
        power_w = cfg["laminar_C"] * mu_pas * (n_rps ** 2) * (impeller_d_m ** 3)
    else:
        regime = "turbulentny"
        power_w = cfg["turbulent_Ne"] * density_kgm3 * (n_rps ** 3) * (impeller_d_m ** 5)

    return re_mix, regime, power_w / 1000.0


def compute_thermal_balance(mass_product_kg, cp_product, t_in, t_out, k_coeff_grzania, exchange_area_m2,
                             tank_mass_kg, cp_steel, utility_type_heat, delta_t_medium_grzewcze,
                             t_utility_heat_in):
    """
    Bilans grzania — analogicznie do compute_cooling: moc grzania wynika z fizyki wymiennika
    (k*A*ΔT), a CZAS grzania jest z niej WYLICZANY (Q/moc), a nie odwrotnie. ΔT po stronie
    produktu liczone jest w uproszczeniu jako różnica temperatury medium grzewczego i średniej
    temperatury produktu (wejście/wyjście), tak samo jak w compute_cooling.

    Przepływ medium NIE jest już wejściem użytkownika — jest WYLICZANY z mocy grzania i
    zaprojektowanego spadku temperatury medium (delta_t_medium_grzewcze): Moc = przepływ * cp * ΔT,
    więc przepływ = Moc / (cp * ΔT). To jednocześnie ustala temperaturę wyjścia medium wprost
    (t_utility_heat_in - delta_t_medium_grzewcze), bez potrzeby zgadywania przepływu.
    Dla pary nasyconej liczy zapotrzebowanie przez ciepło skraplania (przepływ = masa kondensatu/h).
    Zwraca dict z energią, mocą, wyliczonym czasem grzania, przepływem medium, temperaturą
    wyjścia medium i LMTD.
    """
    delta_t_heating = t_out - t_in
    q_heating_kj = (mass_product_kg * cp_product * delta_t_heating) + (tank_mass_kg * cp_steel * delta_t_heating)
    q_heating_mj = q_heating_kj / 1000.0

    approx_dt_heating = t_utility_heat_in - ((t_in + t_out) / 2.0)
    if approx_dt_heating <= 0:
        # Medium grzewcze jest zbyt zimne względem produktu - wymiennik nie zadziała.
        power_heating_kw = 0.0
        process_time_h = float("nan")
        heating_status = "niewystarczajace_dt"
    else:
        power_heating_kw = (k_coeff_grzania * exchange_area_m2 * approx_dt_heating) / 1000.0
        process_time_h = q_heating_kj / (power_heating_kw * 3600.0) if power_heating_kw > 0 else float("nan")
        heating_status = "ok"

    media_cfg = MEDIA_PROCESOWE[utility_type_heat]
    is_steam = media_cfg.get("steam", False)

    if heating_status == "ok":
        if is_steam:
            # Para: energia pochodzi ze skraplania, temperatura pary ~stała (nasycenie);
            # przepływ = wymagana masa kondensatu na godzinę.
            flow_heating_kg_h = (power_heating_kw * 3600.0) / STEAM_LATENT_HEAT_KJKG if STEAM_LATENT_HEAT_KJKG > 0 else 0.0
            t_utility_heat_out = t_utility_heat_in
        else:
            cp_heat_utility = media_cfg["cp"]
            flow_heating_kg_h = (power_heating_kw * 3600.0) / (cp_heat_utility * delta_t_medium_grzewcze) \
                if (cp_heat_utility > 0 and delta_t_medium_grzewcze > 0) else 0.0
            t_utility_heat_out = t_utility_heat_in - delta_t_medium_grzewcze
        mass_utility_heat_kg = flow_heating_kg_h * process_time_h
    else:
        flow_heating_kg_h = 0.0
        mass_utility_heat_kg = 0.0
        t_utility_heat_out = t_utility_heat_in - 5.0

    dt1_h = t_utility_heat_in - t_out
    dt2_h = t_utility_heat_out - t_in

    if dt1_h <= 0 or dt2_h <= 0:
        lmtd_h = 0.0
        lmtd_trigger = "error"
    else:
        lmtd_h = (dt1_h - dt2_h) / math.log(dt1_h / dt2_h) if abs(dt1_h - dt2_h) > 0.1 else dt1_h
        lmtd_trigger = "optimal" if LMTD_MIN_K <= lmtd_h <= LMTD_MAX_K else "warning"

    return {
        "q_heating_mj": q_heating_mj,
        "power_heating_kw": power_heating_kw,
        "process_time_h": process_time_h,
        "heating_status": heating_status,
        "flow_heating_kg_h": flow_heating_kg_h,
        "mass_utility_heat_kg": mass_utility_heat_kg,
        "t_utility_heat_out": t_utility_heat_out,
        "lmtd_h": lmtd_h,
        "lmtd_trigger": lmtd_trigger,
        "is_steam": is_steam,
    }


def compute_cooling(mass_product_kg, cp_product, t_out, t_discharge, t_utility_cool_in,
                     k_coeff, exchange_area_m2, utility_type_cool, delta_t_medium_chlodzace):
    """
    Bilans chłodzenia produktu do temperatury rozlewu. Analogicznie do grzania, przepływ
    chłodziwa jest WYLICZANY z mocy chłodzenia i zaprojektowanego wzrostu temperatury chłodziwa
    (delta_t_medium_chlodzace), zamiast być zgadywany.
    Zwraca (MJ, moc kW, czas h, przepływ chłodziwa kg/h, ostrzeżenie).
    """
    delta_t_cooling = t_out - t_discharge
    if delta_t_cooling <= 0:
        return 0.0, 0.0, 0.0, 0.0, "brak_potrzeby"

    q_cooling_kj = mass_product_kg * cp_product * delta_t_cooling
    q_cooling_mj = q_cooling_kj / 1000.0

    approx_dt_cooling = ((t_out + t_discharge) / 2.0) - t_utility_cool_in
    if approx_dt_cooling <= 0:
        # Medium chłodzące jest zbyt ciepłe względem produktu - wymiennik nie zadziała.
        return q_cooling_mj, 0.0, float("nan"), 0.0, "niewystarczajace_dt"

    cooling_power_kw = (k_coeff * exchange_area_m2 * approx_dt_cooling) / 1000.0
    cooling_time_h = q_cooling_kj / (cooling_power_kw * 3600.0) if cooling_power_kw > 0 else float("nan")

    cp_cool_utility = MEDIA_PROCESOWE[utility_type_cool]["cp"]
    flow_cooling_kg_h = (cooling_power_kw * 3600.0) / (cp_cool_utility * delta_t_medium_chlodzace) \
        if (cp_cool_utility > 0 and delta_t_medium_chlodzace > 0) else 0.0

    return q_cooling_mj, cooling_power_kw, cooling_time_h, flow_cooling_kg_h, "ok"


# Ściągawka średnic rur stalowych (średnica wewnętrzna [m]) do wyboru DN w module pary.
STEAM_PIPE_DN_REFERENCE_M = {
    "DN80": 0.0800, "DN100": 0.1053, "DN125": 0.1300, "DN150": 0.1586, "DN200": 0.2073,
}


def compute_vent_line_scenario(mass_flow_kgs, rho_steam, pipe_length_m, pipe_diameter_m, lambda_friction):
    """
    Bilans hydrauliczny linii odpowietrzenia/zrzutu pary dla jednego scenariusza pracy,
    metodą Darcy-Weisbacha - analogicznie do compute_hydraulics dla cieczy, ale tu strumień
    wejściowy to zadany strumień masowy pary [kg/s] (nie przepływ objętościowy pompy), a opory
    liczone są jako czysto liniowe (bez lokalnych zeta), zgodnie z modelem referencyjnym
    użytkownika (ISO 28300 / API 2000).
    Zwraca (objętość [m3/s], prędkość [m/s], opory [Pa], opory [bar]).
    """
    if rho_steam <= 0 or pipe_diameter_m <= 0:
        return 0.0, 0.0, 0.0, 0.0
    volumetric_flow_m3s = mass_flow_kgs / rho_steam
    area_m2 = 3.14159265 * (pipe_diameter_m ** 2) / 4.0
    velocity_ms = volumetric_flow_m3s / area_m2 if area_m2 > 0 else 0.0
    dp_pa = lambda_friction * (pipe_length_m / pipe_diameter_m) * (rho_steam * velocity_ms ** 2 / 2.0) if pipe_diameter_m > 0 else 0.0
    dp_bar = dp_pa / 100000.0
    return volumetric_flow_m3s, velocity_ms, dp_pa, dp_bar


# --- 2. INICJALIZACJA STRUKTUR W SESJI ---
if "active_portfolio" not in st.session_state:
    # Startowo = 7 generycznych grup produktowych (GENERIC_PORTFOLIO); wgrana receptura
    # (Zakładka 1) odświeża gęstość/cykl/materiał danej grupy jej własnymi wartościami.
    st.session_state.active_portfolio = {k: dict(v) for k, v in GENERIC_PORTFOLIO.items()}

if "prod_dict" not in st.session_state:
    st.session_state.prod_dict = {
        k: {"roczna": 1200000, "user_vol_m3": 15.0, "skus": 1, "num_tanks": 1, "tank_volumes": [15.0]} for k in st.session_state.active_portfolio.keys()
    }

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

if "calculated_times" not in st.session_state:
    st.session_state.calculated_times = {}

if "mixer_tech_advanced_details" not in st.session_state:
    st.session_state.mixer_tech_advanced_details = {}

if "batch_time_components" not in st.session_state:
    st.session_state.batch_time_components = {}

if "recipes_df" not in st.session_state:
    st.session_state.recipes_df = None  # DataFrame wgranych receptur (produkt, roczne zapotrzebowanie, % surowców)

if "recipe_raw_material_consumption" not in st.session_state:
    st.session_state.recipe_raw_material_consumption = None  # dict: surowiec -> t/rok, liczone z recipes_df

if "pack_configs" not in st.session_state:
    # Startowo = wbudowane wartości domyślne (PACK_CONFIGS); po wgraniu arkusza 'Opakowania'
    # w Zakładce 1 są nadpisywane/uzupełniane, a dalej pozostają w pełni edytowalne w apce.
    st.session_state.pack_configs = {k: dict(v) for k, v in PACK_CONFIGS.items()}

if "equipment_df" not in st.session_state:
    st.session_state.equipment_df = None  # DataFrame cennika standardowej instalacji (Zakładka 6)

if "equipment_install_counts" not in st.session_state:
    st.session_state.equipment_install_counts = {}  # dict: Grupa Produktowa -> liczba planowanych instalacji

if "recipe_groups_seen" not in st.session_state:
    st.session_state.recipe_groups_seen = set()  # grupy produktowe z receptury już raz zsynchronizowane z flotą

if "_last_recipe_group_signature" not in st.session_state:
    st.session_state._last_recipe_group_signature = None

if "shared_pumps" not in st.session_state:
    # Pompy współdzielone przez kilka zbiorników (jedna fizyczna pompa obsługująca kilka
    # mieszalników na przemian) - jedno źródło prawdy dla przepływu/sprawności/MTBF/MTTR
    # takiej pompy, niezależnie od tego, ile zbiorników ją współdzieli. Klucz = ID pompy
    # nadane przez użytkownika (np. "P-01"), wartość = dict z parametrami.
    st.session_state.shared_pumps = {}

if "rampup_global_pct" not in st.session_state:
    # Domyślna krzywa rozruchu (% docelowej produkcji osiągane w kolejnych latach) - flota i
    # magazyn są wymiarowane od razu pod docelową (100%) produkcję; ta krzywa opisuje jedynie
    # jak rośnie ich WYKORZYSTANIE w pierwszych RAMPUP_YEARS latach.
    st.session_state.rampup_global_pct = [40.0, 60.0, 80.0, 95.0, 100.0][:RAMPUP_YEARS]
if "rampup_differentiate" not in st.session_state:
    st.session_state.rampup_differentiate = False
if "rampup_per_line_pct" not in st.session_state:
    st.session_state.rampup_per_line_pct = {}  # dict: linia -> lista % per rok (tylko gdy differentiate=True)


def get_rampup_fraction(product_family, year_idx):
    """
    Ułamek (0-1) docelowej produkcji osiąganej w danym roku symulacji rozruchu, dla danej
    linii produktowej. Jedno źródło prawdy używane zarówno w Zakładce 2 (utylizacja floty)
    jak i Zakładce 4 (wykorzystanie magazynu FG+RM) - patrz sync_recipes_into_fleet_defaults
    dla analogicznego wzorca "jedno miejsce prawdy, wiele zakładek czyta".
    """
    if st.session_state.get("rampup_differentiate") and product_family in st.session_state.get("rampup_per_line_pct", {}):
        pct_list = st.session_state.rampup_per_line_pct[product_family]
    else:
        pct_list = st.session_state.get("rampup_global_pct", [100.0] * RAMPUP_YEARS)
    if year_idx < 0 or year_idx >= len(pct_list):
        return 1.0
    return max(0.0, min(float(pct_list[year_idx]), 100.0)) / 100.0


def sync_recipes_into_fleet_defaults():
    """
    Spina Zakładkę 1 (Receptury) z Zakładką 2 (Flota) NA POZIOMIE GRUPY PRODUKTOWEJ - tak jak
    w pliku Excel (Cleaners/Engine Oils/Glycols/Greases/Hydraulic Oils/Watermiscibles/Waxes),
    a nie per pojedynczy produkt czy stara szczegółowa linia FUCHS_PORTFOLIO. Każda grupa
    obecna w recepturze staje się JEDNĄ pozycją do wyboru w panelu bocznym.

    W ramach grupy, wiersze (produkty) dzielą się na "sloty" zbiornikowe wg RECIPE_TANK_ID_COL:
    - Puste ID -> każdy produkt dostaje swój własny, dedykowany zbiornik (jak dotychczas).
    - To samo niepuste ID w kilku wierszach -> te produkty WSPÓŁDZIELĄ jeden fizyczny
      mieszalnik (produkcja kampanijna). Pojemność takiego zbiornika = max spośród zadanych
      (musi pomieścić największą recepturę), a wykorzystanie czasowe liczone jest jako SUMA
      (szarże_i x cykl_i) po wszystkich produktach tego zbiornika - patrz tank_members,
      zużywane w Zakładce 2 do właściwego (nie uproszczonego) przeliczenia utylizacji.

    active_portfolio odświeża się przy każdym uruchomieniu (bezpieczne - nic w Zakładce 2 tego
    ręcznie nie edytuje). prod_dict dla danej grupy ustawiany jest z receptury TYLKO przy jej
    pierwszym pojawieniu się - późniejsze ręczne poprawki w Zakładce 2 nie są nadpisywane przy
    kolejnych edycjach receptury. Wybór w panelu bocznym jest resetowany do dokładnie grup z
    receptury TYLKO gdy zmieni się sam ZESTAW grup w recepturze (nowa/usunięta grupa) - między
    takimi zmianami można swobodnie dopisać ręcznie inne linie bez ich utraty.
    """
    df = st.session_state.get("recipes_df")
    if df is None or df.empty:
        return

    groups_in_recipe = sorted(df[RECIPE_GROUP_COL].dropna().unique().tolist())

    for group_name in groups_in_recipe:
        group_rows_all = df[df[RECIPE_GROUP_COL] == group_name]

        # Produkty "Import - Nigdy" (stały import) nigdy nie dostają własnego mieszalnika -
        # nawet w widoku docelowym/100% pozostają importowane, więc wykluczamy je z sizingu
        # floty. Produkty "Import" z ustalonym rokiem przejścia ZOSTAJĄ w sizingu, bo flota
        # jest wymiarowana pod docelową (w pełni dojrzałą, czyli już produkowaną) zdolność.
        if RECIPE_SOURCING_COL in group_rows_all.columns and RECIPE_IMPORT_TRANSITION_COL in group_rows_all.columns:
            permanent_import_mask = (group_rows_all[RECIPE_SOURCING_COL] == "Import") & \
                                     (group_rows_all[RECIPE_IMPORT_TRANSITION_COL] == "Nigdy (stały import)")
            group_rows = group_rows_all[~permanent_import_mask]
        else:
            group_rows = group_rows_all

        if group_rows.empty:
            continue  # cała grupa to stały import - brak mieszalnika dla tej grupy

        defaults = GROUP_PHYSICAL_DEFAULTS.get(group_name, GROUP_PHYSICAL_DEFAULTS["Hydraulic Oils"])

        weights = group_rows[RECIPE_ANNUAL_COL].clip(lower=0.001)
        avg_density = float((group_rows[RECIPE_DENSITY_COL] * weights).sum() / weights.sum()) if weights.sum() > 0 else 0.88
        total_annual_kg = float(group_rows[RECIPE_ANNUAL_COL].sum()) * 1000.0

        # Podział wierszy grupy na sloty zbiornikowe wg ID Zbiornika (puste = własny slot).
        tank_id_col_vals = group_rows[RECIPE_TANK_ID_COL].fillna("").astype(str).str.strip() if RECIPE_TANK_ID_COL in group_rows.columns else pd.Series([""] * len(group_rows), index=group_rows.index)
        slots, seen_ids = [], {}
        for idx, tid in tank_id_col_vals.items():
            if tid:
                if tid not in seen_ids:
                    seen_ids[tid] = len(slots)
                    slots.append([idx])
                else:
                    slots[seen_ids[tid]].append(idx)
            else:
                slots.append([idx])

        tank_volumes, tank_cycles, tank_products, tank_members = [], [], [], []
        for slot_idxs in slots:
            slot_rows = group_rows.loc[slot_idxs]
            members, slot_vols = [], []
            for _, r in slot_rows.iterrows():
                v = r.get(RECIPE_MIXER_VOL_COL, 0) or 0
                v = float(v) if v > 0 else 15.0
                slot_vols.append(v)
                c = r.get(RECIPE_CYCLE_COL, 0) or 0
                c = float(c) if c > 0 else defaults["cycle_h"]
                dens = float(r.get(RECIPE_DENSITY_COL, 0) or 0.88)
                annual_kg_i = float(r.get(RECIPE_ANNUAL_COL, 0) or 0) * 1000.0
                members.append({"product": str(r[RECIPE_PRODUCT_COL]), "annual_kg": annual_kg_i, "density": dens, "cycle_h": c})

            slot_vol = max(slot_vols) if slot_vols else 15.0
            total_w = sum(m["annual_kg"] for m in members) or 1.0
            weighted_cycle = sum(m["cycle_h"] * m["annual_kg"] for m in members) / total_w

            tank_volumes.append(slot_vol)
            tank_cycles.append(weighted_cycle)
            tank_products.append(members[0]["product"] if len(members) == 1 else None)
            tank_members.append(members)

        avg_vol = sum(tank_volumes) / len(tank_volumes) if tank_volumes else 15.0
        avg_cycle = sum(tank_cycles) / len(tank_cycles) if tank_cycles else defaults["cycle_h"]
        n_tanks = len(slots)
        n_skus = len(group_rows)

        # active_portfolio - bezpieczne do odświeżania co przebieg (nic tego ręcznie nie edytuje).
        st.session_state.active_portfolio[group_name] = {
            "material": defaults["material"], "density": avg_density, "cycle_h": avg_cycle,
            "cp": defaults["cp"], "oil_group": defaults["oil_group"], "water_content": defaults["water_content"],
        }

        if group_name not in st.session_state.recipe_groups_seen:
            st.session_state.prod_dict[group_name] = {
                "roczna": total_annual_kg, "user_vol_m3": avg_vol, "skus": n_skus, "num_tanks": n_tanks,
                "tank_volumes": tank_volumes, "tank_cycles": tank_cycles, "cycle_h_base": avg_cycle,
                "tank_products": tank_products, "tank_members": tank_members,
            }
            st.session_state.recipe_groups_seen.add(group_name)
        elif "tank_members" not in st.session_state.prod_dict[group_name]:
            # Zgodność wsteczna: grupa zsynchronizowana starszą wersją tej funkcji.
            st.session_state.prod_dict[group_name]["tank_products"] = tank_products
            st.session_state.prod_dict[group_name]["tank_members"] = tank_members
        else:
            # Grupa była już wcześniej zsynchronizowana - sprawdź, czy ZESTAW produktów tej
            # grupy w recepturze (nazwa, sposób pozyskania, rok przejścia, ID zbiornika) zmienił
            # się od ostatniej synchronizacji. Bez tego sprawdzenia zmiana np. "Sposób
            # Pozyskania" produktu z "Produkcja własna" na "Import" po ponownym wgraniu
            # receptury NIGDY by się nie przebiła do floty (Zakładka 2/4), bo ta gałąź kodu
            # istnieje właśnie po to, żeby NIE nadpisywać ręcznych edycji użytkownika w
            # Zakładce 2 przy każdym przebiegu - ale musi się jednak odświeżyć, gdy dane
            # źródłowe faktycznie się zmieniły, a nie tylko przy pierwszym pojawieniu się grupy.
            current_signature = tuple(sorted(
                (str(r[RECIPE_PRODUCT_COL]), str(r.get(RECIPE_SOURCING_COL, "") or ""),
                 str(r.get(RECIPE_IMPORT_TRANSITION_COL, "") or ""), str(r.get(RECIPE_TANK_ID_COL, "") or ""))
                for _, r in group_rows.iterrows()
            ))
            st.session_state.setdefault("recipe_group_product_signature", {})
            stored_signature = st.session_state.recipe_group_product_signature.get(group_name)
            if stored_signature != current_signature:
                st.session_state.prod_dict[group_name] = {
                    "roczna": total_annual_kg, "user_vol_m3": avg_vol, "skus": n_skus, "num_tanks": n_tanks,
                    "tank_volumes": tank_volumes, "tank_cycles": tank_cycles, "cycle_h_base": avg_cycle,
                    "tank_products": tank_products, "tank_members": tank_members,
                }
            st.session_state.recipe_group_product_signature[group_name] = current_signature


    group_signature = tuple(groups_in_recipe)
    if st.session_state._last_recipe_group_signature != group_signature:
        st.session_state["wybrane_kategorie_ms"] = groups_in_recipe
        st.session_state._last_recipe_group_signature = group_signature


sync_recipes_into_fleet_defaults()

if st.session_state.recipes_df is None:
    st.info("👋 **Zacznij od Zakładki 1 (Receptury Produktów)** — pobierz szablon, wgraj recepturę produktów "
            "(z wolumenem produkcji, opcjonalnie wielkością mieszalnika i rozbiciem na opakowania) i wróć tu, "
            "żeby dalej skonfigurować flotę i instalację. Możesz też pominąć ten krok i pracować w pełni ręcznie "
            "w kolejnych zakładkach.")
else:
    st.success("✅ Receptura wgrana — grupy produktowe pojawiły się automatycznie w Zakładce 2 (panel boczny, "
               "Krok 1: Wybór Rodzin), każda z liczbą zbiorników = liczbie produktów tej grupy w recepturze. "
               "Możesz je tam dalej edytować.")
    st.caption("⚠️ **Jeśli to ponowne wgranie już wcześniej używanej receptury** (np. zmieniłeś '{}' albo dane "
               "importu dla produktu): zmiana na poziomie produktu (kto importuje, kto produkuje, kiedy) trafi do "
               "Zakładki 2, ale **flota widoczna w Zakładce 4/6 aktualizuje się dopiero po ponownym kliknięciu "
               "'📥 Zatwierdź i wyślij konfigurację do kolejnych kroków' w Zakładce 2** — to jest jawny krok "
               "zatwierdzenia, nie dzieje się automatycznie.".format(RECIPE_SOURCING_COL))

# ==========================================
# PANEL BOCZNY (Wybór Rodzin i Opakowań)
# ==========================================
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
_default_lines = (sorted(st.session_state.recipe_groups_seen) if st.session_state.recipe_groups_seen
                   else ["Hydraulic Oils", "Engine Oils", "Watermiscibles"])
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne grupy produktowe:",
    list(st.session_state.active_portfolio.keys()),
    default=_default_lines,
    key="wybrane_kategorie_ms"
)

st.sidebar.markdown("---")

st.sidebar.header("⏱️ KROK 2: Założenia Czasu Pracy")
liczba_zmian = st.sidebar.slider("Liczba zmian produkcyjnych:", min_value=1.0, max_value=3.0, value=1.0, step=0.5)
godziny_na_zmiane = st.sidebar.slider("Liczba godzin na jedną zmianę:", min_value=4.0, max_value=12.0, value=8.0, step=0.5)

godziny_dziennie = liczba_zmian * godziny_na_zmiane
AVAILABLE_HOURS_MONTH = (WORKING_DAYS_YEAR * godziny_dziennie) / MONTHS_PER_YEAR

st.sidebar.markdown("---")

# --- STRUKTURA INTERFEJSU ---
tab7, tab1, tab2, tab3, tab5, tab4, tab6 = st.tabs([
    "📋 1. Receptury Produktów (Start)",
    "📊 2. Główne Zestawienie i Utylizacja",
    "📐 3. Karta Maszyn, Kocioł i Zasilanie",
    "📦 4. Logistyka i Czas Rozlewu",
    "🛢️ 5. Surowce i Park Zbiorników",
    "💰 6. Analiza Finansowa, CAPEX i ROI",
    "🧵 7. Mapa Strumienia Wartości (VSM)"
])

# ==========================================
# ZAKŁADKA 1: FLOTA MIESZALNIKÓW
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych")

    if wybrane_kategorie:
        st.markdown("##### 📥 Krok A: Parametryzacja Tonażu, Pojemności Mieszalnika oraz SKUs")
        st.caption("Wybierz linię z listy, aby błyskawicznie i płynnie zmienić jej parametry. Wyniki w tabeli poniżej przeliczą się natychmiast.")

        selected_family_to_edit = st.selectbox("Wybierz linię produktową do modyfikacji:", wybrane_kategorie)

        c_ed1, c_ed2, c_ed3, c_ed4 = st.columns(4)
        with c_ed1:
            st.session_state.prod_dict[selected_family_to_edit]["roczna"] = st.number_input(
                "Roczna produkcja [kg]:", min_value=0, value=int(st.session_state.prod_dict[selected_family_to_edit]["roczna"]), step=50000,
                key=f"roczna_{selected_family_to_edit}"
            )
        with c_ed2:
            st.session_state.prod_dict[selected_family_to_edit]["user_vol_m3"] = st.number_input(
                "Pojemność Mieszalnika (bazowa) [m³]:", min_value=0.5, value=float(st.session_state.prod_dict[selected_family_to_edit]["user_vol_m3"]), step=0.5,
                help="Używana bezpośrednio, gdy linia ma jeden zbiornik. Przy kilku zbiornikach to wartość domyślna dla nowo dodanych — każdy można potem zróżnicować poniżej.",
                key=f"pojemnosc_baza_{selected_family_to_edit}"
            )
        with c_ed3:
            st.session_state.prod_dict[selected_family_to_edit].setdefault("cycle_h_base", st.session_state.active_portfolio[selected_family_to_edit]["cycle_h"])
            st.session_state.prod_dict[selected_family_to_edit]["cycle_h_base"] = st.number_input(
                "Cykl Procesowy (bazowy, szacunkowy) [h]:", min_value=0.5, value=float(st.session_state.prod_dict[selected_family_to_edit]["cycle_h_base"]), step=0.5,
                help="Szacunkowy czas cyklu jednej szarży (dozowanie + grzanie + homogenizacja + chłodzenie + rozlew), do wstępnego wymiarowania floty — "
                     "różne receptury/wielkości szarży realnie różnią się czasem cyklu. Po skonfigurowaniu inżynierii w Zakładce 3/8 zobaczysz obok "
                     "rzeczywisty, policzony czas cyklu do porównania.",
                key=f"cykl_baza_{selected_family_to_edit}"
            )
        with c_ed4:
            st.session_state.prod_dict[selected_family_to_edit]["skus"] = st.number_input(
                "Liczba aktywnych SKUs:", min_value=1, value=int(st.session_state.prod_dict[selected_family_to_edit]["skus"]), step=1,
                key=f"skus_{selected_family_to_edit}"
            )

        current_skus = st.session_state.prod_dict[selected_family_to_edit]["skus"]
        _tank_members_current = st.session_state.prod_dict[selected_family_to_edit].get("tank_members", [])
        _has_recipe_products = any(len(m) > 0 for m in _tank_members_current)

        if current_skus > 1:
            st.markdown("---")
            st.session_state.prod_dict[selected_family_to_edit]["num_tanks"] = st.number_input(
                f"🏭 **Wielkość floty dla {selected_family_to_edit}**: Na ile osobnych mieszalników chcesz rozbić produkcję tych {current_skus} SKUs?",
                min_value=1, max_value=int(current_skus), value=min(int(st.session_state.prod_dict[selected_family_to_edit].get("num_tanks", 1)), int(current_skus)),
                key=f"num_tanks_{selected_family_to_edit}"
            )
        else:
            st.session_state.prod_dict[selected_family_to_edit]["num_tanks"] = 1

        tanks_count_now = st.session_state.prod_dict[selected_family_to_edit]["num_tanks"]

        # --- Przypisanie produktów z receptury do konkretnych zbiorników (bez wracania do Excela) ---
        if _has_recipe_products:
            st.markdown("---")
            st.markdown("###### 🔀 Przypisanie Produktów do Zbiorników")
            st.caption("Zmień, do którego zbiornika trafia dany produkt z receptury — np. gdy zbiornik się przeciąża "
                       "i chcesz rozdzielić współdzielone produkty na osobne mieszalniki. Działa od razu, bez "
                       "ponownego wgrywania pliku Excel. (Jeśli chcesz *trwale* zmienić przypisanie na przyszłość, "
                       "warto też poprawić 'ID Zbiornika' w źródłowym pliku — inaczej kolejne wgranie receptury "
                       "przywróci oryginalny podział).")

            all_members_flat = [(slot_idx, mem) for slot_idx, slot in enumerate(_tank_members_current) for mem in slot]
            new_assignment = {}
            for slot_idx, mem in all_members_flat:
                target_options = list(range(1, tanks_count_now + 1))
                default_idx = min(slot_idx, tanks_count_now - 1)
                chosen = st.selectbox(
                    f"{mem['product']} → Zbiornik nr:", target_options, index=default_idx,
                    key=f"tank_assign_{selected_family_to_edit}_{mem['product']}"
                )
                new_assignment.setdefault(chosen - 1, []).append(mem)

            rebuilt_members = [new_assignment.get(i, []) for i in range(tanks_count_now)]
            st.session_state.prod_dict[selected_family_to_edit]["tank_members"] = rebuilt_members

            # Pojemności bazowe nowo powstałych/opróżnionych zbiorników - jeśli slot ma produkty
            # z receptury, podpowiedz pojemność jako max ich zadanych wielkości mieszalnika,
            # żeby nie trzeba było ręcznie ustawiać po każdym przeniesieniu.
            tank_volumes_now = st.session_state.prod_dict[selected_family_to_edit].setdefault("tank_volumes", [15.0])
            while len(tank_volumes_now) < tanks_count_now:
                tank_volumes_now.append(15.0)
            del tank_volumes_now[tanks_count_now:]

        # --- Pojemności i cykle poszczególnych zbiorników, gdy linia jest rozbita na kilka mieszalników ---
        # Domyślnie każdy nowy zbiornik dziedziczy wartości bazowe powyżej, ale można je zróżnicować per
        # zbiornik — np. mniejsza szarża o krótszym cyklu dla niskowolumenowego SKU.
        tanks_count_selected = st.session_state.prod_dict[selected_family_to_edit]["num_tanks"]
        base_vol = st.session_state.prod_dict[selected_family_to_edit]["user_vol_m3"]
        base_cycle = st.session_state.prod_dict[selected_family_to_edit]["cycle_h_base"]
        tank_volumes_sel = st.session_state.prod_dict[selected_family_to_edit].setdefault("tank_volumes", [base_vol])
        tank_cycles_sel = st.session_state.prod_dict[selected_family_to_edit].setdefault("tank_cycles", [base_cycle])
        if len(tank_volumes_sel) < tanks_count_selected:
            tank_volumes_sel.extend([base_vol] * (tanks_count_selected - len(tank_volumes_sel)))
        elif len(tank_volumes_sel) > tanks_count_selected:
            del tank_volumes_sel[tanks_count_selected:]
        if len(tank_cycles_sel) < tanks_count_selected:
            tank_cycles_sel.extend([base_cycle] * (tanks_count_selected - len(tank_cycles_sel)))
        elif len(tank_cycles_sel) > tanks_count_selected:
            del tank_cycles_sel[tanks_count_selected:]

        if tanks_count_selected == 1:
            tank_volumes_sel[0] = base_vol  # przy jednym zbiorniku pola bazowe są jedynym źródłem prawdy
            tank_cycles_sel[0] = base_cycle
        else:
            st.markdown("###### 🧪 Pojemności i Cykle Poszczególnych Zbiorników")
            st.caption("Domyślnie każdy zbiornik dziedziczy wartości bazowe powyżej — edytuj poniżej, jeśli zbiorniki różnią się wielkością szarży "
                       "i/lub czasem cyklu (np. mała szarża niszowego SKU z krótszym cyklem vs. duża szarża wysokowolumenowego SKU z dłuższym). "
                       "Roczna produkcja rodziny jest wtedy dzielona między zbiorniki proporcjonalnie do ich pojemności, a nie po równo.")
            cols_tanks = st.columns(min(tanks_count_selected, 4))
            for i in range(tanks_count_selected):
                with cols_tanks[i % len(cols_tanks)]:
                    tank_volumes_sel[i] = st.number_input(
                        f"Zbiornik #{i + 1} — Pojemność [m³]:", min_value=0.5, value=float(tank_volumes_sel[i]), step=0.5,
                        key=f"tankvol_{selected_family_to_edit}_{i}"
                    )
                    tank_cycles_sel[i] = st.number_input(
                        f"Zbiornik #{i + 1} — Cykl [h]:", min_value=0.5, value=float(tank_cycles_sel[i]), step=0.5,
                        key=f"tankcyc_{selected_family_to_edit}_{i}"
                    )

        final_fleet_rows = []
        real_cycle_reference_rows = []
        tag_counter = 101
        st.session_state.tag_to_recipe_product = {}

        for kat in wybrane_kategorie:
            m_annual = st.session_state.prod_dict[kat]["roczna"]
            tanks_count = st.session_state.prod_dict[kat].get("num_tanks", 1)
            base_vol_kat = st.session_state.prod_dict[kat]["user_vol_m3"]
            base_cycle_kat = st.session_state.prod_dict[kat].setdefault("cycle_h_base", st.session_state.active_portfolio[kat]["cycle_h"])

            tank_volumes = st.session_state.prod_dict[kat].setdefault("tank_volumes", [base_vol_kat])
            tank_cycles = st.session_state.prod_dict[kat].setdefault("tank_cycles", [base_cycle_kat])
            if len(tank_volumes) < tanks_count:
                tank_volumes.extend([base_vol_kat] * (tanks_count - len(tank_volumes)))
            elif len(tank_volumes) > tanks_count:
                del tank_volumes[tanks_count:]
            if len(tank_cycles) < tanks_count:
                tank_cycles.extend([base_cycle_kat] * (tanks_count - len(tank_cycles)))
            elif len(tank_cycles) > tanks_count:
                del tank_cycles[tanks_count:]
            if tanks_count == 1:
                tank_volumes[0] = base_vol_kat
                tank_cycles[0] = base_cycle_kat

            rho_product = st.session_state.active_portfolio[kat]["density"]
            total_capacity = sum(tank_volumes)

            for t_idx, v_tank_user in enumerate(tank_volumes):
                cyc_h = tank_cycles[t_idx]
                tank_members_list = st.session_state.prod_dict[kat].get("tank_members", [])
                members = tank_members_list[t_idx] if t_idx < len(tank_members_list) else None

                if members is not None and len(members) > 1:
                    # Zbiornik współdzielony przez kilka produktów (produkcja kampanijna) -
                    # każdy produkt ma WŁASNĄ masę szarży (ta sama pojemność zbiornika, ale
                    # własna gęstość) i własny cykl; sumujemy szarże i faktyczny czas zajętości
                    # zbiornika, zamiast zgadywać jednym uśrednionym cyklem.
                    total_batches, total_hours, mass_per_batch_list = 0, 0.0, []
                    for mem in members:
                        mass_pb_i = v_tank_user * mem["density"] * 1000.0
                        mass_per_batch_list.append(mass_pb_i)
                        monthly_i = mem["annual_kg"] / MONTHS_PER_YEAR
                        batches_i = math.ceil(monthly_i / mass_pb_i) if mass_pb_i > 0 else 0
                        total_batches += batches_i
                        total_hours += batches_i * mem["cycle_h"]
                    batches_per_tank = total_batches
                    mass_per_batch = max(mass_per_batch_list) if mass_per_batch_list else 0.0
                    real_utilization = (total_hours / AVAILABLE_HOURS_MONTH * 100.0) if AVAILABLE_HOURS_MONTH > 0 else 0.0
                elif members is not None and len(members) == 1:
                    # Zbiornik dedykowany DOKŁADNIE jednemu produktowi z receptury - liczymy
                    # wprost z jego własnych danych (gęstość/roczna/cykl), bez zgadywania przez
                    # podział proporcjonalny do pojemności (mamy dokładne dane, więc ich używamy).
                    mem = members[0]
                    mass_per_batch = v_tank_user * mem["density"] * 1000.0
                    monthly_mass = mem["annual_kg"] / MONTHS_PER_YEAR
                    batches_per_tank = math.ceil(monthly_mass / mass_per_batch) if mass_per_batch > 0 else 0
                    real_utilization = (batches_per_tank * mem["cycle_h"]) / AVAILABLE_HOURS_MONTH * 100.0 if AVAILABLE_HOURS_MONTH > 0 else 0.0
                elif members is not None and len(members) == 0:
                    # Zbiornik jawnie opróżniony (przeniesiono z niego wszystkie produkty w
                    # panelu przypisania powyżej) - nic w nim nie produkujemy.
                    mass_per_batch, batches_per_tank, real_utilization = 0.0, 0, 0.0
                else:
                    # Zbiornik niepowiązany z recepturą (dodany ręcznie, tryb w pełni manualny) —
                    # podział rocznej produkcji rodziny między zbiorniki PROPORCJONALNIE do ich
                    # pojemności, jeśli zbiorniki mają różne wielkości, większy zbiornik przejmuje
                    # większą część wolumenu zamiast wymuszania tej samej liczby szarż co na małym.
                    capacity_share = (v_tank_user / total_capacity) if total_capacity > 0 else (1.0 / tanks_count)
                    annual_per_tank = m_annual * capacity_share
                    monthly_per_tank = annual_per_tank / MONTHS_PER_YEAR

                    mass_per_batch = v_tank_user * rho_product * 1000.0
                    batches_per_tank = math.ceil(monthly_per_tank / mass_per_batch) if mass_per_batch > 0 else 0
                    real_utilization = (batches_per_tank * cyc_h) / AVAILABLE_HOURS_MONTH * 100.0 if AVAILABLE_HOURS_MONTH > 0 else 0.0

                tag_id = f"MT-{tag_counter}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                if members is not None and len(members) == 1:
                    st.session_state.tag_to_recipe_product[tag_id] = members[0]["product"]
                status_txt = "🟢 Optymalna" if real_utilization <= MAX_TANK_UTILIZATION_PCT else "⚠️ Przeciążenie (>85%)"
                if v_tank_user < MIN_TANK_VOLUME_M3:
                    status_txt = "❌ Poniżej min. fabryki (<5 m³)"

                # Rzeczywisty, policzony czas cyklu (dozowanie+grzanie+homog.+pompowanie+chłodzenie) z
                # Zakładki 2/6 — pokazywany OSOBNO poniżej (nie w tej samej edytowalnej tabeli!), bo ta
                # wartość zmienia się za każdym razem, gdy cokolwiek zostanie skonfigurowane na INNEJ
                # zakładce. Trzymanie jej w tej samej tabeli co edytowalna flota powodowało, że
                # st.data_editor dostawał na każdym przebiegu inną zawartość i potrafił zresetować
                # ręczne zmiany użytkownika (np. usunięte wiersze) — stąd "niekontrolowane odświeżanie".
                real_cycle_txt = "—"
                ct = st.session_state.calculated_times.get(tag_id)
                bt = st.session_state.batch_time_components.get(tag_id)
                if ct is not None:
                    real_cycle_h = ct.get("heating", 0.0) + ct.get("pumping", 0.0) + ct.get("cooling_h", 0.0)
                    if bt is not None:
                        real_cycle_h += bt.get("dosing", 0.0) + bt.get("homog", 0.0)
                    real_cycle_txt = f"{real_cycle_h:.2f}"
                real_cycle_reference_rows.append({
                    "ID Urządzenia": tag_id, "Linia": kat,
                    "Cykl Szacowany [h]": round(cyc_h, 2), "Cykl Rzeczywisty [h]": real_cycle_txt,
                })

                if members and len(members) > 1:
                    produkty_txt = f"{len(members)} produktów (współdzielony)"
                elif members and len(members) == 1:
                    produkty_txt = members[0]["product"]
                else:
                    produkty_txt = "—"

                final_fleet_rows.append({
                    "ID Urządzenia": tag_id,
                    "Przypisana Linia": kat,
                    "Produkty": produkty_txt,
                    "Pojemność [m³]": round(v_tank_user, 1),
                    "Masa Szarży [kg]": int(mass_per_batch),
                    "Cykl Szacowany [h]": round(cyc_h, 2),
                    "Szarż / miesiąc (per aparat)": int(batches_per_tank),
                    "Utylizacja Czasowa": f"{real_utilization:.1f}%",
                    "Status": status_txt
                })

            tag_counter += 1

        st.markdown("### 📊 Aktualne Zestawienie Floty Produkcyjnej (Możesz usuwać wiersze)")
        st.caption("💡 **Instrukcja:** Aby usunąć zbiornik, zaznacz pole wyboru po lewej stronie wiersza i naciśnij `Delete` na klawiaturze (lub użyj ikony kosza). "
                    "Kolumnę **Przypisana Linia** można edytować tylko na wartości z aktywnie wybranych linii produktowych - inne wartości zostaną odrzucone przy zatwierdzaniu. "
                    "**Pojemność, Masa Szarży, Cykl, Szarże i Utylizacja są tylko do odczytu** w tej tabeli - to są wyliczone wartości; żeby je zmienić, edytuj pola "
                    "'Pojemność Mieszalnika (bazowa)' / 'Zbiornik #N — Pojemność/Cykl' powyżej. Jeśli chcesz rozdzielić produkty ze **wspólnego zbiornika** "
                    "(receptura ze wspólnym ID Zbiornika) na osobne fizyczne mieszalniki, zrób to w pliku Excel (usuń/zmień ID Zbiornika dla jednego z produktów) "
                    "i wgraj recepturę ponownie w Zakładce 1 - samo zwiększenie liczby zbiorników tutaj dodaje pusty zbiornik, ale nie wie, który produkt ma do niego przenieść.")

        df_fleet = pd.DataFrame(final_fleet_rows)

        # Klucz data_editora zależy od parametrów, które faktycznie napędzają flotę (roczna
        # produkcja, pojemności/cykle bazowe i per-zbiornik, liczba zbiorników) - dzięki temu
        # KAŻDA zmiana tych wartości (np. pojemności bazowej w Kroku A) wymusza pełne
        # odświeżenie tabeli, zamiast pozwalać Streamlitowi zatrzymać nieaktualny stan komórek
        # z poprzedniego przebiegu. Między takimi zmianami klucz jest stabilny, więc ręczne
        # usuwanie wierszy w tabeli nadal działa normalnie do czasu kliknięcia "Zatwierdź".
        fleet_signature = hash(tuple(
            (kat, st.session_state.prod_dict[kat]["roczna"], st.session_state.prod_dict[kat]["user_vol_m3"],
             st.session_state.prod_dict[kat].get("num_tanks", 1),
             tuple(st.session_state.prod_dict[kat].get("tank_volumes", [])),
             tuple(st.session_state.prod_dict[kat].get("tank_cycles", [])))
            for kat in wybrane_kategorie
        ))

        edited_df = st.data_editor(
            df_fleet,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key=f"fleet_data_editor_v4_{fleet_signature}",
            disabled=["ID Urządzenia", "Produkty", "Pojemność [m³]", "Masa Szarży [kg]",
                      "Cykl Szacowany [h]", "Szarż / miesiąc (per aparat)", "Utylizacja Czasowa", "Status"]
        )

        if real_cycle_reference_rows:
            with st.expander("📊 Rzeczywisty czas cyklu (referencja z Zakładki 2/6 — informacyjnie, nieedytowalne)", expanded=False):
                st.caption("Ta tabela aktualizuje się automatycznie w miarę konfigurowania hydrauliki/bilansu cieplnego (Zakładka 3) "
                           "i dozowania/homogenizacji (Zakładka 7) — nie wpływa na flotę powyżej i nie da się jej edytować.")
                st.dataframe(pd.DataFrame(real_cycle_reference_rows), hide_index=True, use_container_width=True)

        if not edited_df.empty:
            total_annual_production_edited = sum(st.session_state.prod_dict[kat]["roczna"] for kat in wybrane_kategorie)
            total_batches_edited = pd.to_numeric(edited_df["Szarż / miesiąc (per aparat)"], errors="coerce").fillna(0).astype(int).sum()
            total_volume_edited = pd.to_numeric(edited_df["Pojemność [m³]"], errors="coerce").fillna(0.0).astype(float).sum()
        else:
            total_annual_production_edited = 0
            total_batches_edited = 0
            total_volume_edited = 0.0

        st.markdown("<br>", unsafe_allow_html=True)
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1: st.metric(label="📈 Sumaryczny tonaż roczny zakładu", value=f"{total_annual_production_edited:,} kg")
        with sum_col2: st.metric(label="🔄 Suma szarż floty / miesiąc", value=f"{total_batches_edited} szarż")
        with sum_col3: st.metric(label="📐 Całkowita kubatura floty", value=f"{total_volume_edited:.1f} m³")

        st.markdown("---")

        if st.button("📥 Zatwierdź i wyślij konfigurację do kolejnych kroków", type="primary", use_container_width=True, key="btn_zatwierdz_flote_v3"):
            if edited_df.empty:
                st.error("❌ Flota nie może być pusta!")
            else:
                # Walidacja wierszy dodanych/edytowanych ręcznie w data_editor, aby uniknąć
                # KeyError przy próbie odczytu nieistniejącej linii z st.session_state.active_portfolio.
                invalid_rows = edited_df[~edited_df["Przypisana Linia"].isin(st.session_state.active_portfolio.keys())]
                numeric_cols = ["Pojemność [m³]", "Masa Szarży [kg]", "Cykl Szacowany [h]", "Szarż / miesiąc (per aparat)"]
                bad_numeric = edited_df[numeric_cols].apply(pd.to_numeric, errors="coerce").isna().any(axis=1)

                if not invalid_rows.empty:
                    zle_linie = sorted(set(invalid_rows["Przypisana Linia"].astype(str)))
                    st.error(f"❌ Wiersze wskazują na nieznane linie produktowe: {', '.join(zle_linie)}. "
                             f"Popraw kolumnę 'Przypisana Linia' na jedną z aktywnie wybranych linii i spróbuj ponownie.")
                elif bad_numeric.any():
                    st.error("❌ Niektóre wiersze zawierają niepoprawne (nienumeryczne) wartości w kolumnach liczbowych. Popraw dane i spróbuj ponownie.")
                else:
                    confirmed_mixers_blueprint = []
                    for _, row in edited_df.iterrows():
                        kat = row["Przypisana Linia"]
                        confirmed_mixers_blueprint.append({
                            "tag": row["ID Urządzenia"],
                            "product_family": kat,
                            "capacity_m3": float(row["Pojemność [m³]"]),
                            "material": st.session_state.active_portfolio[kat]["material"],
                            "batches_count": int(row["Szarż / miesiąc (per aparat)"]),
                            "mass_per_batch": int(row["Masa Szarży [kg]"]),
                            "cycle_h": float(row["Cykl Szacowany [h]"]),
                            "annual_volume": int(row["Masa Szarży [kg]"]) * int(row["Szarż / miesiąc (per aparat)"]) * MONTHS_PER_YEAR,
                            "recipe_product": st.session_state.tag_to_recipe_product.get(row["ID Urządzenia"]),
                        })

                    st.session_state.confirmed_mixers = confirmed_mixers_blueprint
                    st.success(f"🎉 Zapisano strukturę floty ({len(confirmed_mixers_blueprint)} urządzeń).")
    else:
        st.info("💡 Wybierz co najmniej jedną linię produktową w panelu bocznym, aby rozpocząć.")

    # ==========================================
    # SYMULACJA ROZRUCHU (RAMPUP) — flota budowana od razu pod cel, ale wykorzystanie
    # rośnie w czasie. Ta sama krzywa % jest reużywana w Zakładce 4 (magazyn FG+RM), żeby
    # historia "startujemy nisko, dochodzimy do celu" była spójna w całej aplikacji.
    # ==========================================
    if st.session_state.confirmed_mixers:
        st.markdown("---")
        with st.expander("📈 Symulacja Rozruchu (Rampup) — 5 lat", expanded=False):
            st.caption("Flota i magazyn (Zakładka 4) są wymiarowane od razu pod docelową produkcję wpisaną powyżej — "
                       "to buduje się raz. Poniższa krzywa pokazuje/symuluje, jak realnie rośnie WYKORZYSTANIE tej "
                       "floty i magazynu w pierwszych 5 latach, zanim produkcja dojdzie do 100% celu.")

            st.session_state.rampup_differentiate = st.checkbox(
                "🔧 Zróżnicuj tempo rozruchu per linia produktowa", value=st.session_state.rampup_differentiate,
                help="Domyślnie jedna wspólna krzywa dla całej fabryki. Włącz, jeśli np. Engine Oils ma ruszyć "
                     "szybciej niż Greases."
            )

            year_labels = [f"Rok {i+1}" for i in range(RAMPUP_YEARS)]

            if not st.session_state.rampup_differentiate:
                st.markdown("###### Wspólna krzywa dla całej fabryki")
                cols_ramp = st.columns(RAMPUP_YEARS)
                for i, c in enumerate(cols_ramp):
                    with c:
                        st.session_state.rampup_global_pct[i] = st.number_input(
                            f"{year_labels[i]} [%]", min_value=0.0, max_value=100.0,
                            value=float(st.session_state.rampup_global_pct[i]), step=5.0, key=f"rampup_global_{i}"
                        )
            else:
                st.markdown("###### Krzywa per linia produktowa")
                for kat in wybrane_kategorie:
                    st.session_state.rampup_per_line_pct.setdefault(kat, list(st.session_state.rampup_global_pct))
                    st.markdown(f"**{kat}**")
                    cols_ramp = st.columns(RAMPUP_YEARS)
                    for i, c in enumerate(cols_ramp):
                        with c:
                            st.session_state.rampup_per_line_pct[kat][i] = st.number_input(
                                f"{year_labels[i]} [%]", min_value=0.0, max_value=100.0,
                                value=float(st.session_state.rampup_per_line_pct[kat][i]), step=5.0,
                                key=f"rampup_line_{kat}_{i}"
                            )

            # --- Przeliczenie: tonaż roczny i średnia utylizacja floty per rok symulacji ---
            target_annual_t = sum(m["annual_volume"] for m in st.session_state.confirmed_mixers) / 1000.0
            rampup_summary_rows = []
            rampup_tonnage_chart = {"Rok": [], "Tonaż [t/rok]": [], "Cel [t/rok]": []}
            for i in range(RAMPUP_YEARS):
                year_tonnage_t = 0.0
                util_weighted, util_weight_sum = 0.0, 0.0
                util_ciagla_weighted = 0.0
                for m in st.session_state.confirmed_mixers:
                    frac = get_rampup_fraction(m["product_family"], i)
                    year_tonnage_t += (m["annual_volume"] / 1000.0) * frac

                    scaled_monthly_mass = (m["annual_volume"] / MONTHS_PER_YEAR) * frac
                    scaled_batches = math.ceil(scaled_monthly_mass / m["mass_per_batch"]) if m["mass_per_batch"] > 0 else 0
                    scaled_util_pct = (scaled_batches * m["cycle_h"]) / AVAILABLE_HOURS_MONTH * 100.0 if AVAILABLE_HOURS_MONTH > 0 else 0.0
                    util_weighted += scaled_util_pct * m["capacity_m3"]
                    util_weight_sum += m["capacity_m3"]

                    # Wariant ciągły (bez zaokrąglania w górę do pełnych szarż) - czysto
                    # diagnostyczny, żeby pokazać płynny trend rosnącego zapotrzebowania nawet
                    # gdy realna (całkowita) liczba szarż jeszcze się nie zmienia między latami.
                    scaled_batches_ciagle = scaled_monthly_mass / m["mass_per_batch"] if m["mass_per_batch"] > 0 else 0.0
                    scaled_util_pct_ciagly = (scaled_batches_ciagle * m["cycle_h"]) / AVAILABLE_HOURS_MONTH * 100.0 if AVAILABLE_HOURS_MONTH > 0 else 0.0
                    util_ciagla_weighted += scaled_util_pct_ciagly * m["capacity_m3"]

                avg_util_pct = (util_weighted / util_weight_sum) if util_weight_sum > 0 else 0.0
                avg_util_ciagly_pct = (util_ciagla_weighted / util_weight_sum) if util_weight_sum > 0 else 0.0
                rampup_summary_rows.append({
                    "Rok": year_labels[i], "Tonaż [t/rok]": round(year_tonnage_t, 0),
                    "% Celu": f"{(year_tonnage_t / target_annual_t * 100.0) if target_annual_t > 0 else 0:.0f}%",
                    "Śr. Utylizacja Floty [%] (pełne szarże)": round(avg_util_pct, 1),
                    "Śr. Utylizacja Floty [%] (ciągła)": round(avg_util_ciagly_pct, 1),
                })
                rampup_tonnage_chart["Rok"].append(year_labels[i])
                rampup_tonnage_chart["Tonaż [t/rok]"].append(year_tonnage_t)
                rampup_tonnage_chart["Cel [t/rok]"].append(target_annual_t)

            chart_df = pd.DataFrame(rampup_tonnage_chart).set_index("Rok")
            st.line_chart(chart_df)
            st.dataframe(pd.DataFrame(rampup_summary_rows), hide_index=True, use_container_width=True)
            st.caption("ℹ️ **Pełne szarże** — realna liczba szarż zaokrąglona w górę do liczb całkowitych (tak faktycznie "
                       "planuje się produkcję); może być identyczna w sąsiednich latach, jeśli wzrost popytu nie "
                       "przekroczył jeszcze progu kolejnej pełnej szarży na wystarczającej liczbie mieszalników. "
                       "**Ciągła** — ta sama utylizacja bez zaokrąglania, czysto diagnostyczna: pokazuje płynny trend "
                       "rosnącego zapotrzebowania nawet między takimi progami.")
            st.caption(f"🎯 Docelowa produkcja (100%, jak wymiarowana jest flota): **{target_annual_t:,.0f} t/rok**. "
                       "Ta sama krzywa steruje wykorzystaniem magazynu w Zakładce 4 (wybór roku symulacji).")

# ==========================================
# ZAKŁADKA 2: KARTA MASZYN, HYDRAULIKA, MIESZANIE I BILANS CIEPLNY
# ==========================================
with tab2:
    st.header("Karta Maszyn: Zaawansowane Projektowanie Procesowe")

    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych o flocie. Skonfiguruj i zatwierdź flotę w Zakładce 2, aby odblokować ten krok.")
    else:
        summary_combined_rows = []

        # --- KROK 1: Inicjalizacja domyślnych parametrów (bez widgetów) dla każdego urządzenia ---
        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            kat = mixer["product_family"]

            if m_id not in st.session_state.mixer_tech_advanced_details:
                st.session_state.mixer_tech_advanced_details[m_id] = {}

            p = st.session_state.mixer_tech_advanced_details[m_id]

            defaults = {
                "pump_flow_m3h": 15.0,
                "pipe_dn": 80,
                "pipe_length_m": 25.0,
                "delta_h_m": 5.0,
                "viscosity_min_cst": 30.0,
                "viscosity_max_cst": 300.0,
                "density_kg_m3": st.session_state.active_portfolio[kat]["density"] * 1000.0,
                "count_elbows_90": 4,
                "count_tees": 2,
                "count_valves": 3,
                "pump_efficiency": 0.65,
                "cp_product": 2.10,
                "t_product_in": 20.0,
                "t_product_out": 70.0,
                "k_coeff_grzania": 450.0,
                "tank_mass": 1200.0,
                "cp_steel": 0.46,
                "t_discharge_c": 30.0,
                "exchange_area_m2": 4.5,
                "delta_t_medium_grzewcze": 10.0,
                "delta_t_medium_chlodzace": 6.0,
                "utility_type_heat": "Woda technologiczna",
                "utility_type_cool": "Woda technologiczna",
                "t_utility_heat_in": 95.0,
                "t_utility_cool_in": 12.0,
                "k_coeff": 350.0,
                "agitator_type": "Turbinowe (Rushton)",
                "agitator_rpm": 90.0,
                "agitator_diameter_m": 0.6,
                "pump_mode": "Dedykowana (dla tego zbiornika)",
                "shared_pump_id": "",
                "pump_mtbf_h": 2000.0,
                "pump_mttr_h": 8.0,
                "reactor_mtbf_h": 4000.0,
                "reactor_mttr_h": 12.0,
            }
            for key, val in defaults.items():
                if key not in p:
                    p[key] = val

        # --- KROK 2: Parametryzatory (widgety) — MUSZĄ wykonać się PRZED przeliczeniem poniżej. ---
        # POPRAWKA: wcześniej te widgety renderowały się PO pętli obliczeniowej, więc każda
        # zmiana wartości (np. DN rury) była widoczna w tabeli zbiorczej dopiero po KOLEJNEJ
        # interakcji — do tego czasu tabela pokazywała wynik dla poprzedniej wartości. Stąd
        # pozornie "odwrócona" fizyka (większe DN pokazujące większą prędkość) — to był efekt
        # przestarzałych danych, nie błąd wzoru.
        st.markdown("### ⚙️ Parametryzatory Szczegółowe Maszyn i Mediów")

        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            kat = mixer["product_family"]
            p = st.session_state.mixer_tech_advanced_details[m_id]

            with st.expander(f"🛠️ Konfiguracja hydrauliki, mieszania i bilansu energii: {m_id}", expanded=False):
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    st.markdown("**🌊 Średnice, Przepływ i Reologia**")
                    p["pump_mode"] = st.selectbox(
                        "Tryb pompy:", ["Dedykowana (dla tego zbiornika)", "Współdzielona (kilka zbiorników)"],
                        index=["Dedykowana (dla tego zbiornika)", "Współdzielona (kilka zbiorników)"].index(p["pump_mode"]),
                        key=f"pump_mode_{m_id}",
                        help="Jedna fizyczna pompa może obsługiwać kilka zbiorników na przemian — wybierz "
                             "'Współdzielona' i podaj ten sam ID pompy dla wszystkich zbiorników, które ją dzielą. "
                             "Przepływ, sprawność, MTBF i MTTR takiej pompy edytujesz wtedy raz, w tabeli "
                             "'Pompy Współdzielone' poniżej listy urządzeń — obowiązują dla wszystkich zbiorników z tym ID."
                    )
                    if p["pump_mode"] == "Współdzielona (kilka zbiorników)":
                        p["shared_pump_id"] = st.text_input(
                            "ID pompy współdzielonej:", value=p["shared_pump_id"] or "P-01", key=f"shared_pump_id_{m_id}"
                        )
                        st.caption("Przepływ pompy [m³/h], sprawność, MTBF i MTTR dla tej pompy skonfigurujesz w tabeli "
                                   "'🔧 Pompy Współdzielone' poniżej — tu jedynie przypisujesz zbiornik do pompy.")
                    else:
                        p["shared_pump_id"] = ""
                        p["pump_flow_m3h"] = st.number_input(f"Przepływ pompy [m³/h]:", min_value=1.0, value=float(p["pump_flow_m3h"]), key=f"q_adv_{m_id}")
                    p["pipe_dn"] = st.number_input(f"Średnica rury [DN]:", min_value=15, value=int(p["pipe_dn"]), key=f"dn_adv_{m_id}")
                    p["viscosity_min_cst"] = st.number_input(f"Lepkość MIN [cSt]:", min_value=0.5, value=float(p["viscosity_min_cst"]), key=f"v_min_{m_id}")
                    p["viscosity_max_cst"] = st.number_input(f"Lepkość MAX [cSt]:", min_value=1.0, value=float(p["viscosity_max_cst"]), key=f"v_max_{m_id}")
                with c2:
                    st.markdown("**📐 Geometria Rurociągu**")
                    p["pipe_length_m"] = st.number_input(f"Długość rury L [m]:", min_value=0.1, value=float(p["pipe_length_m"]), key=f"l_len_{m_id}")
                    p["delta_h_m"] = st.number_input(f"Różnica wysokości Δh [m]:", min_value=0.0, value=float(p["delta_h_m"]), key=f"h_delta_{m_id}")
                    p["count_elbows_90"] = st.number_input(f"Liczba kolan 90°:", min_value=0, value=int(p["count_elbows_90"]), key=f"elb_{m_id}")
                    p["count_valves"] = st.number_input(f"Liczba zaworów:", min_value=0, value=int(p["count_valves"]), key=f"val_{m_id}")
                with c3:
                    st.markdown("**🌀 Mieszadło**")
                    p["agitator_type"] = st.selectbox("Typ mieszadła:", list(AGITATOR_TYPES.keys()),
                                                        index=list(AGITATOR_TYPES.keys()).index(p["agitator_type"]), key=f"ag_type_{m_id}")
                    p["agitator_rpm"] = st.number_input("Prędkość obrotowa [obr/min]:", min_value=1.0, value=float(p["agitator_rpm"]), key=f"ag_rpm_{m_id}")
                    p["agitator_diameter_m"] = st.number_input("Średnica mieszadła [m]:", min_value=0.05, value=float(p["agitator_diameter_m"]), key=f"ag_d_{m_id}")
                with c4:
                    st.markdown("**🔥 Wymiennik Ciepła i Nośniki Energii**")
                    p["utility_type_heat"] = st.selectbox(f"Medium grzewcze:", list(MEDIA_PROCESOWE.keys()), index=list(MEDIA_PROCESOWE.keys()).index(p["utility_type_heat"]), key=f"ut_h_type_{m_id}")
                    p["t_utility_heat_in"] = st.number_input(f"Temp. zasilania medium grzewczego [°C]:", value=float(p["t_utility_heat_in"]), key=f"t_ut_h_{m_id}")
                    if MEDIA_PROCESOWE[p["utility_type_heat"]].get("steam"):
                        st.caption("ℹ️ Para nasycona: bilans liczony przez ciepło skraplania, nie cp·ΔT. Poniższe ΔT medium grzewczego nie dotyczy pary.")
                    p["k_coeff_grzania"] = st.number_input(f"Współczynnik przenikania ciepła — grzanie k [W/m²K]:", min_value=1.0, value=float(p["k_coeff_grzania"]), key=f"k_grz_{m_id}")
                    p["delta_t_medium_grzewcze"] = st.number_input(
                        f"ΔT medium grzewczego (projektowy spadek) [K]:", min_value=1.0, value=float(p["delta_t_medium_grzewcze"]), key=f"dt_med_grz_{m_id}",
                        help="Ile stopni medium grzewcze traci przechodząc przez wymiennik — z tego i mocy grzania wyliczany jest wymagany przepływ."
                    )
                    p["utility_type_cool"] = st.selectbox(f"Medium chłodzące:", list(MEDIA_PROCESOWE.keys()), index=list(MEDIA_PROCESOWE.keys()).index(p["utility_type_cool"]), key=f"ut_c_type_{m_id}")
                    p["t_utility_cool_in"] = st.number_input(f"Temp. wody chłodzącej [°C]:", value=float(p["t_utility_cool_in"]), key=f"t_ut_c_{m_id}")
                    p["k_coeff"] = st.number_input(f"Współczynnik przenikania ciepła — chłodzenie k [W/m²K]:", min_value=1.0, value=float(p["k_coeff"]), key=f"k_chl_{m_id}")
                    p["delta_t_medium_chlodzace"] = st.number_input(
                        f"ΔT medium chłodzącego (projektowy wzrost) [K]:", min_value=1.0, value=float(p["delta_t_medium_chlodzace"]), key=f"dt_med_chl_{m_id}",
                        help="O ile stopni ogrzewa się chłodziwo przechodząc przez wymiennik — z tego i mocy chłodzenia wyliczany jest wymagany przepływ."
                    )
                    p["exchange_area_m2"] = st.number_input(f"Powierzchnia wymiany (wspólny płaszcz) [m²]:", min_value=0.1, value=float(p["exchange_area_m2"]), key=f"area_{m_id}")
                    p["t_product_in"] = st.number_input(f"Temp. początkowa płynu [°C]:", value=float(p["t_product_in"]), key=f"tpin_adv_{m_id}")
                    p["t_product_out"] = st.number_input(f"Temp. procesu (gorący) [°C]:", value=float(p["t_product_out"]), key=f"tpout_adv_{m_id}")
                    p["t_discharge_c"] = st.number_input(f"Temp. rozlewu (docelowa) [°C]:", value=float(p["t_discharge_c"]), key=f"tdisc_{m_id}")
                    st.caption("ℹ️ Czas grzania nie jest już wpisywany ręcznie — jest wyliczany z mocy grzania "
                               "(k × A × ΔT) i wymaganej energii, tak samo jak czas chłodzenia. Przepływy obu mediów są "
                               "teraz również wyliczane, nie zgadywane.")
                with c5:
                    st.markdown("**🔧 Niezawodność (MTBF/MTTR)**")
                    st.caption("Zasila automatycznie 'Dostępność [%]' w Zakładce 7 (VSM/OEE) — patrz przycisk "
                               "'Zastosuj wyliczoną Dostępność' w tamtej zakładce.")
                    p["reactor_mtbf_h"] = st.number_input(
                        "MTBF reaktora/mieszadła [h]:", min_value=1.0, value=float(p["reactor_mtbf_h"]), key=f"reactor_mtbf_{m_id}",
                        help="Średni czas między awariami samego zbiornika/mieszadła (bez pompy)."
                    )
                    p["reactor_mttr_h"] = st.number_input(
                        "MTTR reaktora/mieszadła [h]:", min_value=0.1, value=float(p["reactor_mttr_h"]), key=f"reactor_mttr_{m_id}",
                        help="Średni czas naprawy/usunięcia awarii zbiornika/mieszadła."
                    )
                    if p["pump_mode"] == "Dedykowana (dla tego zbiornika)":
                        p["pump_mtbf_h"] = st.number_input(
                            "MTBF pompy [h]:", min_value=1.0, value=float(p["pump_mtbf_h"]), key=f"pump_mtbf_{m_id}"
                        )
                        p["pump_mttr_h"] = st.number_input(
                            "MTTR pompy [h]:", min_value=0.1, value=float(p["pump_mttr_h"]), key=f"pump_mttr_{m_id}"
                        )
                        avail_pump_preview = p["pump_mtbf_h"] / (p["pump_mtbf_h"] + p["pump_mttr_h"]) * 100.0
                    else:
                        shared = st.session_state.shared_pumps.get(p["shared_pump_id"], {})
                        pump_mtbf_disp = shared.get("mtbf_h", 2000.0)
                        pump_mttr_disp = shared.get("mttr_h", 8.0)
                        st.caption(f"Pompa '{p['shared_pump_id']}': MTBF {pump_mtbf_disp:.0f} h / MTTR {pump_mttr_disp:.1f} h "
                                   f"(edytuj w tabeli 'Pompy Współdzielone' poniżej).")
                        avail_pump_preview = pump_mtbf_disp / (pump_mtbf_disp + pump_mttr_disp) * 100.0
                    avail_reactor_preview = p["reactor_mtbf_h"] / (p["reactor_mtbf_h"] + p["reactor_mttr_h"]) * 100.0
                    avail_combined_preview = (avail_pump_preview / 100.0) * (avail_reactor_preview / 100.0) * 100.0
                    st.metric("Dostępność łączna (reaktor × pompa)", f"{avail_combined_preview:.1f}%")

                st.markdown("---")
                st.markdown("**🌫️ Typ Procesu i Bilans Pary (dla smarów/waxów)**")
                p.setdefault("process_type", "Ciecz (mieszanie/blending)")
                p["process_type"] = st.selectbox(
                    "Typ procesu:", ["Ciecz (mieszanie/blending)", "Smar/Wax (gotowanie z odparowaniem)"],
                    index=["Ciecz (mieszanie/blending)", "Smar/Wax (gotowanie z odparowaniem)"].index(p["process_type"]),
                    key=f"proc_type_{m_id}",
                    help="Wybierz 'Smar/Wax', jeśli ten reaktor gotuje z intensywnym odparowaniem (np. zmydlanie) "
                         "i wymaga bilansu linii zrzutu pary — poniżej pojawią się dodatkowe pola, a zbiorczy "
                         "rurociąg zrzutowy policzy się niżej, dla wszystkich reaktorów tego typu naraz."
                )
                if p["process_type"] == "Smar/Wax (gotowanie z odparowaniem)":
                    p.setdefault("steam_avg_flow", 0.0185)
                    p.setdefault("steam_max_process", 0.037)
                    p.setdefault("steam_max_decompress", 0.089)
                    cs1, cs2, cs3 = st.columns(3)
                    with cs1:
                        p["steam_avg_flow"] = st.number_input("Średni strumień odwadniania [kg/s]:", min_value=0.0, value=float(p["steam_avg_flow"]), step=0.001, format="%.4f", key=f"steam_avg_{m_id}")
                    with cs2:
                        p["steam_max_process"] = st.number_input("Maks. strumień procesowy [kg/s]:", min_value=0.0, value=float(p["steam_max_process"]), step=0.001, format="%.4f", key=f"steam_proc_{m_id}")
                    with cs3:
                        p["steam_max_decompress"] = st.number_input("Maks. strumień dekompresji [kg/s]:", min_value=0.0, value=float(p["steam_max_decompress"]), step=0.001, format="%.4f", key=f"steam_decomp_{m_id}")

        # --- Pompy współdzielone: jedno miejsce edycji przepływu/sprawności/MTBF/MTTR, ---
        # wspólne dla wszystkich zbiorników, które przypisano do tej samej pompy powyżej.
        shared_pump_ids_in_use = sorted(set(
            st.session_state.mixer_tech_advanced_details[m["tag"]]["shared_pump_id"]
            for m in st.session_state.confirmed_mixers
            if st.session_state.mixer_tech_advanced_details.get(m["tag"], {}).get("pump_mode") == "Współdzielona (kilka zbiorników)"
            and st.session_state.mixer_tech_advanced_details[m["tag"]]["shared_pump_id"]
        ))

        if shared_pump_ids_in_use:
            st.markdown("### 🔧 Pompy Współdzielone — Przepływ, Sprawność, MTBF/MTTR")
            st.caption("Jeden wiersz = jedna fizyczna pompa obsługująca kilka zbiorników na przemian. Zmiana tutaj "
                       "dotyczy od razu wszystkich zbiorników przypisanych do tej pompy powyżej.")
            for pid in shared_pump_ids_in_use:
                st.session_state.shared_pumps.setdefault(pid, {
                    "flow_m3h": 15.0, "efficiency": 0.65, "mtbf_h": 2000.0, "mttr_h": 8.0,
                })

            shared_pump_rows = [
                {"ID Pompy": pid, "Przepływ [m³/h]": cfg["flow_m3h"], "Sprawność [-]": cfg["efficiency"],
                 "MTBF [h]": cfg["mtbf_h"], "MTTR [h]": cfg["mttr_h"],
                 "Zbiorniki": ", ".join(m["tag"] for m in st.session_state.confirmed_mixers
                                        if st.session_state.mixer_tech_advanced_details.get(m["tag"], {}).get("shared_pump_id") == pid)}
                for pid, cfg in st.session_state.shared_pumps.items() if pid in shared_pump_ids_in_use
            ]
            edited_shared_pumps = st.data_editor(
                pd.DataFrame(shared_pump_rows), hide_index=True, use_container_width=True,
                disabled=["ID Pompy", "Zbiorniki"], key="shared_pumps_editor"
            )
            for _, row in edited_shared_pumps.iterrows():
                st.session_state.shared_pumps[row["ID Pompy"]] = {
                    "flow_m3h": float(row["Przepływ [m³/h]"]), "efficiency": float(row["Sprawność [-]"]),
                    "mtbf_h": float(row["MTBF [h]"]), "mttr_h": float(row["MTTR [h]"]),
                }

        st.markdown("---")

        # --- KROK 3: Przeliczenie hydrauliki/bilansu cieplnego — TERAZ z aktualnymi wartościami z KROKU 2. ---
        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            kat = mixer["product_family"]
            p = st.session_state.mixer_tech_advanced_details[m_id]

            try:
                # --- 0. Rozwiązanie parametrów pompy (dedykowana vs. współdzielona) i niezawodności ---
                if p["pump_mode"] == "Współdzielona (kilka zbiorników)" and p["shared_pump_id"] in st.session_state.shared_pumps:
                    shared_pump_cfg = st.session_state.shared_pumps[p["shared_pump_id"]]
                    effective_pump_flow_m3h = shared_pump_cfg["flow_m3h"]
                    effective_pump_efficiency = shared_pump_cfg["efficiency"]
                    pump_mtbf_h = shared_pump_cfg["mtbf_h"]
                    pump_mttr_h = shared_pump_cfg["mttr_h"]
                else:
                    effective_pump_flow_m3h = p["pump_flow_m3h"]
                    effective_pump_efficiency = p["pump_efficiency"]
                    pump_mtbf_h = p["pump_mtbf_h"]
                    pump_mttr_h = p["pump_mttr_h"]

                availability_pump_pct = pump_mtbf_h / (pump_mtbf_h + pump_mttr_h) * 100.0 if (pump_mtbf_h + pump_mttr_h) > 0 else 100.0
                availability_reactor_pct = p["reactor_mtbf_h"] / (p["reactor_mtbf_h"] + p["reactor_mttr_h"]) * 100.0 \
                    if (p["reactor_mtbf_h"] + p["reactor_mttr_h"]) > 0 else 100.0
                availability_combined_pct = (availability_pump_pct / 100.0) * (availability_reactor_pct / 100.0) * 100.0

                # --- 1. HYDRAULIKA POMPY (Re / opór / moc), po 3 punktach lepkości ---
                visc_min = p["viscosity_min_cst"]
                visc_max = p["viscosity_max_cst"]
                visc_avg = (visc_min + visc_max) / 2.0

                zeta_sum_calculated = (p["count_elbows_90"] * 0.5) + (p["count_tees"] * 1.5) + (p["count_valves"] * 0.2)

                re_min, p_bar_min, power_kw_min, velocity = compute_hydraulics(
                    effective_pump_flow_m3h, p["pipe_dn"], p["pipe_length_m"], p["delta_h_m"],
                    visc_min, p["density_kg_m3"], zeta_sum_calculated, effective_pump_efficiency)
                re_avg, p_bar_avg, power_kw_avg, _ = compute_hydraulics(
                    effective_pump_flow_m3h, p["pipe_dn"], p["pipe_length_m"], p["delta_h_m"],
                    visc_avg, p["density_kg_m3"], zeta_sum_calculated, effective_pump_efficiency)
                re_max, p_bar_max, power_kw_max, _ = compute_hydraulics(
                    effective_pump_flow_m3h, p["pipe_dn"], p["pipe_length_m"], p["delta_h_m"],
                    visc_max, p["density_kg_m3"], zeta_sum_calculated, effective_pump_efficiency)

                # --- 2. MOC MIESZANIA (dawniej zdefiniowane, ale nigdy nie używane) ---
                re_mix, mix_regime, agitator_power_kw = compute_agitator_power(
                    p["agitator_type"], p["agitator_rpm"], p["agitator_diameter_m"],
                    p["density_kg_m3"], visc_avg)

                # --- 3. BILANS CIEPLNY: GRZANIE (woda/olej sensybilnie, para przez ciepło skraplania) ---
                mass_product = mixer["mass_per_batch"]
                thermal = compute_thermal_balance(
                    mass_product, p["cp_product"], p["t_product_in"], p["t_product_out"],
                    p["k_coeff_grzania"], p["exchange_area_m2"], p["tank_mass"], p["cp_steel"],
                    p["utility_type_heat"], p["delta_t_medium_grzewcze"], p["t_utility_heat_in"])

                # --- 4. CHŁODZENIE DO ROZLEWU ---
                q_cooling_mj, cooling_power_kw, cooling_time_h, flow_cooling_kg_h, cooling_status = compute_cooling(
                    mass_product, p["cp_product"], p["t_product_out"], p["t_discharge_c"],
                    p["t_utility_cool_in"], p["k_coeff"], p["exchange_area_m2"],
                    p["utility_type_cool"], p["delta_t_medium_chlodzace"])

                # --- 5. Zapis wyników z powrotem do stanu sesji, aby Zakładka 4 mogła z nich realnie korzystać ---
                # Czas pompowania: objętość szarży / wydajność pompy.
                pumping_time_h = (mass_product / p["density_kg_m3"]) / effective_pump_flow_m3h if effective_pump_flow_m3h > 0 else 0.0

                st.session_state.calculated_times[m_id] = {
                    "power_mix_kw": agitator_power_kw,
                    "power_pump_kw": power_kw_avg,
                    "heating": thermal["process_time_h"] if thermal["heating_status"] == "ok" else 0.0,
                    "pumping": pumping_time_h,
                    "t_max_mix": p["t_product_out"],
                    "t_rozlew": p["t_discharge_c"],
                    "cooling_h": cooling_time_h if cooling_status == "ok" else 0.0,
                    "power_heating_kw": thermal["power_heating_kw"],
                    "power_cooling_kw": cooling_power_kw,
                    "flow_heating_kg_h": thermal["flow_heating_kg_h"],
                    "flow_cooling_kg_h": flow_cooling_kg_h if cooling_status == "ok" else 0.0,
                    "medium_grz": p["utility_type_heat"],
                    "medium_chl": p["utility_type_cool"],
                    "is_steam": thermal["is_steam"],
                    "availability_pct": availability_combined_pct,
                    "availability_pump_pct": availability_pump_pct,
                    "availability_reactor_pct": availability_reactor_pct,
                }

                cooling_txt = f"{cooling_time_h:.2f}" if cooling_status == "ok" else ("—" if cooling_status == "brak_potrzeby" else "⚠️ N/A")
                heating_txt = f"{thermal['process_time_h']:.2f}" if thermal["heating_status"] == "ok" else "⚠️ N/A"

                summary_combined_rows.append({
                    "ID Urządzenia": m_id,
                    "Linia": kat,
                    "Prędkość [m/s]": round(velocity, 2),
                    "Opór [bar] (Min/Śr/Max)": f"{p_bar_min:.2f}/{p_bar_avg:.2f}/{p_bar_max:.2f}",
                    "Moc Pompy [kW] (Min/Śr/Max)": f"{power_kw_min:.2f}/{power_kw_avg:.2f}/{power_kw_max:.2f}",
                    "Moc Mieszania [kW]": round(agitator_power_kw, 2),
                    "Reżim mieszania": mix_regime,
                    "Moc Grzania [kW]": round(thermal["power_heating_kw"], 1),
                    "Przepływ medium grzewczego [kg/h]": round(thermal["flow_heating_kg_h"], 1),
                    "Czas Grzania [h]": heating_txt,
                    "LMTD Grzania [K]": round(thermal["lmtd_h"], 1),
                    "Moc Chłodzenia [kW]": round(cooling_power_kw, 1),
                    "Przepływ medium chłodzącego [kg/h]": round(flow_cooling_kg_h, 1) if cooling_status == "ok" else 0.0,
                    "Czas chłodzenia [h]": cooling_txt,
                    "Dostępność (MTBF/MTTR) [%]": round(availability_combined_pct, 1),
                    "_velocity_val": velocity,
                    "_lmtd_trigger": thermal["lmtd_trigger"],
                    "_cooling_status": cooling_status,
                    "_heating_status": thermal["heating_status"],
                })
            except Exception as exc:
                st.error(f"⚠️ Błąd obliczeń dla urządzenia {m_id}: {exc}. Sprawdź parametry w sekcji poniżej.")
                continue

        st.markdown("### 📋 Zbiorcza Specyfikacja Techniczna Maszyn, Pompy i Mieszania")
        st.info("💡 **Kryteria inżynieryjne:** Czerwonym kolorem podświetlane są **wyłącznie komórki**, które wykraczają poza normy "
                f"(Prędkość poza przedziałem **{VELOCITY_MIN_MS} - {VELOCITY_MAX_MS} m/s**, błąd profilu termicznego LMTD, lub "
                "niewystarczające ΔT grzania/chłodzenia).")

        if summary_combined_rows:
            df_summary = pd.DataFrame(summary_combined_rows)
            columns_to_show = [c for c in df_summary.columns if not c.startswith('_')]

            def style_basic_with_alerts(df_data):
                style_matrix = pd.DataFrame('', index=df_data.index, columns=df_data.columns)
                for idx, row in df_data.iterrows():
                    v = df_summary.loc[idx, "_velocity_val"]
                    if v < VELOCITY_MIN_MS or v > VELOCITY_MAX_MS:
                        if "Prędkość [m/s]" in style_matrix.columns:
                            style_matrix.loc[idx, "Prędkość [m/s]"] = 'background-color: #FFC7CE; color: #9C0006; font-weight: bold;'

                    lmtd_flag = df_summary.loc[idx, "_lmtd_trigger"]
                    if lmtd_flag == "error":
                        if "LMTD Grzania [K]" in style_matrix.columns:
                            style_matrix.loc[idx, "LMTD Grzania [K]"] = 'background-color: #FCE4D6; color: #C00000; font-weight: bold;'
                    elif lmtd_flag == "warning":
                        if "LMTD Grzania [K]" in style_matrix.columns:
                            style_matrix.loc[idx, "LMTD Grzania [K]"] = 'background-color: #FFF2CC; color: #7F6000;'

                    if df_summary.loc[idx, "_cooling_status"] == "niewystarczajace_dt":
                        if "Czas chłodzenia [h]" in style_matrix.columns:
                            style_matrix.loc[idx, "Czas chłodzenia [h]"] = 'background-color: #FFC7CE; color: #9C0006; font-weight: bold;'

                    if df_summary.loc[idx, "_heating_status"] == "niewystarczajace_dt":
                        if "Czas Grzania [h]" in style_matrix.columns:
                            style_matrix.loc[idx, "Czas Grzania [h]"] = 'background-color: #FFC7CE; color: #9C0006; font-weight: bold;'
                return style_matrix

            df_filtered = df_summary[columns_to_show]
            styled_grid = df_filtered.style.apply(style_basic_with_alerts, axis=None)

            st.dataframe(styled_grid, hide_index=True, use_container_width=True)
        else:
            df_filtered = pd.DataFrame()
            st.warning("Brak poprawnie policzonych urządzeń — sprawdź komunikaty o błędach powyżej.")

        st.markdown("---")

        # ============================================================
        # BILANS PARY I ODPOWIETRZENIA (agregacja dla reaktorów typu Smar/Wax)
        # ============================================================
        grease_mixers_p = [
            (m, st.session_state.mixer_tech_advanced_details.get(m["tag"], {}))
            for m in st.session_state.confirmed_mixers
        ]
        grease_mixers_p = [(m, p) for m, p in grease_mixers_p if p.get("process_type") == "Smar/Wax (gotowanie z odparowaniem)"]

        if grease_mixers_p:
            st.markdown("### 🌫️ Bilans Pary i Odpowietrzenie — Zbiorczy Rurociąg Zrzutowy")
            st.caption("Agreguje strumienie masowe pary wpisane powyżej dla reaktorów oznaczonych jako "
                       "'Smar/Wax' i liczy hydraulikę wspólnego rurociągu zrzutowego metodą Darcy-Weisbacha, "
                       "względem progów bezpieczeństwa (ISO 28300 / API 2000).")
            st.warning("⚠️ Wspomaganie wstępnego oszacowania — wymaga przeglądu przez uprawnionego inżyniera "
                       "ds. bezpieczeństwa procesowego (HAZOP/SIL) przed wdrożeniem.")

            c_gv1, c_gv2, c_gv3, c_gv4 = st.columns(4)
            with c_gv1:
                gv_pipe_length = st.number_input("Długość rurociągu zbiorczego (L) [m]:", min_value=0.1, value=10.0, step=0.5, key="tab2_steam_L")
            with c_gv2:
                gv_dn_choice = st.selectbox("Średnica wg DN (lub 'Własna'):", list(STEAM_PIPE_DN_REFERENCE_M.keys()) + ["Własna"], index=0, key="tab2_steam_dn")
                if gv_dn_choice == "Własna":
                    gv_pipe_d = st.number_input("Średnica wewnętrzna (d) [m]:", min_value=0.01, value=0.0889, step=0.001, format="%.4f", key="tab2_steam_d_custom")
                else:
                    gv_pipe_d = STEAM_PIPE_DN_REFERENCE_M[gv_dn_choice]
            with c_gv3:
                gv_lambda = st.number_input("Współczynnik tarcia (λ) [-]:", min_value=0.001, value=0.025, step=0.001, format="%.3f", key="tab2_steam_lambda")
            with c_gv4:
                gv_rho = st.number_input("Gęstość pary (ρ) [kg/m³]:", min_value=0.01, value=0.598, step=0.01, key="tab2_steam_rho")

            c_ge1, c_ge2 = st.columns(2)
            with c_ge1:
                gv_emergency = st.number_input("Maks. strumień zrzutu awaryjnego (PRV) [kg/s]:", min_value=0.0, value=2.0, step=0.1, key="tab2_steam_emergency")
                gv_nastawa = st.number_input("Nastawa zaworu bezpieczeństwa [bar]:", min_value=0.1, value=10.0, step=0.5, key="tab2_steam_nastawa")
            with c_ge2:
                gv_prog_ab = st.number_input("Próg prędkości - scenariusze A/B [m/s]:", min_value=1.0, value=35.0, step=1.0, key="tab2_steam_prog_ab")
                gv_prog_c = st.number_input("Próg prędkości - scenariusz C [m/s]:", min_value=1.0, value=60.0, step=1.0, key="tab2_steam_prog_c")

            sum_avg_flow = sum(p.get("steam_avg_flow", 0.0) for _, p in grease_mixers_p)
            max_single_decompress = max((p.get("steam_max_decompress", 0.0) for _, p in grease_mixers_p), default=0.0)
            sum_max_process = sum(p.get("steam_max_process", 0.0) for _, p in grease_mixers_p)
            prog_dp_bar_gv = gv_nastawa * 0.10

            gv_scenarios = [
                {"name": f"A. Normalna praca średnia ({len(grease_mixers_p)} reaktor(y) Smar/Wax)", "mass_flow": sum_avg_flow, "check": "velocity", "prog": gv_prog_ab,
                 "msg_bad": "ZAGROŻENIE: Rura za ciasna nawet dla wartości średnich!",
                 "msg_ok": "Teoretycznie bezpiecznie, ale ignoruje szczyty chwilowe (dm/dt)."},
                {"name": "B. Szczyt odparowania (najgorszy pojedynczy reaktor, faza Flash)", "mass_flow": max_single_decompress, "check": "velocity", "prog": gv_prog_ab,
                 "msg_bad": "OSTRZEŻENIE: Pojedynczy zrzut dławi rurę. Spadek efektu flash.",
                 "msg_ok": "Prędkość optymalna dla jednej maszyny."},
                {"name": "C. Najgorszy szczyt roboczy (suma maks. procesowych, koincydencja)", "mass_flow": sum_max_process, "check": "velocity", "prog": gv_prog_c,
                 "msg_bad": f"KRYTYCZNE DŁAWIENIE! Prędkość > {gv_prog_c:.0f} m/s. Blokada zrzutu pary, ryzyko cofki produktu! Rozważ większą średnicę.",
                 "msg_ok": "ZGODNIE Z NORMĄ (15-30 m/s): Średnica dobrana poprawnie pod szczyt obciążenia."},
                {"name": f"D. Scenariusz awaryjny (otwarcie zaworu - {gv_nastawa:.0f} bar)", "mass_flow": gv_emergency, "check": "pressure", "prog": prog_dp_bar_gv,
                 "msg_bad": f"KATASTROFA API 2000! Opory przekraczają 10% nastawy ({prog_dp_bar_gv:.2f} bar). Zawór ulegnie ZABLOKOWANIU!",
                 "msg_ok": "ZGODNIE Z API 2000: Ciśnienie wsteczne poniżej 10% nastawy. Zawór zadziała prawidłowo."},
            ]

            gv_result_rows = []
            for sc in gv_scenarios:
                vol_flow, velocity, dp_pa, dp_bar = compute_vent_line_scenario(sc["mass_flow"], gv_rho, gv_pipe_length, gv_pipe_d, gv_lambda)
                is_bad = (velocity > sc["prog"]) if sc["check"] == "velocity" else (dp_bar > sc["prog"])
                gv_result_rows.append({
                    "Scenariusz Pracy Instalacji": sc["name"], "Masa pary [kg/s]": round(sc["mass_flow"], 4),
                    "Prędkość pary [m/s]": round(velocity, 2), "Opory liniowe [bar]": round(dp_bar, 4),
                    "Weryfikacja": sc["msg_bad"] if is_bad else sc["msg_ok"], "_is_bad": is_bad,
                })

            df_gv = pd.DataFrame(gv_result_rows)

            def style_gv_alerts(df_data):
                sm = pd.DataFrame('', index=df_data.index, columns=df_data.columns)
                for idx in df_data.index:
                    if df_gv.loc[idx, "_is_bad"]:
                        for col in ["Prędkość pary [m/s]", "Opory liniowe [bar]", "Weryfikacja"]:
                            sm.loc[idx, col] = 'background-color: #FFC7CE; color: #9C0006; font-weight: bold;'
                    else:
                        sm.loc[idx, "Weryfikacja"] = 'background-color: #C6EFCE; color: #006100;'
                return sm

            st.dataframe(df_gv.drop(columns=["_is_bad"]).style.apply(style_gv_alerts, axis=None), hide_index=True, use_container_width=True)
            n_gv_alerts = int(df_gv["_is_bad"].sum())
            if n_gv_alerts > 0:
                st.error(f"🔴 {n_gv_alerts} z {len(df_gv)} scenariuszy przekracza próg bezpieczeństwa.")
            else:
                st.success("🟢 Wszystkie scenariusze mieszczą się w przyjętych progach bezpieczeństwa.")

            st.markdown("---")

        # ============================================================
        # DOBÓR KOTŁA GRZEWCZEGO (agregacja zapotrzebowania cieplnego floty)
        # ============================================================
        st.markdown("### 🔥 Dobór Kotła Grzewczego i Instalacji Grzewczej")
        st.caption("Sumuje moc grzania I przepływ medium grzewczego (ta zakładka) po wszystkich mieszalnikach — moc dobiera kocioł, "
                   "przepływ dobiera pompy obiegowe i średnicę rurociągu rozdzielczego.")

        heat_by_medium = {}
        for m in st.session_state.confirmed_mixers:
            ct = st.session_state.calculated_times.get(m["tag"])
            if ct is None:
                continue
            medium = ct.get("medium_grz", "Woda technologiczna")
            heat_by_medium.setdefault(medium, {"power_kw": 0.0, "flow_kg_h": 0.0, "is_steam": ct.get("is_steam", False),
                                                "daily_energy_kwh": 0.0})
            heat_by_medium[medium]["power_kw"] += ct.get("power_heating_kw", 0.0)
            heat_by_medium[medium]["flow_kg_h"] += ct.get("flow_heating_kg_h", 0.0)
            batches_per_day = m["batches_count"] / (WORKING_DAYS_YEAR / MONTHS_PER_YEAR)
            heat_by_medium[medium]["daily_energy_kwh"] += ct.get("power_heating_kw", 0.0) * ct.get("heating", 0.0) * batches_per_day

        if not heat_by_medium:
            st.info("ℹ️ Skonfiguruj bilans cieplny mieszalników powyżej, aby dobrać kocioł.")
            total_heating_power_installed = 0.0
        else:
            c_b1, c_b2 = st.columns(2)
            with c_b1:
                wspolczynnik_jednoczesnosci_cieplny = st.slider(
                    "Współczynnik jednoczesności grzania [%]:", min_value=20, max_value=100, value=70,
                    help="Odsetek zainstalowanej mocy grzania, który realnie występuje jednocześnie w szczycie "
                         "(rzadko wszystkie reaktory grzeją w tej samej minucie). Używany, gdy NIE stosujemy bufora ciepła.") / 100.0
            with c_b2:
                margines_kotla = st.slider("Margines bezpieczeństwa kotła [%]:", min_value=0, max_value=50, value=20) / 100.0

            st.markdown("##### 🛢️ Bufor Ciepła (Zbiornik Akumulacyjny)")
            st.caption("Bufor ciepła gromadzi energię w spokojniejszych okresach i oddaje ją w szczycie — dzięki temu kocioł nie musi "
                       "być dobrany na chwilowy szczyt mocy, tylko na uśrednione, ciągłe zapotrzebowanie w ciągu dnia (mniejszy, tańszy "
                       "kocioł pracujący w sposób ciągły zamiast dużego kotła 'z doskoku').")
            stosuj_bufor = st.checkbox("Zastosuj bufor ciepła w instalacji", value=False, key="stosuj_bufor_cieplny")
            if stosuj_bufor:
                c_buf1, c_buf2 = st.columns(2)
                with c_buf1:
                    autonomia_bufora_h = st.number_input(
                        "Docelowa autonomia bufora [h]:", min_value=0.25, value=1.0, step=0.25, key="autonomia_bufora",
                        help="Ile godzin różnicy między szczytem a średnią ma pokryć bufor — typowo 0.5-2h dla procesów wsadowych."
                    )
                with c_buf2:
                    delta_t_bufora = st.number_input(
                        "Użyteczny wahań ΔT bufora [K]:", min_value=5.0, value=20.0, step=1.0, key="dt_bufora",
                        help="Różnica między maks. a min. temperaturą wody w zbiorniku akumulacyjnym, jaką realnie wykorzystujemy."
                    )

            boiler_rows = []
            total_heating_power_installed = 0.0
            total_buffer_kwh_needed = 0.0
            for medium, data in heat_by_medium.items():
                installed = data["power_kw"]
                total_heating_power_installed += installed
                needed_peak = installed * wspolczynnik_jednoczesnosci_cieplny * (1 + margines_kotla)

                if stosuj_bufor:
                    needed_avg = (data["daily_energy_kwh"] / godziny_dziennie) * (1 + margines_kotla) if godziny_dziennie > 0 else needed_peak
                    needed = min(needed_avg, needed_peak)  # bufor nigdy nie każe dobierać WIĘKSZEGO kotła niż szczyt
                    buffer_kwh = max(needed_peak - needed, 0.0) * autonomia_bufora_h
                    total_buffer_kwh_needed += buffer_kwh
                else:
                    needed = needed_peak

                STANDARD_BOILER_SIZES_KW = [50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 800, 1000, 1250, 1600, 2000]
                recommended = next((s for s in STANDARD_BOILER_SIZES_KW if s >= needed), needed)
                row = {
                    "Medium": medium,
                    "Moc zainstalowana (szczyt) [kW]": round(installed, 1),
                    "Moc wymagana [kW]": round(needed, 1),
                    "Zalecana moc kotła [kW]": round(recommended, 1),
                    "Przepływ medium (szczyt) [kg/h]": round(data["flow_kg_h"], 1),
                }
                if data["is_steam"]:
                    row["Wydajność pary [kg/h]"] = round(recommended * 3600 / STEAM_LATENT_HEAT_KJKG, 1)
                boiler_rows.append(row)
            st.dataframe(pd.DataFrame(boiler_rows), hide_index=True, use_container_width=True)

            if stosuj_bufor and total_buffer_kwh_needed > 0:
                buffer_volume_m3 = (total_buffer_kwh_needed * 3600) / (4.19 * 1000 * delta_t_bufora)
                m_buf1, m_buf2 = st.columns(2)
                with m_buf1:
                    st.metric("🛢️ Szacowana wymagana pojemność cieplna bufora", f"{total_buffer_kwh_needed:.1f} kWh")
                with m_buf2:
                    st.metric("📐 Orientacyjna objętość zbiornika (woda)", f"{buffer_volume_m3:.1f} m³")
                st.caption("⚠️ To uproszczone oszacowanie (różnica szczyt/średnia × zadeklarowana autonomia), nie pełna symulacja "
                           "profilu obciążenia w czasie — realny dobór bufora warto zweryfikować analizą dynamiczną, szczególnie "
                           "przy nierównomiernym harmonogramie szarż.")

        st.markdown("##### ⛽ Typ Kotła i Koszt Paliwa")
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            typ_kotla = st.radio("Typ kotła centralnego:", ["Gazowy", "Elektryczny"], horizontal=True, key="typ_kotla")
        with c_f2:
            if typ_kotla == "Gazowy":
                cena_gazu_mwh = st.number_input("Cena gazu [PLN/MWh]:", min_value=1.0, value=250.0, key="cena_gazu")
                sprawnosc_kotla = st.number_input("Sprawność kotła gazowego [%]:", min_value=50.0, max_value=100.0, value=90.0, key="sprawnosc_gaz") / 100.0
            else:
                cena_gazu_mwh = None
                sprawnosc_kotla = st.number_input("Sprawność kotła elektrycznego [%]:", min_value=50.0, max_value=100.0, value=98.0, key="sprawnosc_el") / 100.0
        with c_f3:
            st.metric("Moc zainstalowana grzania (suma floty)", f"{total_heating_power_installed:.1f} kW")

        # Miesięczny koszt paliwa grzewczego — energia użyteczna (Q grzania) / sprawność kotła.
        total_heating_energy_mwh_month = 0.0
        for m in st.session_state.confirmed_mixers:
            ct = st.session_state.calculated_times.get(m["tag"])
            if ct is None:
                continue
            energy_kwh_batch = ct.get("power_heating_kw", 0.0) * ct.get("heating", 0.0)
            total_heating_energy_mwh_month += (energy_kwh_batch * m["batches_count"]) / 1000.0

        fuel_price_for_calc = cena_gazu_mwh if typ_kotla == "Gazowy" else st.session_state.get("cena_mwh_tab4", 750.0)
        koszt_paliwa_grzewczego_month = (total_heating_energy_mwh_month / sprawnosc_kotla) * fuel_price_for_calc if sprawnosc_kotla > 0 else 0.0

        st.session_state["koszt_paliwa_grzewczego_month"] = koszt_paliwa_grzewczego_month
        st.session_state["boiler_capacity_installed_kw"] = total_heating_power_installed
        st.session_state["sprawnosc_kotla_frac"] = sprawnosc_kotla
        st.session_state["cena_gazu_mwh"] = cena_gazu_mwh

        st.caption(f"Szacowany miesięczny koszt paliwa grzewczego: **{koszt_paliwa_grzewczego_month:,.2f}** "
                   f"({'gaz' if typ_kotla=='Gazowy' else 'energia elektryczna'}) — pozycja ta trafia teraz do "
                   f"Zakładki 4 (Analiza Finansowa) jako osobny koszt.")

        st.markdown("---")

        # ============================================================
        # DOBÓR UKŁADU CHŁODZENIA (moc + przepływ chłodziwa floty)
        # ============================================================
        st.markdown("### ❄️ Dobór Układu Chłodzenia")
        st.caption("Analogicznie do kotła grzewczego — suma mocy chłodzenia i przepływu chłodziwa po wszystkich mieszalnikach, "
                   "do doboru wydajności agregatu/wieży chłodniczej oraz pomp i rurociągu obiegu chłodzącego. Zapotrzebowanie "
                   "elektryczne chłodzenia (przez COP) jest już liczone osobno w sekcji ⚡ poniżej.")

        cool_by_medium = {}
        for m in st.session_state.confirmed_mixers:
            ct = st.session_state.calculated_times.get(m["tag"])
            if ct is None:
                continue
            medium = ct.get("medium_chl", "Woda technologiczna")
            cool_by_medium.setdefault(medium, {"power_kw": 0.0, "flow_kg_h": 0.0})
            cool_by_medium[medium]["power_kw"] += ct.get("power_cooling_kw", 0.0)
            cool_by_medium[medium]["flow_kg_h"] += ct.get("flow_cooling_kg_h", 0.0)

        if not cool_by_medium:
            st.info("ℹ️ Skonfiguruj bilans cieplny mieszalników powyżej, aby dobrać układ chłodzenia.")
        else:
            wspolczynnik_jednoczesnosci_chlodzenia = st.slider(
                "Współczynnik jednoczesności chłodzenia [%]:", min_value=20, max_value=100, value=70,
                help="Odsetek zainstalowanej mocy chłodzenia, który realnie występuje jednocześnie w szczycie.",
                key="wsp_jednocz_chlodzenie") / 100.0

            cooling_rows = []
            for medium, data in cool_by_medium.items():
                installed_cool = data["power_kw"]
                needed_cool = installed_cool * wspolczynnik_jednoczesnosci_chlodzenia
                cooling_rows.append({
                    "Medium": medium,
                    "Moc zainstalowana (szczyt) [kW]": round(installed_cool, 1),
                    "Moc wymagana (ze wsp. jednocz.) [kW]": round(needed_cool, 1),
                    "Przepływ chłodziwa (szczyt) [kg/h]": round(data["flow_kg_h"], 1),
                })
            st.dataframe(pd.DataFrame(cooling_rows), hide_index=True, use_container_width=True)

        st.markdown("---")

        # ============================================================
        # ZAPOTRZEBOWANIE NA MOC ELEKTRYCZNĄ I DOBÓR TRANSFORMATORA
        # ============================================================
        st.markdown("### ⚡ Zapotrzebowanie na Moc Elektryczną i Dobór Transformatora")
        st.caption("Sumuje moc silników mieszadeł i pomp z floty, ewentualny kocioł elektryczny oraz (opcjonalnie) "
                   "szacunkowe zapotrzebowanie elektryczne chłodzenia (przez współczynnik COP), z uwzględnieniem "
                   "współczynnika jednoczesności i mocy transformatora w kVA.")

        total_mix_power = sum(st.session_state.calculated_times.get(m["tag"], {}).get("power_mix_kw", 0.0)
                               for m in st.session_state.confirmed_mixers)
        total_pump_power = sum(st.session_state.calculated_times.get(m["tag"], {}).get("power_pump_kw", 0.0)
                                for m in st.session_state.confirmed_mixers)
        total_cooling_duty = sum(st.session_state.calculated_times.get(m["tag"], {}).get("power_cooling_kw", 0.0)
                                  for m in st.session_state.confirmed_mixers)

        c_e1, c_e2, c_e3 = st.columns(3)
        with c_e1:
            uwzglednij_chlodzenie_el = st.checkbox("Uwzględnij elektryczne chłodzenie (agregaty/chillery)", value=True)
            cop_chlodzenia = st.number_input("COP chłodzenia [-]:", min_value=1.0, value=3.0,
                                              disabled=not uwzglednij_chlodzenie_el,
                                              help="Współczynnik wydajności chłodniczej — moc elektryczna = moc chłodzenia / COP.")
        with c_e2:
            wspolczynnik_jednoczesnosci_el = st.slider("Współczynnik jednoczesności elektrycznej [%]:",
                                                         min_value=20, max_value=100, value=65) / 100.0
            cos_phi = st.number_input("cos φ (współczynnik mocy):", min_value=0.5, max_value=1.0, value=0.90, step=0.01)
        with c_e3:
            margines_transformatora = st.slider("Margines bezpieczeństwa transformatora [%]:",
                                                  min_value=0, max_value=100, value=25) / 100.0

        electric_boiler_load = total_heating_power_installed if typ_kotla == "Elektryczny" else 0.0
        cooling_electric_load = (total_cooling_duty / cop_chlodzenia) if uwzglednij_chlodzenie_el and cop_chlodzenia > 0 else 0.0

        st.markdown("---")
        st.markdown("##### 🏢 Odbiory Pozaprodukcyjne (Serwery, Oświetlenie, Sprężarkownia, Inne)")
        st.caption("Odbiory niezwiązane bezpośrednio z reaktorami/pompami floty, ale realnie obciążające transformator "
                   "zakładu — zwykle pracują z wyższym współczynnikiem jednoczesności niż urządzenia procesowe "
                   "wsadowe (są 'włączone' niemal cały czas), więc liczone są z osobnym współczynnikiem poniżej.")

        c_f_1, c_f_2, c_f_3 = st.columns(3)
        with c_f_1:
            serwery_kw = st.number_input("Serwery / IT [kW]:", min_value=0.0, value=5.0, step=0.5, key="fac_servers_kw")
            hvac_kw = st.number_input("Wentylacja / HVAC (poza chłodzeniem procesowym) [kW]:", min_value=0.0, value=15.0, step=1.0, key="fac_hvac_kw")
        with c_f_2:
            powierzchnia_zakladu_m2 = st.number_input("Powierzchnia zakładu do oświetlenia [m²]:", min_value=0.0, value=2000.0, step=100.0, key="fac_area_m2")
            wskaznik_oswietlenia_w_m2 = st.number_input("Wskaźnik mocy oświetlenia [W/m²]:", min_value=1.0, value=8.0, step=0.5, key="fac_light_wm2",
                                                          help="Typowo 6-10 W/m² dla oświetlenia LED w halach przemysłowych.")
            oswietlenie_kw = (powierzchnia_zakladu_m2 * wskaznik_oswietlenia_w_m2) / 1000.0
            st.caption(f"Wyliczona moc oświetlenia: **{oswietlenie_kw:.1f} kW**")
        with c_f_3:
            sprezarkownia_kw = st.number_input("Sprężarkownia (sprężone powietrze) [kW]:", min_value=0.0, value=45.0, step=5.0, key="fac_compressed_air_kw")
            inne_odbiory_kw = st.number_input("Inne (biura, ładowarki wózków, warsztat UR) [kW]:", min_value=0.0, value=20.0, step=5.0, key="fac_other_kw")

        total_facility_load_kw = serwery_kw + hvac_kw + oswietlenie_kw + sprezarkownia_kw + inne_odbiory_kw
        wspolczynnik_jednoczesnosci_facility = st.slider(
            "Współczynnik jednoczesności odbiorów pozaprodukcyjnych [%]:", min_value=50, max_value=100, value=90,
            help="Serwery/oświetlenie/sprężarkownia pracują niemal ciągle, więc ten współczynnik jest zwykle wyższy niż dla floty procesowej.",
            key="fac_wsp_jednocz") / 100.0

        st.markdown("---")

        installed_electric_load_kw = total_mix_power + total_pump_power + electric_boiler_load + cooling_electric_load
        process_demand_kw = installed_electric_load_kw * wspolczynnik_jednoczesnosci_el
        facility_demand_kw = total_facility_load_kw * wspolczynnik_jednoczesnosci_facility
        demand_kw = process_demand_kw + facility_demand_kw
        demand_kva = (demand_kw / cos_phi) * (1 + margines_transformatora) if cos_phi > 0 else 0.0

        STANDARD_TRANSFORMER_SIZES_KVA = [100, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500]
        recommended_transformer = next((s for s in STANDARD_TRANSFORMER_SIZES_KVA if s >= demand_kva), demand_kva)

        load_rows = [
            {"Odbiornik": "Silniki mieszadeł (suma floty)", "Moc [kW]": round(total_mix_power, 1), "Kategoria": "Proces"},
            {"Odbiornik": "Silniki pomp (suma floty)", "Moc [kW]": round(total_pump_power, 1), "Kategoria": "Proces"},
            {"Odbiornik": "Kocioł elektryczny" if typ_kotla == "Elektryczny" else "Kocioł (gazowy — brak obciążenia elektrycznego)",
             "Moc [kW]": round(electric_boiler_load, 1), "Kategoria": "Proces"},
            {"Odbiornik": "Chłodzenie (agregaty, przez COP)" if uwzglednij_chlodzenie_el else "Chłodzenie (nieuwzględnione)",
             "Moc [kW]": round(cooling_electric_load, 1), "Kategoria": "Proces"},
            {"Odbiornik": "Serwery / IT", "Moc [kW]": round(serwery_kw, 1), "Kategoria": "Pozaprodukcyjne"},
            {"Odbiornik": "Wentylacja / HVAC", "Moc [kW]": round(hvac_kw, 1), "Kategoria": "Pozaprodukcyjne"},
            {"Odbiornik": "Oświetlenie zakładu", "Moc [kW]": round(oswietlenie_kw, 1), "Kategoria": "Pozaprodukcyjne"},
            {"Odbiornik": "Sprężarkownia", "Moc [kW]": round(sprezarkownia_kw, 1), "Kategoria": "Pozaprodukcyjne"},
            {"Odbiornik": "Inne (biura, ładowarki, UR)", "Moc [kW]": round(inne_odbiory_kw, 1), "Kategoria": "Pozaprodukcyjne"},
        ]
        st.dataframe(pd.DataFrame(load_rows), hide_index=True, use_container_width=True)

        m_e0a, m_e0b = st.columns(2)
        with m_e0a:
            st.metric("⚙️ Moc szczytowa — proces (ze wsp. jednocz.)", f"{process_demand_kw:.1f} kW")
        with m_e0b:
            st.metric("🏢 Moc szczytowa — pozaprodukcyjne (ze wsp. jednocz.)", f"{facility_demand_kw:.1f} kW")

        m_e1, m_e2, m_e3, m_e4 = st.columns(4)
        with m_e1: st.metric("Moc zainstalowana (razem)", f"{installed_electric_load_kw + total_facility_load_kw:.1f} kW")
        with m_e2: st.metric("Moc szczytowa (razem)", f"{demand_kw:.1f} kW")
        with m_e3: st.metric("Moc pozorna wymagana", f"{demand_kva:.1f} kVA")
        with m_e4: st.metric("🔌 Zalecany transformator", f"{recommended_transformer:.0f} kVA")

        # Zapis do session_state, żeby połączona Zakładka Analiza Finansowa mogła doliczyć
        # PEŁNY koszt energii elektrycznej (proces + odbiory pozaprodukcyjne), a nie tylko
        # mieszanie/pompowanie, jak dotychczas. Proces i odbiory pozaprodukcyjne zapisywane
        # OSOBNO, bo w symulacji rozruchu (ROI) tylko obciążenie procesowe skaluje się z
        # wolumenem produkcji — serwery/HVAC/oświetlenie/sprężarkownia działają praktycznie
        # niezależnie od tego, ile realnie produkujesz w danym roku.
        st.session_state["demand_kw_total"] = demand_kw
        st.session_state["process_demand_kw"] = process_demand_kw
        st.session_state["facility_demand_kw"] = facility_demand_kw

        st.caption("Uwaga: sekcja rozlewu/pakowania nie ma dziś modelowanych mocy silników (tylko wydajność kg/min), "
                   "więc nie jest tu ujęta — jeśli chcesz uwzględnić linie napełniające w bilansie elektrycznym, "
                   "podaj ich orientacyjną moc zainstalowaną do doliczenia ręcznego.")

        if not df_filtered.empty:
            csv_buffer = io.StringIO()
            df_filtered.to_csv(csv_buffer, index=False, sep=";")

            st.download_button(
                label="📊 Pobierz pełny raport procesowy (Format CSV)",
                data=csv_buffer.getvalue().encode("utf-8-sig"),  # BOM, żeby Excel poprawnie czytał polskie znaki
                file_name="Fuchs_Pelny_Model_Hydrauliczno_Procesowy.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_download_final_csv_v13"
            )

# ==========================================
# ZAKŁADKA 3: LOGISTYKA I OPALETOWANIE
# ==========================================
with tab3:
    st.header("📦 Analiza Logistyczna, Czas Rozlewu i Gospodarka Paletowa")
    if not st.session_state.confirmed_mixers:
        st.info("💡 Najpierw zatwierdź konfigurację floty w Zakładce 2.")
    else:
        mixers_fleet = st.session_state.confirmed_mixers

        rampup_year_options = ["Docelowa produkcja (100%)"] + [f"Rok {i+1}" for i in range(RAMPUP_YEARS)]
        selected_rampup_year_label = st.selectbox(
            "📈 Rok symulacji rozruchu:", rampup_year_options, index=0, key="tab3_rampup_year_select",
            help="Magazyn i flota są budowane od razu pod docelową (100%) produkcję — ten wybór tylko pokazuje, "
                 "jaki wolumen FG i RM realnie przepłynie przez fabrykę w danym roku rozruchu (krzywa z Zakładki 2), "
                 "i ile z gotowej powierzchni magazynowej to zajmie."
        )
        selected_rampup_year_idx = None if selected_rampup_year_label.startswith("Docelowa") else int(selected_rampup_year_label.split(" ")[1]) - 1

        st.markdown("---")

        st.markdown("##### 📦 Konfiguracja Opakowań i Głowic Rozlewniczych")
        st.caption("Jedna tabela na typ opakowania: pojemność i sztuk/paletę (domyślnie wbudowane, nadpisywane przez "
                   "opcjonalny arkusz 'Opakowania' z Zakładki 1) razem z parametrami głowic nalewaka tego opakowania. "
                   "Dodaj/usuń wiersz, aby dodać/usunąć typ opakowania.")

        if "filling_lines_config" not in st.session_state:
            st.session_state.filling_lines_config = {}
        for p in st.session_state.pack_configs.keys():
            if p not in st.session_state.filling_lines_config:
                st.session_state.filling_lines_config[p] = {"nozzles": 4, "speed_kg_min": 15.0} if "5l" in p.lower() or "1l" in p.lower() else {"nozzles": 1, "speed_kg_min": 60.0}

        pack_fill_editor_rows = [
            {"Nazwa Opakowania": name, "Pojemność [L]": cfg["size_l"], "Sztuk na Palecie": cfg["per_pallet"],
             "Głowice nalewaka [szt]": int(st.session_state.filling_lines_config.get(name, {"nozzles": 1})["nozzles"]),
             "Wydajność 1 głowicy [kg/min]": float(st.session_state.filling_lines_config.get(name, {"speed_kg_min": 30.0})["speed_kg_min"])}
            for name, cfg in st.session_state.pack_configs.items()
        ]
        edited_pack_fill_df = st.data_editor(
            pd.DataFrame(pack_fill_editor_rows), hide_index=True, use_container_width=True,
            num_rows="dynamic", key="pack_fill_editor"
        )
        new_pack_configs = {}
        new_filling_config = {}
        for _, row in edited_pack_fill_df.iterrows():
            name = str(row["Nazwa Opakowania"])
            if not name or pd.isna(row["Pojemność [L]"]) or pd.isna(row["Sztuk na Palecie"]):
                continue
            existing = st.session_state.pack_configs.get(name, {"rate_szt_h": 0})
            new_pack_configs[name] = {
                "size_l": float(row["Pojemność [L]"]),
                "per_pallet": int(row["Sztuk na Palecie"]),
                "rate_szt_h": existing.get("rate_szt_h", 0),
            }
            new_filling_config[name] = {
                "nozzles": float(row["Głowice nalewaka [szt]"]) if pd.notna(row["Głowice nalewaka [szt]"]) else 1.0,
                "speed_kg_min": float(row["Wydajność 1 głowicy [kg/min]"]) if pd.notna(row["Wydajność 1 głowicy [kg/min]"]) else 30.0,
            }
        st.session_state.pack_configs = new_pack_configs
        st.session_state.filling_lines_config = new_filling_config

        aktywne_opakowania = set(st.session_state.pack_configs.keys())

        with st.expander("🧴 Rozbicie na Opakowania (ręczne, per linia) — używane, gdy receptura go nie określa", expanded=False):
            st.caption("Jeśli produkt ma w recepturze (Zakładka 1) wypełnione % opakowań, apka użyje ich wprost. "
                       "Dla pozostałych produktów obowiązuje rozbicie z tej tabeli, per linia produktowa.")

            opakowania_podzial = st.session_state.setdefault("opakowania_podzial", {})
            split_editor_rows = []
            for kat in wybrane_kategorie:
                for p in st.session_state.pack_configs.keys():
                    key_id = f"pct_{kat}_{p}"
                    split_editor_rows.append({"Linia": kat, "Opakowanie": p, "Udział [%]": opakowania_podzial.get(key_id, 0.0)})

            if split_editor_rows:
                edited_split_df = st.data_editor(
                    pd.DataFrame(split_editor_rows), hide_index=True, use_container_width=True,
                    disabled=["Linia", "Opakowanie"], key="opakowania_split_editor"
                )
                for _, row in edited_split_df.iterrows():
                    opakowania_podzial[f"pct_{row['Linia']}_{row['Opakowanie']}"] = float(row["Udział [%]"])

                sum_check = edited_split_df.groupby("Linia")["Udział [%]"].sum()
                bad_lines = sum_check[(sum_check > 0) & ((sum_check - 100).abs() > 0.5)]
                if not bad_lines.empty:
                    st.warning("⚠️ Suma % różni się od 100% dla: " + ", ".join(f"{k} ({v:.0f}%)" for k, v in bad_lines.items()) +
                               " — dotyczy tylko produktów bez własnego rozbicia w recepturze.")
            else:
                st.info("Wybierz aktywne linie produktowe w panelu bocznym, aby skonfigurować ręczny podział opakowań.")

        st.markdown("---")
        czas_skladowania_dni = st.number_input("Czas składowania palety (Rotacja) [dni]:", min_value=1, value=14)
        st.session_state["czas_skladowania_tab3"] = czas_skladowania_dni
        dni_robocze_miesiac = WORKING_DAYS_YEAR / MONTHS_PER_YEAR

        real_split_rows = []
        fg_positions_target_list = []  # miejsca magazynowe FG liczone przy 100% celu (stały rozmiar budynku)
        fg_pallets_target_list = []  # palet/mies. FG liczone przy 100% celu - do wykresu wysyłek na 5 lat
        recipes_df_lookup = st.session_state.get("recipes_df")
        pack_cols_in_recipe = []
        if recipes_df_lookup is not None and not recipes_df_lookup.empty:
            pack_cols_in_recipe = [c for c in recipes_df_lookup.columns if c.startswith("Opak: ") and c.endswith(" [%]")]

        effective_year_idx_for_import = selected_rampup_year_idx if selected_rampup_year_idx is not None else RAMPUP_YEAR_TARGET_SENTINEL
        products_imported_this_view = set()  # produkty (recipe_product) importowane w wybranym roku/widoku

        for m in mixers_fleet:
            kat = m["product_family"]
            recipe_product = m.get("recipe_product")

            # Produkt z DEDYKOWANYM zbiornikiem (recipe_product ustawiony), który w wybranym
            # roku/widoku jest jeszcze importowany (nie osiągnął swojego roku przejścia) - jego
            # BIEŻĄCA (ten rok) produkcja to 0, a zapotrzebowanie na magazyn liczy się osobno w
            # sekcji "Import" poniżej, z rytmu dostaw. Budynek (docelowe 100%) i tak MUSI
            # uwzględnić jego docelową (już produkowaną) wielkość, więc target liczy się zawsze,
            # niezależnie od statusu importu w wybranym roku. Zbiorniki współdzielone (bez
            # pojedynczego recipe_product) nie są dziś rozbijane per produkt - traktowane jak
            # dotychczas, w całości jako produkcja.
            is_imported_this_view = False
            if recipe_product and recipes_df_lookup is not None and RECIPE_SOURCING_COL in recipes_df_lookup.columns:
                match_src = recipes_df_lookup[recipes_df_lookup[RECIPE_PRODUCT_COL] == recipe_product]
                if not match_src.empty:
                    src_row = match_src.iloc[0]
                    if is_product_imported_in_year(src_row.get(RECIPE_SOURCING_COL, "Produkcja własna"),
                                                    src_row.get(RECIPE_IMPORT_TRANSITION_COL, ""),
                                                    effective_year_idx_for_import):
                        is_imported_this_view = True
                        products_imported_this_view.add(recipe_product)

            rampup_frac_fg = get_rampup_fraction(kat, selected_rampup_year_idx) if selected_rampup_year_idx is not None else 1.0
            target_monthly_mass = m["batches_count"] * m["mass_per_batch"]
            mixer_monthly_mass = 0.0 if is_imported_this_view else target_monthly_mass * rampup_frac_fg
            rho_linii = st.session_state.active_portfolio[kat]["density"]

            # Priorytet 1: rozbicie na opakowania WPROST z receptury tego konkretnego produktu
            # (Zakładka 1), jeśli podano i sumuje się w przybliżeniu do 100%.
            recipe_split = None
            if recipe_product and pack_cols_in_recipe:
                match = recipes_df_lookup[recipes_df_lookup[RECIPE_PRODUCT_COL] == recipe_product]
                if not match.empty:
                    row0 = match.iloc[0]
                    pack_sum = sum(row0.get(c, 0) or 0 for c in pack_cols_in_recipe)
                    if pack_sum > 0.5:
                        recipe_split = {c[len("Opak: "):-len(" [%]")]: (row0.get(c, 0) or 0) for c in pack_cols_in_recipe
                                         if (row0.get(c, 0) or 0) > 0}

            if recipe_split is not None:
                split_source = "receptura"
                pack_pcts = recipe_split
            else:
                # Priorytet 2 (fallback): ręczny podział per linia z tabeli powyżej.
                split_source = "ręczny"
                pack_pcts = {p: opakowania_podzial.get(f"pct_{kat}_{p}", 0.0) for p in st.session_state.pack_configs.keys()}

            for p, udzial_pct in pack_pcts.items():
                if udzial_pct <= 0 or p not in st.session_state.pack_configs:
                    continue
                masa_opakowania_month = mixer_monthly_mass * (udzial_pct / 100.0)
                pack_capacity_kg = st.session_state.pack_configs[p]["size_l"] * rho_linii
                liczba_sztuk_month = math.ceil(masa_opakowania_month / pack_capacity_kg) if pack_capacity_kg > 0 else 0

                cfg_fill = st.session_state.filling_lines_config.get(p, {"nozzles": 1, "speed_kg_min": 30.0})
                sekcja_nalewania_m3_h = (cfg_fill["nozzles"] * cfg_fill["speed_kg_min"] * 60.0) / (rho_linii * 1000.0)

                # Rzeczywisty przepływ pompy TEGO KONKRETNEGO mieszalnika z Zakładki 3 (nie
                # reprezentanta całej grupy jak poprzednio - każdy mieszalnik ma teraz własny wiersz).
                tech_details = st.session_state.get("mixer_tech_advanced_details", {}).get(m["tag"], {})
                q_pump_m3h = tech_details.get("pump_flow_m3h", 15.0)

                q_effective_flow_m3h = min(q_pump_m3h, sekcja_nalewania_m3_h)
                czas_rozlewu_h = (masa_opakowania_month / (rho_linii * 1000.0)) / q_effective_flow_m3h if q_effective_flow_m3h > 0 else 0.0
                liczba_palet_month = math.ceil(liczba_sztuk_month / st.session_state.pack_configs[p]["per_pallet"])
                miejsca_paletowe = math.ceil((liczba_palet_month / dni_robocze_miesiac) * czas_skladowania_dni)

                # Miejsca magazynowe przy 100% celu (niezależnie od wybranego roku symulacji) -
                # to jest rozmiar BUDYNKU, który stawia się raz, pod docelową zdolność produkcyjną.
                masa_opakowania_month_target = target_monthly_mass * (udzial_pct / 100.0)
                liczba_sztuk_month_target = math.ceil(masa_opakowania_month_target / pack_capacity_kg) if pack_capacity_kg > 0 else 0
                liczba_palet_month_target = math.ceil(liczba_sztuk_month_target / st.session_state.pack_configs[p]["per_pallet"])
                miejsca_paletowe_target = math.ceil((liczba_palet_month_target / dni_robocze_miesiac) * czas_skladowania_dni)
                fg_positions_target_list.append(miejsca_paletowe_target)
                fg_pallets_target_list.append(liczba_palet_month_target)

                if not is_imported_this_view:
                    real_split_rows.append({
                        "Typ": "FG", "Reaktor 🔒": m["tag"], "Linia 🔒": kat, "Opakowanie 📦": p, "Udział": f"{udzial_pct:.1f}%",
                        "Źródło %": split_source,
                        "Opakowań [/mies]": int(liczba_sztuk_month), "Palet [/mies] 🧱": int(liczba_palet_month),
                        "Miejsca magazynowe [szt] 📐": int(miejsca_paletowe), "Czas rozlewu strumienia [h] ⏱️": round(czas_rozlewu_h, 1),
                        "Wąskie gardło": "Pompa" if q_pump_m3h < sekcja_nalewania_m3_h else "Sekcja nalewania"
                    })

        st.session_state["logistics_results"] = real_split_rows

        # ============================================================
        # IMPORT — bufor magazynowy dla produktów jeszcze/na stałe importowanych, liczony z
        # rytmu dostaw (częstotliwość + wielkość), a nie z cyklu produkcji. Model zapasu
        # cyklicznego: szczytowy stan magazynu = wielkość 1 dostawy + bufor bezpieczeństwa
        # (bo tuż przed kolejną dostawą bufor bezpieczeństwa wciąż stoi, a nowa dostawa
        # dokłada się na wierzch) - to jest wartość, pod którą trzeba realnie zarezerwować
        # miejsce, nie średnia.
        # ============================================================
        import_pallet_mass_kg = st.session_state.get("import_pallet_mass_kg", 800.0)

        def compute_import_positions(year_idx_for_calc):
            rows, total_positions = [], 0
            if recipes_df_lookup is None or recipes_df_lookup.empty or RECIPE_SOURCING_COL not in recipes_df_lookup.columns:
                return rows, total_positions
            import_rows_df = recipes_df_lookup[recipes_df_lookup[RECIPE_SOURCING_COL] == "Import"]
            for _, r in import_rows_df.iterrows():
                if not is_product_imported_in_year(r.get(RECIPE_SOURCING_COL, "Produkcja własna"),
                                                     r.get(RECIPE_IMPORT_TRANSITION_COL, ""), year_idx_for_calc):
                    continue
                annual_t_target = float(r.get(RECIPE_ANNUAL_COL, 0) or 0)
                frac = get_rampup_fraction(r[RECIPE_GROUP_COL], year_idx_for_calc) if year_idx_for_calc != RAMPUP_YEAR_TARGET_SENTINEL else 1.0
                effective_annual_t = annual_t_target * frac
                daily_t = effective_annual_t / WORKING_DAYS_YEAR if WORKING_DAYS_YEAR > 0 else 0.0
                freq_days = float(r.get(RECIPE_IMPORT_FREQ_COL, 0) or 0)
                lot_t = float(r.get(RECIPE_IMPORT_LOT_COL, 0) or 0)
                safety_days = float(r.get(RECIPE_IMPORT_SAFETY_DAYS_COL, 0) or 0)
                safety_stock_t = safety_days * daily_t
                peak_stock_t = lot_t + safety_stock_t
                deliveries_per_year = math.ceil(effective_annual_t / lot_t) if lot_t > 0 else 0
                miejsca_paletowe_import = math.ceil((peak_stock_t * 1000.0) / import_pallet_mass_kg) if import_pallet_mass_kg > 0 else 0
                rows.append({
                    "Produkt": r[RECIPE_PRODUCT_COL], "Linia": r[RECIPE_GROUP_COL],
                    "Tryb": "Stały import" if r.get(RECIPE_IMPORT_TRANSITION_COL, "") == "Nigdy (stały import)" else r.get(RECIPE_IMPORT_TRANSITION_COL, ""),
                    "Wolumen [t/rok]": round(effective_annual_t, 1),
                    "Częstotliwość dostawy [dni]": freq_days if freq_days > 0 else "—",
                    "Wielkość dostawy [t]": lot_t,
                    "Dostaw/rok": deliveries_per_year,
                    "Bufor bezpieczeństwa [t]": round(safety_stock_t, 2),
                    "Szczytowy zapas [t]": round(peak_stock_t, 2),
                    "Miejsca magazynowe [szt]": int(miejsca_paletowe_import),
                })
                total_positions += miejsca_paletowe_import
            return rows, total_positions

        import_warehouse_rows_view, total_import_positions = compute_import_positions(effective_year_idx_for_import)
        # Baseline "budynku" (target/100%) uwzględnia TYLKO stały import ("Nigdy") - produkty z
        # rokiem przejścia w widoku docelowym są już produkowane, więc ich miejsce liczy fg_positions_target_list.
        import_warehouse_rows_target, total_import_positions_target = compute_import_positions(RAMPUP_YEAR_TARGET_SENTINEL)

        rm_warehouse_rows = st.session_state.get("raw_material_warehouse_rows", [])

        if real_split_rows or rm_warehouse_rows or import_warehouse_rows_view:
            st.markdown("##### 🔀 Wyniki Symulacji Logistyczno-Magazynowej (Wyroby Gotowe, FG)")
            if real_split_rows:
                st.caption("Kolumna **Źródło %** pokazuje, czy rozbicie na opakowania tego wiersza pochodzi z receptury "
                           "(Zakładka 1, per produkt) czy z ręcznego podziału w panelu bocznym (per grupa, gdy receptura "
                           "nie precyzuje opakowań dla tego produktu). Kolumna **Wąskie gardło** pokazuje, czy czas rozlewu "
                           "jest dziś limitowany przez wydajność pompy TEGO reaktora (Zakładka 3), czy przez sekcję głowic nalewczych.")
                st.dataframe(pd.DataFrame(real_split_rows), hide_index=True, use_container_width=True)
            else:
                st.info("ℹ️ W wybranym roku/widoku wszystkie produkty tej floty są jeszcze importowane (patrz sekcja "
                        "'📦 Import' poniżej) — brak własnej produkcji FG do pokazania.")

            # ============================================================
            # IMPORT — produkty importowane w wybranym roku/widoku
            # ============================================================
            if import_warehouse_rows_view:
                st.markdown("##### 📦 Import — Bufor Magazynowy")
                st.caption("Produkty jeszcze (lub na stałe) importowane w wybranym roku/widoku — bufor liczony z rytmu "
                           "dostaw, nie z cyklu produkcji. **Szczytowy zapas** = wielkość 1 dostawy + bufor bezpieczeństwa "
                           "(bo tuż przed kolejną dostawą bufor bezpieczeństwa wciąż stoi w magazynie).")
                import_pallet_mass_kg = st.number_input(
                    "Masa 1 palety importowej [kg]:", min_value=1.0, value=float(import_pallet_mass_kg), step=50.0,
                    key="import_pallet_mass_kg_input",
                    help="Uproszczenie: jedna wspólna masa/paletę dla wszystkich produktów importowanych, do przeliczenia "
                         "szczytowego zapasu [t] na miejsca magazynowe [szt]."
                )
                st.session_state["import_pallet_mass_kg"] = import_pallet_mass_kg
                import_warehouse_rows_view, total_import_positions = compute_import_positions(effective_year_idx_for_import)
                import_warehouse_rows_target, total_import_positions_target = compute_import_positions(RAMPUP_YEAR_TARGET_SENTINEL)
                st.dataframe(pd.DataFrame(import_warehouse_rows_view), hide_index=True, use_container_width=True)
                st.metric("📦 Miejsca magazynowe — Import (ten rok)", f"{total_import_positions} szt.")
            else:
                st.info("ℹ️ Brak produktów importowanych w wybranym roku/widoku (albo brak wgranych receptur z "
                        "'Sposób Pozyskania' = 'Import' w Zakładce 1).")

            # ============================================================
            # SUROWCE (RM) W BECZKACH/IBC/WORKACH — z Zakładki 6, jeśli policzone
            # ============================================================
            if rm_warehouse_rows:
                with st.expander("🧴 Surowce w Beczkach/IBC/Workach (RM) — z Zakładki 6", expanded=False):
                    st.caption("Surowce nietrafiające do zbiorników (Zakładka 5) — te też stoją w tym samym "
                               "magazynie co wyroby gotowe i wliczają się do łącznej powierzchni poniżej.")
                    st.dataframe(pd.DataFrame(rm_warehouse_rows), hide_index=True, use_container_width=True)
            else:
                st.info("ℹ️ Brak policzonych surowców w beczkach/IBC/workach — wgraj receptury (Zakładka 1) i "
                        "odwiedź Zakładkę 6, aby doliczyć ich miejsca magazynowe do bilansu poniżej.")

            # ============================================================
            # PODSUMOWANIE POWIERZCHNI MAGAZYNOWEJ — FG + RM RAZEM (suma miejsc paletowych -> m²)
            # ============================================================
            st.markdown("##### 📐 Podsumowanie Powierzchni Magazynowej (FG + RM, wspólny magazyn)")
            st.caption("Ten sam magazyn przechowuje zarówno wyroby gotowe (FG), jak i surowce nietrafiające do "
                       "zbiorników (RM) — wszystko, co nie stoi w silosie, musi stanąć tutaj. Powierzchnia na "
                       "jedno miejsce paletowe zależy od typu składowania — regały selektywne wymagają więcej "
                       "przestrzeni na alejki niż składowanie blokowe, ale za to (razem z liczbą poziomów poniżej) "
                       "pozwalają postawić więcej palet na tej samej powierzchni podłogi.")

            RACKING_PRESETS_M2 = {
                "Składowanie blokowe (block stacking)": {"m2": 1.3, "poziomy": 2},
                "Regały wjezdne (drive-in)": {"m2": 1.8, "poziomy": 3},
                "Regały paletowe selektywne (standardowe)": {"m2": 3.0, "poziomy": 4},
                "Własna wartość": {"m2": None, "poziomy": None},
            }
            c_wh1, c_wh2, c_wh3 = st.columns(3)
            with c_wh1:
                typ_skladowania = st.selectbox("Typ składowania:", list(RACKING_PRESETS_M2.keys()), index=2, key="typ_skladowania_tab3")
            with c_wh2:
                domyslna_powierzchnia = RACKING_PRESETS_M2[typ_skladowania]["m2"]
                powierzchnia_na_miejsce = st.number_input(
                    "Powierzchnia / miejsce paletowe (1 poziom) [m²]:", min_value=0.5,
                    value=float(domyslna_powierzchnia) if domyslna_powierzchnia is not None else 3.0,
                    step=0.1, disabled=domyslna_powierzchnia is not None,
                    help="Odblokowuje się przy wyborze 'Własna wartość' powyżej. Wartość obejmuje udział alejek i "
                         "dróg transportowych, dla JEDNEGO poziomu składowania (nie całej wysokości regału)."
                )
            with c_wh3:
                domyslne_poziomy = RACKING_PRESETS_M2[typ_skladowania]["poziomy"]
                liczba_poziomow = st.number_input(
                    "Liczba poziomów składowania:", min_value=1, max_value=10,
                    value=int(domyslne_poziomy) if domyslne_poziomy is not None else 3, step=1,
                    disabled=domyslne_poziomy is not None,
                    help="Ile palet w pionie mieści jedno miejsce podłogowe — dla block stackingu to fizyczne "
                         "piętrzenie palet jedna na drugiej (zwykle 2-3), dla regałów to liczba poziomów "
                         "regału (zwykle 3-5). Więcej poziomów = mniejsza wymagana powierzchnia podłogi przy "
                         "tej samej liczbie miejsc paletowych. Wybierz 'Własna wartość' powyżej, aby to odblokować."
                )

            total_fg_positions = sum(r["Miejsca magazynowe [szt] 📐"] for r in real_split_rows)
            rm_rampup_frac = (get_rampup_fraction("__global__", selected_rampup_year_idx)
                               if selected_rampup_year_idx is not None else 1.0)
            total_rm_positions = math.ceil(sum(r["Miejsca magazynowe [szt]"] for r in rm_warehouse_rows) * rm_rampup_frac)
            total_miejsca_magazynowe = total_fg_positions + total_rm_positions + total_import_positions

            # Budynek stawiany RAZ, pod docelową (100%) produkcję — niezależnie od wybranego roku
            # symulacji. RM w rm_warehouse_rows jest już liczone przy 100% (Zakładka 5 nie skaluje
            # rampupem), więc target = suma bez przeliczenia; FG target liczony osobno w pętli wyżej;
            # Import target = TYLKO produkty na stałe importowane ("Nigdy") - te potrzebują miejsca
            # w magazynie nawet w pełnej dojrzałości.
            total_fg_positions_target = sum(fg_positions_target_list)
            total_rm_positions_target = sum(r["Miejsca magazynowe [szt]"] for r in rm_warehouse_rows)
            total_miejsca_magazynowe_target = total_fg_positions_target + total_rm_positions_target + total_import_positions_target
            total_floor_slots_target = math.ceil(total_miejsca_magazynowe_target / liczba_poziomow) if liczba_poziomow > 0 else total_miejsca_magazynowe_target
            total_powierzchnia_m2 = total_floor_slots_target * powierzchnia_na_miejsce

            wykorzystanie_magazynu_pct = (total_miejsca_magazynowe / total_miejsca_magazynowe_target * 100.0) \
                if total_miejsca_magazynowe_target > 0 else 0.0

            m_wh1, m_wh2, m_wh3, m_wh4 = st.columns(4)
            with m_wh1: st.metric("📦 Miejsca paletowe — ten rok (FG + RM + Import)", f"{total_miejsca_magazynowe:,} szt.",
                                   help=f"FG: {total_fg_positions:,} szt. · RM: {total_rm_positions:,} szt. · Import: {total_import_positions:,} szt.")
            with m_wh2: st.metric("🎯 Miejsca paletowe — docelowe (100%)", f"{total_miejsca_magazynowe_target:,} szt.",
                                   help=f"W tym stały import (\"Nigdy\"): {total_import_positions_target:,} szt.")
            with m_wh3: st.metric("📐 Powierzchnia magazynu (budowana pod 100%)", f"{total_powierzchnia_m2:,.0f} m²")
            with m_wh4: st.metric("📊 Wykorzystanie magazynu w tym roku", f"{wykorzystanie_magazynu_pct:.0f}%")

            st.caption("💡 Powierzchnia = ⌈(docelowe miejsca paletowe FG + RM + stały Import) / liczba poziomów⌉ × "
                       "powierzchnia/miejsce (1 poziom) — budynek stawiany RAZ, pod pełną (100%) zdolność. "
                       "Bufor **surowców w zbiornikach** (silosy) jest liczony i wymiarowany osobno w Zakładce 5. "
                       f"Powierzchnia budynku pozostaje wymiarowana pod 100% celu niezależnie od wybranego roku — "
                       f"zmienia się tylko pokazane wykorzystanie ({selected_rampup_year_label}).")

            # ============================================================
            # WYSYŁKI — ile trzeba wysyłać dziennie, żeby magazyn WG nie rósł ponad projektową
            # rotację, i co się dzieje, jeśli realne wysyłki są mniejsze od sugerowanych.
            # ============================================================
            st.markdown("---")
            st.markdown("##### 🚚 Wysyłki — Utrzymanie Optymalnego Poziomu Magazynu")
            st.caption("Magazyn jest zaprojektowany pod rotację **{:.0f} dni** (pole 'Czas składowania palety' powyżej) "
                       "— żeby jej dotrzymać, tyle samo palet WG musi dziennie WYJEŻDŻAĆ, ile średnio dziennie "
                       "PRZYBYWA z produkcji. Poniżej: sugerowane tempo wysyłek w tym roku/widoku, oraz co się "
                       "dzieje, jeśli realne wysyłki są od niego mniejsze.".format(czas_skladowania_dni))

            total_palety_month_fg = sum(r["Palet [/mies] 🧱"] for r in real_split_rows)
            suggested_pallets_per_day = (total_palety_month_fg / dni_robocze_miesiac) if dni_robocze_miesiac > 0 else 0.0

            c_ship1, c_ship2 = st.columns(2)
            with c_ship1:
                pallets_per_truck = st.number_input(
                    "Palet na 1 wysyłkę (naczepa/kontener) [szt]:", min_value=1, value=33, step=1, key="pallets_per_truck",
                    help="Typowa naczepa standardowa mieści ~33 palety EUR — dostosuj do realnego taboru."
                )
            with c_ship2:
                suggested_trucks_per_day = suggested_pallets_per_day / pallets_per_truck if pallets_per_truck > 0 else 0.0
                st.metric("📦 Sugerowane wysyłki / dzień (ten rok)", f"{suggested_trucks_per_day:.2f} wysyłki/dzień",
                          help=f"= {suggested_pallets_per_day:.1f} palet/dzień ({total_palety_month_fg:.0f} palet/mies. ÷ "
                               f"{dni_robocze_miesiac:.1f} dni roboczych/mies.)")

            actual_trucks_per_day = st.number_input(
                "Rzeczywiste/planowane wysyłki / dzień:", min_value=0.0,
                value=round(suggested_trucks_per_day, 2), step=0.5, key="actual_trucks_per_day",
                help="Domyślnie ustawione na wartość sugerowaną — zmień, żeby zobaczyć skutek wysyłania mniej (lub więcej) niż potrzeba."
            )
            actual_pallets_per_day = actual_trucks_per_day * pallets_per_truck
            gap_pallets_per_day = suggested_pallets_per_day - actual_pallets_per_day

            if actual_trucks_per_day <= 0:
                st.warning("⚠️ Przy zerowych wysyłkach magazyn WG napełni się od zera do pełnej pojemności w "
                           f"**{(total_fg_positions_target / suggested_pallets_per_day):.0f} dni roboczych** "
                           "(przy tempie produkcji z wybranego roku) — i dalej rosnąć, bez odpływu.")
            elif gap_pallets_per_day > 0.001:
                effective_rotation_days = czas_skladowania_dni * (suggested_pallets_per_day / actual_pallets_per_day)
                # Ile miejsc podłogowych zajmie magazyn WG, jeśli realnie rotacja wydłuża się do effective_rotation_days
                # zamiast projektowych czas_skladowania_dni - proporcjonalnie do dziennego niedoboru wysyłek.
                fg_positions_at_actual_rate = math.ceil(total_fg_positions_target * (effective_rotation_days / czas_skladowania_dni)) \
                    if czas_skladowania_dni > 0 else total_fg_positions_target
                extra_positions_needed = max(fg_positions_at_actual_rate - total_fg_positions_target, 0)
                spare_capacity = max(total_miejsca_magazynowe_target - total_miejsca_magazynowe, 0)
                days_to_overflow = (spare_capacity / gap_pallets_per_day) if gap_pallets_per_day > 0 else float("inf")

                st.error(f"🔴 Wysyłasz **{gap_pallets_per_day:.1f} palety/dzień mniej** niż sugerowane — magazyn WG "
                         f"rośnie ponad projekt. Efektywna rotacja wydłuża się z {czas_skladowania_dni:.0f} do "
                         f"~**{effective_rotation_days:.0f} dni**, co odpowiada ok. **{extra_positions_needed:,} dodatkowym "
                         f"miejscom paletowym** ponad dzisiejszy projekt budynku. Przy obecnym zapasie wolnej "
                         f"powierzchni ({spare_capacity:,} miejsc w tym roku/widoku) magazyn **przepełni się za "
                         f"~{days_to_overflow:.0f} dni roboczych**, jeśli nic się nie zmieni.")
            else:
                st.success(f"🟢 Planowane wysyłki ({actual_trucks_per_day:.2f}/dzień) pokrywają lub przewyższają "
                           f"sugerowane tempo — magazyn WG powinien utrzymać projektową rotację "
                           f"{czas_skladowania_dni:.0f} dni.")

            # ============================================================
            # SYMULACJA STANU MAGAZYNOWEGO W CZASIE (60 miesięcy = 5 lat rozruchu): jak zapas
            # WG będzie się zmieniał w zależności od PLANOWANEJ PRODUKCJI (krzywa rozruchu) przy
            # ZAŁOŻONYM TEMPIE WYSYŁEK (pole "Rzeczywiste/planowane wysyłki/dzień" powyżej) - sam
            # poziom wysyłek na wykresie POMIJAMY (jest już ujęty w komunikacie ostrzegawczym
            # powyżej) i pokazujemy tylko wynikowy stan magazynowy, razem z jego wartością.
            # ============================================================
            st.markdown("###### 📈 Symulacja Stanu Magazynowego — 5 lat")
            st.caption("Zgodnie z planowaną produkcją (krzywa rozruchu z Zakładki 2) i wysyłkami ustawionymi "
                       "powyżej: jak zmienia się stan magazynowy WG w palet oraz jego wartość, na tle projektowej "
                       "pojemności budynku.")

            total_palety_month_fg_target = sum(fg_pallets_target_list)
            target_annual_t_ship = sum(m["annual_volume"] for m in mixers_fleet) / 1000.0
            shipped_pallets_month_assumed = actual_pallets_per_day * dni_robocze_miesiac
            fg_capacity_pallets = total_fg_positions_target

            # Przelicznik palety -> kg -> koszt, do wyceny zapasu. Koszt/kg pochodzi z Zakładki 6
            # (per grupa produktowa), ważony rzeczywistym miksem produkcji tej floty; jeśli
            # Zakładka 6 nie była jeszcze skonfigurowana w tej sesji, używana jest wartość domyślna.
            target_monthly_mass_kg_total = sum(m["batches_count"] * m["mass_per_batch"] for m in mixers_fleet)
            avg_kg_per_pallet = (target_monthly_mass_kg_total / total_palety_month_fg_target) if total_palety_month_fg_target > 0 else 0.0
            manuf_cost_per_group_stock = st.session_state.get("manuf_cost_per_group", {})
            total_annual_volume_kg = sum(m["annual_volume"] for m in mixers_fleet)
            avg_manuf_cost_per_kg = (sum(m["annual_volume"] * manuf_cost_per_group_stock.get(m["product_family"], 2.12) for m in mixers_fleet)
                                      / total_annual_volume_kg) if total_annual_volume_kg > 0 else 2.12
            waluta_stock = st.selectbox("Waluta wyceny zapasu:", ["PLN", "EUR", "USD"], key="waluta_stock_value")
            if not manuf_cost_per_group_stock:
                st.caption(f"ℹ️ Koszt produkcyjny per grupa nie był jeszcze ustawiany w Zakładce 6 — użyto wartości "
                           f"domyślnej ({avg_manuf_cost_per_kg:.2f} {waluta_stock}/kg). Ustaw go w Zakładce 6, aby wycena była dokładniejsza.")

            stock_rows = []
            stock_level = 0.0
            for yi in range(RAMPUP_YEARS):
                year_tonnage_t = sum((m["annual_volume"] / 1000.0) * get_rampup_fraction(m["product_family"], yi)
                                      for m in mixers_fleet)
                frac_yi = (year_tonnage_t / target_annual_t_ship) if target_annual_t_ship > 0 else 0.0
                production_pallets_month_yi = total_palety_month_fg_target * frac_yi

                for mi in range(1, 13):
                    stock_level = max(stock_level + production_pallets_month_yi - shipped_pallets_month_assumed, 0.0)
                    wartosc_zapasu = stock_level * avg_kg_per_pallet * avg_manuf_cost_per_kg
                    stock_rows.append({
                        "Miesiąc": yi * 12 + mi, "Okres": f"Rok {yi + 1}, mies. {mi}",
                        "Stan magazynowy [pal]": stock_level,
                        "Pojemność FG [pal]": fg_capacity_pallets,
                        f"Wartość zapasu [{waluta_stock}]": wartosc_zapasu,
                    })

            df_stock = pd.DataFrame(stock_rows)

            st.markdown(f"**Stan magazynowy [palety]** (na tle projektowej pojemności FG = {fg_capacity_pallets:,.0f} palet)")
            st.line_chart(df_stock.set_index("Miesiąc")[["Stan magazynowy [pal]", "Pojemność FG [pal]"]])

            st.markdown(f"**Wartość zapasu [{waluta_stock}]** (koszt produkcyjny × ilość magazynowana)")
            st.line_chart(df_stock.set_index("Miesiąc")[[f"Wartość zapasu [{waluta_stock}]"]])

            v_c1, v_c2, v_c3 = st.columns(3)
            with v_c1:
                st.metric("💰 Wartość zapasu — koniec Roku 1", f"{df_stock.iloc[11][f'Wartość zapasu [{waluta_stock}]']:,.0f} {waluta_stock}")
            with v_c2:
                st.metric("💰 Wartość zapasu — koniec Roku 5", f"{df_stock.iloc[-1][f'Wartość zapasu [{waluta_stock}]']:,.0f} {waluta_stock}")
            with v_c3:
                st.metric("📈 Szczytowa wartość zapasu", f"{df_stock[f'Wartość zapasu [{waluta_stock}]'].max():,.0f} {waluta_stock}")

            if stock_level > fg_capacity_pallets:
                st.error(f"🔴 Przy tych założeniach stan magazynowy po 5 latach ({stock_level:,.0f} palet) "
                         f"**przekracza** projektową pojemność FG ({fg_capacity_pallets:,.0f} palet) — wysyłki nie "
                         f"nadążają za rozruchem produkcji.")
            else:
                st.success(f"🟢 Przy tych założeniach stan magazynowy po 5 latach ({stock_level:,.0f} palet) mieści "
                           f"się w projektowej pojemności FG ({fg_capacity_pallets:,.0f} palet).")
        else:
            st.info("Brak skonfigurowanego podziału opakowań o niezerowym udziale — uzupełnij procenty w panelu bocznym, "
                    "albo (dla produktów importowanych) uzupełnij dane importu w Zakładce 1.")

# ==========================================
# ZAKŁADKA 6: ANALIZA FINANSOWA, CAPEX I ROI (tab4)
# ==========================================
with tab4:
    st.header("💰 Analiza Finansowa, CAPEX i ROI")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Najpierw zatwierdź flotę w Zakładce 2.")
    else:
        waluta = st.selectbox("Wybierz walutę operacyjną:", ["PLN", "EUR", "USD"])

        st.markdown("### 💵 Krok 1: Koszt Produkcyjny per Grupa")
        st.caption("Koszt produkcyjny (surowce + robocizna + narzut, bez energii - tę liczymy osobno niżej z realnej "
                   "hydrauliki/bilansu cieplnego) różni się między grupami produktowymi — podaj go osobno dla "
                   "każdej aktywnej linii.")
        if "manuf_cost_per_group" not in st.session_state:
            st.session_state.manuf_cost_per_group = {}
        active_groups_fin = sorted(set(m["product_family"] for m in st.session_state.confirmed_mixers))
        cost_cols = st.columns(min(len(active_groups_fin), 4)) if active_groups_fin else []
        for i, grp in enumerate(active_groups_fin):
            with cost_cols[i % len(cost_cols)]:
                default_cost = st.session_state.manuf_cost_per_group.get(grp, 2.12)
                st.session_state.manuf_cost_per_group[grp] = st.number_input(
                    f"{grp} [{waluta}/kg]:", min_value=0.01, value=float(default_cost), step=0.05,
                    format="%.3f", key=f"manuf_cost_{grp}"
                )

        st.markdown("---")
        st.markdown("### ⚡ Krok 2: Koszty Energii i Bilans Miesięczny")
        cena_mwh = st.number_input(f"Cena energii elektrycznej [{waluta}/MWh]:", min_value=1.0, value=750.0)
        st.session_state["cena_mwh_tab4"] = cena_mwh

        if not st.session_state.calculated_times:
            st.info("ℹ️ Skonfiguruj urządzenia w Zakładce 3, aby koszty energii odzwierciedlały rzeczywistą hydraulikę i bilans cieplny "
                    "(w przeciwnym razie poniżej używane są bezpieczne wartości domyślne).")

        # Cena i sprawność "paliwa grzewczego" (gaz lub prąd, zależnie od wyboru kotła w Zakładce 2)
        # — używana zarówno do kosztu ogrzewania, jak i do wyceny odzysku ciepła (fizycznie
        # spójniej niż stosowanie ogólnej ceny elektrycznej do oszczędności cieplnej).
        heating_fuel_price = st.session_state.get("cena_mwh_tab4", cena_mwh)
        heating_fuel_efficiency = st.session_state.get("sprawnosc_kotla_frac", 0.98)
        if st.session_state.get("typ_kotla") == "Gazowy":
            heating_fuel_price = st.session_state.get("cena_gazu_mwh", 250.0)
        heating_fuel_price = heating_fuel_price if heating_fuel_price else cena_mwh
        heating_fuel_efficiency = heating_fuel_efficiency if heating_fuel_efficiency else 1.0

        financial_summary = []
        total_monthly_saving_thermal = 0.0
        total_base_manuf_cost = 0.0
        total_energy_cost_el = 0.0
        calculated_times = st.session_state.get("calculated_times", {})

        for mixer in st.session_state.confirmed_mixers:
            tag = mixer["tag"]
            kat = mixer["product_family"]
            prod_info = st.session_state.active_portfolio[kat]
            m_monthly_kg = mixer["annual_volume"] / MONTHS_PER_YEAR
            batches_per_month = mixer["batches_count"]
            manuf_cost_per_kg_kat = st.session_state.manuf_cost_per_group.get(kat, 2.12)

            # POPRAWKA: te dane teraz faktycznie pochodzą z Zakładki 2 (patrz zapis do
            # st.session_state.calculated_times w pętli obliczeniowej Zakładki 2).
            # Wartości domyślne poniżej są używane wyłącznie, jeśli użytkownik jeszcze
            # nie odwiedził Zakładki 2 dla danego urządzenia.
            m_data = calculated_times.get(tag, {"power_mix_kw": 5.5, "power_pump_kw": 1.5, "heating": 1.5, "pumping": 0.75, "t_max_mix": 60.0, "t_rozlew": 30.0})

            mixing_energy = m_data["power_mix_kw"] * mixer.get("cycle_h", prod_info["cycle_h"]) * batches_per_month
            pumping_energy = m_data["power_pump_kw"] * m_data["pumping"] * batches_per_month
            cost_el = ((mixing_energy + pumping_energy) / 1000.0) * cena_mwh
            total_energy_cost_el += cost_el

            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg_kat
            total_base_manuf_cost += base_manuf_cost_monthly

            oszczednosc_cieplna = 0.0
            if m_data["t_rozlew"] < m_data["t_max_mix"]:
                oszczednosc_cieplna = ((m_monthly_kg * prod_info["cp"] * (m_data["t_max_mix"] - m_data["t_rozlew"])) / 3_600_000.0) * heating_fuel_price / heating_fuel_efficiency
                total_monthly_saving_thermal += oszczednosc_cieplna

            financial_summary.append({
                "Reaktor": tag, "Linia": kat, "Miesięczny tonaż [kg]": int(m_monthly_kg),
                "Koszt Prod. [kg]": manuf_cost_per_kg_kat,
                "Energia Mieszania [kWh]": round(mixing_energy, 1), "Energia Pompowania [kWh]": round(pumping_energy, 1),
                "Koszt prądu": f"{cost_el:.2f} {waluta}", "Odzysk ciepła": f"- {oszczednosc_cieplna:.2f} {waluta}",
                "Źródło danych": "Zakładka 3" if tag in calculated_times else "Wartości domyślne"
            })

        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, use_container_width=True)

        koszt_paliwa_grzewczego = st.session_state.get("koszt_paliwa_grzewczego_month", 0.0)
        if koszt_paliwa_grzewczego > 0:
            typ_kotla_disp = st.session_state.get("typ_kotla", "—")
            st.metric(label=f"🔥 Koszt paliwa grzewczego ({typ_kotla_disp}, z Zakładki 2)",
                      value=f"{koszt_paliwa_grzewczego:,.2f} {waluta}")
        else:
            st.info("ℹ️ Skonfiguruj kocioł i typ paliwa w Zakładce 3 (sekcja 'Dobór Kotła Grzewczego'), aby doliczyć "
                    "koszt ogrzewania do kosztu wytworzenia.")

        # Koszt energii elektrycznej PROCESU (silniki, kocioł elektryczny, chłodzenie przez COP)
        # i odbiorów POZAPRODUKCYJNYCH (serwery, HVAC, oświetlenie, sprężarkownia) - z sekcji ⚡
        # Zakładki 3, dotąd NIEUWZGLĘDNIANE tutaj (liczono tylko mieszanie/pompowanie powyżej).
        # Rozbite na dwa koszty CELOWO: proces skaluje się z wolumenem produkcji (krok 4, ROI
        # z rozruchem), odbiory pozaprodukcyjne są w przybliżeniu STAŁE niezależnie od tego,
        # ile realnie produkujesz w danym roku (światło/HVAC/serwery działają tak samo).
        process_demand_kw = st.session_state.get("process_demand_kw", 0.0)
        facility_demand_kw = st.session_state.get("facility_demand_kw", 0.0)
        godziny_rocznie_zakladu = godziny_dziennie * WORKING_DAYS_YEAR
        koszt_energii_proces_month = ((process_demand_kw * godziny_rocznie_zakladu) / 1000.0 / MONTHS_PER_YEAR) * cena_mwh
        koszt_energii_facility_month = ((facility_demand_kw * godziny_rocznie_zakladu) / 1000.0 / MONTHS_PER_YEAR) * cena_mwh
        if process_demand_kw > 0 or facility_demand_kw > 0:
            c_en3, c_en4 = st.columns(2)
            with c_en3:
                st.metric("⚙️ Energia — proces (skaluje się z rozruchem)", f"{koszt_energii_proces_month:,.2f} {waluta}/mies.")
            with c_en4:
                st.metric("🏢 Energia — pozaprodukcyjne (stałe, z Zakładki 3)", f"{koszt_energii_facility_month:,.2f} {waluta}/mies.")
        else:
            st.info("ℹ️ Skonfiguruj sekcję ⚡ 'Zapotrzebowanie na Moc Elektryczną' w Zakładce 3, aby doliczyć pełny "
                    "koszt energii procesowej i pozaprodukcyjnej (dziś liczone tylko mieszanie/pompowanie powyżej).")

        # Część kosztu, która skaluje się z wolumenem produkcji (a więc z krzywą rozruchu w Kroku 4)
        variable_monthly_opex_target = (total_base_manuf_cost + total_energy_cost_el + koszt_paliwa_grzewczego
                                         + koszt_energii_proces_month - total_monthly_saving_thermal)
        # Część kosztu w przybliżeniu STAŁA niezależnie od roku rozruchu (odbiory pozaprodukcyjne)
        fixed_monthly_opex = koszt_energii_facility_month

        final_cost = variable_monthly_opex_target + fixed_monthly_opex
        st.metric(label="🚀 CAŁKOWITY KOSZT WYTWORZENIA (Miesięcznie, przy 100% celu)", value=f"{final_cost:,.2f} {waluta}")

        st.info("💡 Pełna analiza czasu cyklu szarży (dozowanie, grzanie, homogenizacja, QC, pompowanie, chłodzenie, "
                "rozlew) oraz rekomendacja liczby zmian znajdują się w **Zakładce 7 (Mapa Strumienia Wartości)**, "
                "razem z resztą analizy czasu procesu.")

        st.markdown("---")
        st.markdown("### 🧰 Krok 3: CAPEX — Cennik i Standardowa Instalacja")
        st.caption("Zdefiniuj listę komponentów standardowej instalacji per grupa produktowa (pompy, czujniki, "
                   "zawory, elektrozawory itd.) wraz z cenami jednostkowymi — treść zwykle przepisana z Twojego "
                   "istniejącego P&ID danej instalacji standardowej. Podaj, ile takich instalacji planujesz, "
                   "a aplikacja przeliczy szacunkowy CAPEX. Cennik wgrywasz ponownie, gdy ceny się zmienią.")

        equipment_template_bytes = generate_equipment_template_bytes()
        st.download_button(
            label="⬇️ Pobierz szablon Excel (Cennik_Instalacji_Szablon.xlsx)",
            data=equipment_template_bytes,
            file_name="Cennik_Instalacji_Szablon.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_download_equipment_template"
        )

        uploaded_equipment_file = st.file_uploader("Wybierz plik .xlsx z cennikiem instalacji:", type=["xlsx"], key="equipment_uploader")

        if uploaded_equipment_file is not None:
            parsed_eq_df, eq_errors = parse_equipment_excel(uploaded_equipment_file)
            for err in eq_errors:
                st.warning(f"⚠️ {err}")
            if parsed_eq_df is not None and not parsed_eq_df.empty:
                st.session_state.equipment_df = parsed_eq_df
                st.success(f"✅ Wczytano {len(parsed_eq_df)} pozycji cennika.")
            elif parsed_eq_df is None:
                st.error("❌ Nie udało się wczytać żadnych poprawnych pozycji z tego pliku — popraw błędy powyżej i wgraj ponownie.")

        total_capex = 0.0
        if st.session_state.equipment_df is not None and not st.session_state.equipment_df.empty:
            edited_eq_df = st.data_editor(
                st.session_state.equipment_df, hide_index=True, use_container_width=True,
                num_rows="dynamic", key="equipment_data_editor",
                column_config={EQUIPMENT_GROUP_COL: st.column_config.SelectboxColumn(options=RECIPE_PRODUCT_GROUPS)}
            )
            edited_eq_df[EQUIPMENT_LINE_TOTAL_COL] = edited_eq_df[EQUIPMENT_QTY_COL] * edited_eq_df[EQUIPMENT_UNIT_PRICE_COL]
            st.session_state.equipment_df = edited_eq_df

            groups_in_price_list = sorted(edited_eq_df[EQUIPMENT_GROUP_COL].dropna().unique().tolist())

            # Domyślna liczba instalacji = liczba unikalnych produktów danej grupy w recepturach
            # wgranych w Zakładce 1, jeśli są dostępne - w przeciwnym razie 1.
            default_counts_from_recipes = {}
            if st.session_state.recipes_df is not None and not st.session_state.recipes_df.empty:
                default_counts_from_recipes = st.session_state.recipes_df.groupby(RECIPE_GROUP_COL)[RECIPE_PRODUCT_COL].nunique().to_dict()

            cols_counts = st.columns(min(len(groups_in_price_list), 4)) if groups_in_price_list else []
            for i, grp in enumerate(groups_in_price_list):
                with cols_counts[i % len(cols_counts)]:
                    default_val = int(st.session_state.equipment_install_counts.get(grp, default_counts_from_recipes.get(grp, 1)))
                    st.session_state.equipment_install_counts[grp] = st.number_input(
                        f"{grp} — instalacji:", min_value=0, value=default_val, step=1, key=f"eq_count_{grp}"
                    )

            capex_rows = []
            for grp in groups_in_price_list:
                n_install = st.session_state.equipment_install_counts.get(grp, 0)
                grp_df = edited_eq_df[edited_eq_df[EQUIPMENT_GROUP_COL] == grp]
                per_install_cost = grp_df[EQUIPMENT_LINE_TOTAL_COL].sum()
                group_total = per_install_cost * n_install
                total_capex += group_total
                currencies = grp_df[EQUIPMENT_CURRENCY_COL].dropna().unique().tolist()
                currency_label = currencies[0] if len(currencies) == 1 else "/".join(currencies) if currencies else "—"
                capex_rows.append({
                    "Grupa Produktowa": grp, "Komponentów w cenniku": len(grp_df),
                    "Koszt 1 instalacji": round(per_install_cost, 2), "Liczba instalacji": n_install,
                    "CAPEX grupy": round(group_total, 2), "Waluta": currency_label,
                })

            st.dataframe(pd.DataFrame(capex_rows), hide_index=True, use_container_width=True)
            st.metric("💰 Łączny szacowany CAPEX (wszystkie grupy)", f"{total_capex:,.0f}")

            with st.expander("📋 Szczegółowa lista komponentów per grupa", expanded=False):
                for grp in groups_in_price_list:
                    st.markdown(f"**{grp}**")
                    st.dataframe(edited_eq_df[edited_eq_df[EQUIPMENT_GROUP_COL] == grp].drop(columns=[EQUIPMENT_GROUP_COL]),
                                 hide_index=True, use_container_width=True)
        else:
            st.info("💡 Wgraj cennik powyżej, aby zobaczyć tu podsumowanie CAPEX per grupa produktowa.")

        st.markdown("---")
        st.markdown("### 📈 Krok 4: ROI (z uwzględnieniem krzywej rozruchu)")
        st.caption("Przychód liczony jako koszt wytworzenia powiększony o zadaną marżę — 'koszt plus'. "
                   "**OPEX skaluje się z tą samą 5-letnią krzywą rozruchu co w Zakładce 2**: część kosztu, która "
                   "rośnie z wolumenem (surowce/robocizna, energia procesowa, paliwo grzewcze), jest mnożona przez "
                   "% celu danego roku; odbiory pozaprodukcyjne (serwery/HVAC/oświetlenie/sprężarkownia) liczone są "
                   "jako w przybliżeniu stałe, bo działają niezależnie od tempa produkcji.")
        marza_pct = st.number_input("Marża narzucona na koszt wytworzenia [%]:", min_value=0.0, value=20.0, step=1.0, key="roi_marza_pct")

        # Ta sama ważona (wolumenem) krzywa rozruchu co w Zakładce 2 - liczona tu od nowa na
        # bazie confirmed_mixers, żeby ROI nie zależało od tego, czy użytkownik odwiedził
        # Zakładkę 2 w tej samej sesji przeglądarki.
        target_annual_t_fin = sum(m["annual_volume"] for m in st.session_state.confirmed_mixers) / 1000.0
        roi_rows = []
        cumulative_profit = 0.0
        payback_year_fraction = None
        for i in range(RAMPUP_YEARS):
            year_tonnage_t = sum((m["annual_volume"] / 1000.0) * get_rampup_fraction(m["product_family"], i)
                                  for m in st.session_state.confirmed_mixers)
            frac_year = (year_tonnage_t / target_annual_t_fin) if target_annual_t_fin > 0 else 1.0

            annual_variable_opex = variable_monthly_opex_target * frac_year * MONTHS_PER_YEAR
            annual_fixed_opex = fixed_monthly_opex * MONTHS_PER_YEAR
            annual_opex_year = annual_variable_opex + annual_fixed_opex
            annual_revenue_year = annual_opex_year * (1.0 + marza_pct / 100.0)
            annual_profit_year = annual_revenue_year - annual_opex_year

            profit_before = cumulative_profit
            cumulative_profit += annual_profit_year
            if payback_year_fraction is None and total_capex > 0 and cumulative_profit >= total_capex:
                # Interpolacja liniowa w obrębie roku, żeby okres zwrotu nie skakał "co pełny rok".
                needed = total_capex - profit_before
                payback_year_fraction = i + (needed / annual_profit_year if annual_profit_year > 0 else 0.0)

            roi_rows.append({
                "Rok": f"Rok {i + 1}", "% Celu": f"{frac_year * 100.0:.0f}%",
                "OPEX roczny": round(annual_opex_year, 0), "Przychód roczny": round(annual_revenue_year, 0),
                "Zysk roczny": round(annual_profit_year, 0), "Zysk skumulowany": round(cumulative_profit, 0),
                "ROI (ten rok) [%]": round((annual_profit_year / total_capex * 100.0), 1) if total_capex > 0 else None,
            })

        st.dataframe(pd.DataFrame(roi_rows), hide_index=True, use_container_width=True)

        chart_cum = pd.DataFrame({
            "Rok": [r["Rok"] for r in roi_rows],
            "Zysk skumulowany": [r["Zysk skumulowany"] for r in roi_rows],
            "CAPEX": [total_capex] * len(roi_rows),
        }).set_index("Rok")
        st.line_chart(chart_cum)

        r_c1, r_c2, r_c3, r_c4 = st.columns(4)
        with r_c1:
            st.metric("💰 OPEX w Roku 1 (rozruch)", f"{roi_rows[0]['OPEX roczny']:,.0f} {waluta}")
        with r_c2:
            st.metric("💵 Zysk w Roku 5 (pełna dojrzałość)", f"{roi_rows[-1]['Zysk roczny']:,.0f} {waluta}")
        with r_c3:
            roi_year5 = roi_rows[-1]["ROI (ten rok) [%]"]
            st.metric("🎯 ROI w Roku 5 (ustabilizowane)", f"{roi_year5:.1f}%" if roi_year5 is not None else "—")
        with r_c4:
            if total_capex <= 0:
                st.metric("⏳ Okres zwrotu (z rozruchem)", "—", help="Uzupełnij cennik CAPEX w Kroku 3 powyżej.")
            elif payback_year_fraction is not None:
                st.metric("⏳ Okres zwrotu (z rozruchem)", f"{payback_year_fraction:.1f} lat")
            else:
                st.metric("⏳ Okres zwrotu (z rozruchem)", f"> {RAMPUP_YEARS} lat",
                          help="Skumulowany zysk nie pokrywa CAPEX nawet w Roku 5 przy obecnych założeniach.")

        if total_capex <= 0:
            st.info("ℹ️ ROI wymaga policzonego CAPEX — uzupełnij cennik instalacji w Kroku 3 powyżej.")

# ==========================================
# ZAKŁADKA 5: PARK ZBIORNIKÓW (TANK FARM) (tab5)
# ==========================================
with tab5:
    st.header("🛢️ Logistyka Surowcowa i Grupy Magazynowe (Tank Farm)")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych technicznych. Uruchom konfigurację w Zakładce 2.")
    else:
        days_of_stock = st.number_input("Wymagany zapas bezpieczeństwa surowca [dni]:", min_value=5, value=14)
        st.session_state["days_of_stock_tab5"] = days_of_stock
        selected_tank_capacity_m3 = st.selectbox("Wybierz pojemność pojedynczego silosu [m³]:", [30, 50, 60, 80, 100, 150, 200], index=4)

        st.markdown("### 📋 Zestawienie Surowcowe Floty (per Reaktor)")
        st.caption("Rozkład bazy olejowej / wody DEMI per reaktor, na podstawie grupy oleju przypisanej do jego linii "
                   "produktowej — kontekst fleetowy, niezależny od tego, czy wgrałeś recepturę.")

        active_chemical_ratio = st.slider("Średni udział fazy ciekłej (baza + woda) w recepturze [%]:", 50, 95, 85) / 100.0

        raw_material_summary = []
        silos_aggregation = {"Mineralne (Gr. I/II)": 0.0, "Syntetyczne (Gr. III/IV)": 0.0, "Woda Procesowa DEMI": 0.0, "Inne / Pakiety płynne": 0.0}

        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = st.session_state.active_portfolio[kat]
            total_liquid_tony = (mixer["annual_volume"] / 1000.0) * active_chemical_ratio

            water_annual = total_liquid_tony * prod_info["water_content"]
            oil_annual = total_liquid_tony * (1.0 - prod_info["water_content"]) if prod_info["oil_group"] != "Brak (Specjalistyczne)" else 0.0
            other_liquid = total_liquid_tony - water_annual - oil_annual

            silos_aggregation["Woda Procesowa DEMI"] += water_annual
            if oil_annual > 0: silos_aggregation[prod_info["oil_group"]] += oil_annual
            silos_aggregation["Inne / Pakiety płynne"] += other_liquid

            raw_material_summary.append({
                "ID Reaktora 🔒": mixer["tag"], "Linia 🔒": kat, "Typ Bazy": prod_info["oil_group"],
                "Produkcja [t/rok]": round(mixer["annual_volume"]/1000.0, 1), "Baza Olejowa [t/rok]": round(oil_annual, 1), "Woda DEMI [t/rok]": round(water_annual, 1)
            })

        st.dataframe(pd.DataFrame(raw_material_summary), hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🏢 Wymiarowanie Silosów Magazynowych")

        recipe_consumption = st.session_state.get("recipe_raw_material_consumption")
        has_recipe_consumption = bool(recipe_consumption) and any(v > 0 for v in recipe_consumption.values())

        if has_recipe_consumption:
            st.caption("Liczone **per pojedynczy surowiec** (np. osobno Base Oil II i Base Oil III) na podstawie "
                       "receptur wgranych w **Zakładce 1**. Dla każdego surowca sprawdzane jest też (a) czy fizycznie/"
                       "praktycznie nadaje się do magazynowania luzem w zbiorniku, oraz (b) czy roczne zużycie "
                       "przekracza próg opłacalności dedykowanego zbiornika — jeśli oba warunki są spełnione, "
                       "proponowany jest zbiornik o określonej pojemności; w przeciwnym razie beczki/IBC/worki.")

            c_thr1, c_thr2 = st.columns(2)
            with c_thr1:
                prog_zbiornika_t = st.number_input(
                    "Próg rocznego zużycia do zbiornika dedykowanego [t/rok]:", min_value=1.0, value=50.0, step=5.0,
                    key="prog_zbiornika_tab6",
                    help="Poniżej tego wolumenu zbiornik dedykowany zwykle się nie zwraca — surowiec zostaje w "
                         "beczkach/IBC, nawet jeśli fizycznie nadaje się do magazynowania luzem."
                )
            with c_thr2:
                st.caption(f"Zapas bezpieczeństwa i pojemność silosu jak ustawione powyżej ({days_of_stock:.0f} dni, "
                           f"{selected_tank_capacity_m3} m³).")

            STANDARD_SMALL_TANK_SIZES_M3 = [5, 10, 15, 20, 30, 50, 60, 80, 100, 150, 200]

            recipe_silos_rows = []
            recipe_total_tanks = 0
            drummed_materials = []  # surowce NIE trafiające do zbiornika - potrzebują miejsca w magazynie
            for material, annual_tony in sorted(recipe_consumption.items(), key=lambda x: -x[1]):
                if annual_tony <= 0:
                    continue
                info = RAW_MATERIAL_STORAGE_INFO.get(material, {"bulk_eligible": True, "note": "Brak danych - domyślnie traktowany jak ciecz magazynowalna luzem."})
                bulk_ok = info["bulk_eligible"]
                recommend_tank = bulk_ok and annual_tony >= prog_zbiornika_t

                daily_t = annual_tony / WORKING_DAYS_YEAR
                if recommend_tank:
                    required_m3 = (daily_t * days_of_stock) / OIL_FILL_FACTOR
                    needed_tanks = math.ceil(required_m3 / (selected_tank_capacity_m3 * TANK_SAFETY_FILL))
                    recommended_capacity = next((s for s in STANDARD_SMALL_TANK_SIZES_M3 if s >= required_m3 / TANK_SAFETY_FILL), required_m3 / TANK_SAFETY_FILL)
                    recipe_total_tanks += needed_tanks
                    rekomendacja = f"🛢️ Zbiornik dedykowany ({recommended_capacity:.0f} m³)"
                    uzasadnienie = f"Zużycie {annual_tony:.1f} t/rok ≥ próg {prog_zbiornika_t:.0f} t/rok, nadaje się do magazynowania luzem."
                    bufor_txt = f"{required_m3:.1f}"
                    silosy_txt = f"{needed_tanks} szt."
                else:
                    rekomendacja = "🧴 Beczki / IBC / worki"
                    uzasadnienie = info["note"] if not bulk_ok else f"Zużycie {annual_tony:.1f} t/rok < próg {prog_zbiornika_t:.0f} t/rok — zbiornik się nie opłaca."
                    bufor_txt = "—"
                    silosy_txt = "—"
                    drummed_materials.append({"material": material, "annual_tony": annual_tony, "info": info})

                recipe_silos_rows.append({
                    "Surowiec": material, "Konsumpcja [t/rok]": round(annual_tony, 2),
                    "Wymagany Bufor [m³]": bufor_txt, "Liczba silosów": silosy_txt,
                    "Rekomendacja": rekomendacja, "Uzasadnienie": uzasadnienie,
                })

            st.dataframe(pd.DataFrame(recipe_silos_rows), hide_index=True, use_container_width=True)
            m_silo1, m_silo2 = st.columns(2)
            with m_silo1:
                st.metric("🧱 Całkowita liczba silosów (surowce w zbiornikach)", f"{recipe_total_tanks} szt.")
            with m_silo2:
                n_drums = sum(1 for r in recipe_silos_rows if "Beczki" in r["Rekomendacja"])
                st.metric("🧴 Surowce zostające w beczkach/IBC", f"{n_drums} / {len(recipe_silos_rows)}")

            st.markdown("---")
            st.markdown("### 📦 Magazynowanie Surowców w Beczkach/IBC/Workach")
            st.caption("Surowce, które nie trafiają do zbiornika (powyżej), i tak muszą stanąć w magazynie — "
                       "przypisz każdemu typ pojemnika, a aplikacja przeliczy liczbę pojemników/palet/miejsc "
                       "magazynowych. Wynik doliczy się do **łącznej powierzchni magazynowej w Zakładce 4** "
                       "razem z wyrobami gotowymi (FG) — to jeden, wspólny magazyn.")

            if drummed_materials:
                if "rm_container_assignment" not in st.session_state:
                    st.session_state.rm_container_assignment = {}
                rm_container_rows = []
                for dm in drummed_materials:
                    mat, ann_t, info = dm["material"], dm["annual_tony"], dm["info"]
                    default_container = st.session_state.rm_container_assignment.get(
                        mat, default_rm_container_for(mat, info))
                    rm_container_rows.append({"Surowiec": mat, "Konsumpcja [t/rok]": round(ann_t, 2),
                                               "Typ pojemnika": default_container})

                edited_rm_containers = st.data_editor(
                    pd.DataFrame(rm_container_rows), hide_index=True, use_container_width=True,
                    disabled=["Surowiec", "Konsumpcja [t/rok]"], key="rm_container_editor",
                    column_config={"Typ pojemnika": st.column_config.SelectboxColumn(options=list(RM_CONTAINER_TYPES.keys()))}
                )
                for _, row in edited_rm_containers.iterrows():
                    st.session_state.rm_container_assignment[row["Surowiec"]] = row["Typ pojemnika"]

                dni_robocze_miesiac_rm = WORKING_DAYS_YEAR / MONTHS_PER_YEAR
                rm_warehouse_rows = []
                for dm in drummed_materials:
                    mat, ann_t = dm["material"], dm["annual_tony"]
                    container_name = st.session_state.rm_container_assignment.get(mat, "Beczka 200 kg (ciecz)")
                    container_cfg = RM_CONTAINER_TYPES[container_name]
                    monthly_kg = (ann_t * 1000.0) / MONTHS_PER_YEAR
                    n_containers_month = math.ceil(monthly_kg / container_cfg["capacity_kg"]) if container_cfg["capacity_kg"] > 0 else 0
                    n_pallets_month = math.ceil(n_containers_month / container_cfg["per_pallet"])
                    miejsca_paletowe_rm = math.ceil((n_pallets_month / dni_robocze_miesiac_rm) * days_of_stock)
                    rm_warehouse_rows.append({
                        "Surowiec 🔒": mat, "Typ pojemnika 🔒": container_name,
                        "Pojemników [/mies]": int(n_containers_month), "Palet [/mies]": int(n_pallets_month),
                        "Miejsca magazynowe [szt]": int(miejsca_paletowe_rm),
                    })

                st.dataframe(pd.DataFrame(rm_warehouse_rows), hide_index=True, use_container_width=True)
                total_rm_pallet_positions = sum(r["Miejsca magazynowe [szt]"] for r in rm_warehouse_rows)
                st.metric("📦 Miejsca magazynowe surowców (RM)", f"{total_rm_pallet_positions} szt.")
                st.session_state["raw_material_warehouse_rows"] = rm_warehouse_rows
            else:
                st.info("Wszystkie surowce z receptur trafiają do zbiorników — brak surowców do magazynowania w beczkach/IBC/workach.")
                st.session_state["raw_material_warehouse_rows"] = []
        else:
            st.info("💡 Wgraj receptury produktów w **Zakładce 1**, aby uzyskać dokładniejsze wymiarowanie per "
                    "pojedynczy surowiec. Poniżej uproszczony szacunek grupowy (wg typu bazy z floty).")

            silos_rows = []
            total_tanks = 0
            for group_name, annual_tony in silos_aggregation.items():
                if annual_tony > 0:
                    daily_t = annual_tony / WORKING_DAYS_YEAR
                    fill_factor = WATER_FILL_FACTOR if "Woda" in group_name else OIL_FILL_FACTOR
                    required_m3 = (daily_t * days_of_stock) / fill_factor
                    needed_tanks = math.ceil(required_m3 / (selected_tank_capacity_m3 * TANK_SAFETY_FILL))
                    total_tanks += needed_tanks
                    silos_rows.append({
                        "Grupa Surowcowa": group_name, "Konsumpcja [t/rok]": round(annual_tony, 1), "Wymagany Bufor [m³]": round(required_m3, 1), "Liczba silosów": f"{needed_tanks} szt."
                    })
            st.dataframe(pd.DataFrame(silos_rows), hide_index=True, use_container_width=True)
            st.metric("🧱 Całkowita wymagana liczba silosów surowcowych (szacunek grupowy)", f"{total_tanks} szt.")

# ==========================================
# ZAKŁADKA 7: MAPA STRUMIENIA WARTOŚCI (VSM) (tab6)
# ==========================================
with tab6:
    st.header("🧵 Mapa Strumienia Wartości (Value Stream Mapping)")
    st.caption("Ta zakładka **nie liczy niczego od nowa** — składa w jeden łańcuch czasy już policzone w Zakładkach 2-5 "
               "(hydraulika/bilans cieplny, rozlew, bufory magazynowe), więc automatycznie aktualizuje się razem z nimi.")

    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Najpierw zatwierdź flotę w Zakładce 2.")
    else:
        rodziny_w_flocie = sorted(set(m["product_family"] for m in st.session_state.confirmed_mixers))
        selected_vsm_family = st.selectbox("Wybierz linię produktową do mapowania:", rodziny_w_flocie, key="vsm_family_select")

        # --- KONFIGURACJA PANELU ZWOLNIENIA QC ---
        st.markdown("##### 🧪 Panel testów QC do zwolnienia szarży")
        st.caption("Wybierz testy z katalogu laboratoryjnego wchodzące w standardowy panel zwolnienia dla tej linii. "
                   "Czasy trwania są edytowalnymi wartościami domyślnymi — popraw je na rzeczywiste, jeśli różnią się w Twoim laboratorium.")

        if "vsm_qc_config" not in st.session_state:
            st.session_state.vsm_qc_config = {}
        qc_cfg = st.session_state.vsm_qc_config.setdefault(selected_vsm_family, {
            "tests": ["Lepkość kinematyczna @40°C", "Barwa ASTM", "Temp. zapłonu - tygiel otwarty"],
            "mode": "Sekwencyjnie (jeden technik, jedno stanowisko)",
            "custom_durations": {},
        })

        c_qc1, c_qc2 = st.columns([2, 1])
        with c_qc1:
            qc_cfg["tests"] = st.multiselect(
                "Testy w panelu zwolnienia:", list(QC_TEST_CATALOG.keys()),
                default=[t for t in qc_cfg["tests"] if t in QC_TEST_CATALOG],
                key=f"qc_tests_{selected_vsm_family}"
            )
        with c_qc2:
            qc_cfg["mode"] = st.radio(
                "Sposób wykonania:",
                ["Sekwencyjnie (jeden technik, jedno stanowisko)", "Równolegle (kilku techników / aparatów)"],
                index=0 if qc_cfg["mode"].startswith("Sekw") else 1,
                key=f"qc_mode_{selected_vsm_family}"
            )

        if qc_cfg["tests"]:
            df_qc = pd.DataFrame([{
                "Test": t,
                "Czas [min]": qc_cfg["custom_durations"].get(t, QC_TEST_CATALOG[t]["duration_min"]),
                "Sprzęt": QC_TEST_CATALOG[t]["equipment"],
            } for t in qc_cfg["tests"]])

            edited_qc = st.data_editor(
                df_qc, hide_index=True, use_container_width=True,
                disabled=["Test", "Sprzęt"], key=f"qc_dur_editor_{selected_vsm_family}"
            )
            for _, r in edited_qc.iterrows():
                qc_cfg["custom_durations"][r["Test"]] = float(r["Czas [min]"])

            durations_min = [qc_cfg["custom_durations"][t] for t in qc_cfg["tests"]]
            qc_time_h = (sum(durations_min) if qc_cfg["mode"].startswith("Sekw") else max(durations_min)) / 60.0
        else:
            qc_time_h = 0.0
            st.info("Brak wybranych testów — czas zwolnienia QC przyjęto jako 0h.")

        # Kolejka laboratoryjna: czas oczekiwania próbki na wolne stanowisko/technika,
        # ODDZIELNY od czasu samego wykonania testów (qc_time_h powyżej).
        if "vsm_qc_queue_days" not in st.session_state:
            st.session_state.vsm_qc_queue_days = {}
        qc_queue_days = st.number_input(
            "⏳ Kolejka laboratoryjna przed rozpoczęciem testów [dni]:", min_value=0.0,
            value=float(st.session_state.vsm_qc_queue_days.get(selected_vsm_family, 0.0)), step=0.5,
            key=f"qc_queue_{selected_vsm_family}"
        )
        st.session_state.vsm_qc_queue_days[selected_vsm_family] = qc_queue_days

        st.markdown("---")

        # --- CZASY PROCESOWE DLA WYBRANEJ RODZINY (średnia z floty tej linii, z Zakładki 2) ---
        mixers_in_family = [m for m in st.session_state.confirmed_mixers if m["product_family"] == selected_vsm_family]
        calc_times_family = [st.session_state.calculated_times.get(m["tag"]) for m in mixers_in_family]
        calc_times_family = [c for c in calc_times_family if c is not None]

        if not calc_times_family:
            st.info("ℹ️ Skonfiguruj hydraulikę i bilans cieplny dla tej linii w Zakładce 3, aby uzyskać rzeczywiste czasy "
                    "grzania/pompowania/chłodzenia (poniżej użyto bezpiecznych wartości domyślnych).")
            heating_h, pumping_h, cooling_h = 1.5, 0.75, 0.5
        else:
            heating_h = sum(c["heating"] for c in calc_times_family) / len(calc_times_family)
            pumping_h = sum(c["pumping"] for c in calc_times_family) / len(calc_times_family)
            cooling_h = sum(c.get("cooling_h", 0.0) for c in calc_times_family) / len(calc_times_family)

        # --- DOZOWANIE / HOMOGENIZACJA: konfiguracja per urządzenie, przeniesiona tu z Zakładki 4 ---
        # (dawniej wpisywana w Zakładce 4 i odczytywana przez klucz widgetu — jeśli nikt nie odwiedził
        # tamtej zakładki dla danej rodziny, VSM cicho używał wartości domyślnych; teraz to jest
        # jedyne miejsce konfiguracji tych czasów).
        st.markdown("##### ⏱️ Dozowanie i Homogenizacja (per urządzenie)")
        for mixer in mixers_in_family:
            tag = mixer["tag"]
            defaults_bt = st.session_state.batch_time_components.setdefault(tag, {"dosing": 1.0, "homog": 2.0})
            with st.expander(f"⏱️ Składniki czasu operacyjnego dla: {tag}", expanded=(len(mixers_in_family) == 1)):
                defaults_bt["dosing"] = st.number_input(
                    "Dozowanie surowców [h]:", min_value=0.1, value=float(defaults_bt["dosing"]), key=f"vsm_tdos_{tag}")
                defaults_bt["homog"] = st.number_input(
                    "Homogenizacja właściwa [h]:", min_value=0.1, value=float(defaults_bt["homog"]), key=f"vsm_thom_{tag}")

        dosing_vals = [st.session_state.batch_time_components[m["tag"]]["dosing"] for m in mixers_in_family]
        homog_vals = [st.session_state.batch_time_components[m["tag"]]["homog"] for m in mixers_in_family]
        t_dosing = sum(dosing_vals) / len(dosing_vals)
        t_homog = sum(homog_vals) / len(homog_vals)

        # Czas rozlewu — suma po opakowaniach dla tej rodziny, z Zakładki 3.
        logistics_rows = st.session_state.get("logistics_results", [])
        filling_h = sum(r["Czas rozlewu strumienia [h] ⏱️"] for r in logistics_rows if r["Linia 🔒"] == selected_vsm_family)
        if filling_h == 0.0:
            st.info("ℹ️ Skonfiguruj podział opakowań w panelu bocznym i odwiedź Zakładkę 3, aby uzyskać rzeczywisty czas rozlewu dla tej rodziny.")

        # Bufory magazynowe — założenia globalne z Zakładek 3 i 5 (te wejścia nie są dziś różnicowane per rodzina).
        raw_material_buffer_days = st.session_state.get("days_of_stock_tab5", 14)
        fg_storage_days = st.session_state.get("czas_skladowania_tab3", 14)

        HOURS_PER_DAY = 24.0
        raw_material_buffer_h = raw_material_buffer_days * HOURS_PER_DAY
        fg_storage_h = fg_storage_days * HOURS_PER_DAY
        qc_queue_h = qc_queue_days * HOURS_PER_DAY

        process_steps = [
            {"name": "Dozowanie", "hours": t_dosing, "value_added": True},
            {"name": "Grzanie", "hours": heating_h, "value_added": True},
            {"name": "Homogenizacja", "hours": t_homog, "value_added": True},
            {"name": "Zwolnienie QC", "hours": qc_time_h, "value_added": False, "extra_wait_h": qc_queue_h},
            {"name": "Pompowanie", "hours": pumping_h, "value_added": True},
            {"name": "Chłodzenie", "hours": cooling_h, "value_added": True},
            {"name": "Rozlew", "hours": filling_h, "value_added": True},
        ]
        for s in process_steps:
            s.setdefault("extra_wait_h", 0.0)

        # --- OEE: C/O, Uptime, Dostępność, Pass rate per etap (edytowalne, domyślnie neutralne) ---
        st.markdown("##### ⚙️ Zmiana, Dostępność i Jakość per Etap (OEE)")
        st.caption("Domyślnie C/O=0h i Uptime/Dostępność/Pass=100% (brak strat) — popraw na wartości rzeczywiste tam, "
                   "gdzie mają znaczenie (typowo: Grzanie/Homogenizacja przy zmianie produktu w reaktorze, oraz Rozlew "
                   "przy zmianie SKU na linii pakującej). **C/O jest wliczane do Lead Time** — zajmuje realny czas "
                   "na reaktorze/linii, nawet jeśli księgowane jest jako strata, a nie czas procesu.")

        if "vsm_oee" not in st.session_state:
            st.session_state.vsm_oee = {}
        oee_cfg = st.session_state.vsm_oee.setdefault(selected_vsm_family, {})
        for s in process_steps:
            oee_cfg.setdefault(s["name"], {"co_h": 0.0, "uptime_pct": 100.0, "availability_pct": 100.0, "pass_pct": 100.0})

        # Dostępność wyliczona z MTBF/MTTR (Zakładka 3, karta maszyn) — średnia dla mieszalników
        # tej rodziny, ważona liczbą szarż/miesiąc (urządzenia bardziej obciążone mają większy
        # wpływ na realną dostępność linii). Dotyczy etapów, w których fizycznie bierze udział
        # reaktor i/lub pompa (Dozowanie/Grzanie/Homogenizacja/Pompowanie/Chłodzenie) — Zwolnienie
        # QC i Rozlew korzystają z innych zasobów (laboratorium, linia pakująca), nieujętych tu.
        reactor_pump_steps = ["Dozowanie", "Grzanie", "Homogenizacja", "Pompowanie", "Chłodzenie"]
        mtbf_weighted_avail, mtbf_weight_sum = 0.0, 0.0
        for mx in mixers_in_family:
            ct_mx = st.session_state.calculated_times.get(mx["tag"])
            if ct_mx is not None and "availability_pct" in ct_mx:
                w = max(mx.get("batches_count", 1), 1)
                mtbf_weighted_avail += ct_mx["availability_pct"] * w
                mtbf_weight_sum += w
        mtbf_derived_availability_pct = (mtbf_weighted_avail / mtbf_weight_sum) if mtbf_weight_sum > 0 else None

        c_avail1, c_avail2 = st.columns([3, 1])
        with c_avail1:
            if mtbf_derived_availability_pct is not None:
                st.caption(f"📟 Dostępność wyliczona z MTBF/MTTR (Zakładka 3, ważona liczbą szarż) dla tej rodziny: "
                           f"**{mtbf_derived_availability_pct:.1f}%**. Dotyczy etapów: {', '.join(reactor_pump_steps)}.")
            else:
                st.caption("ℹ️ Skonfiguruj MTBF/MTTR w Zakładce 3 (karta maszyn, sekcja 🔧 Niezawodność), aby móc "
                           "podstawić tu wyliczoną dostępność zamiast wpisywać ją ręcznie.")
        with c_avail2:
            if st.button("🔄 Zastosuj wyliczoną Dostępność", key=f"apply_mtbf_avail_{selected_vsm_family}",
                          disabled=mtbf_derived_availability_pct is None, use_container_width=True):
                for step_name in reactor_pump_steps:
                    oee_cfg[step_name]["availability_pct"] = round(mtbf_derived_availability_pct, 1)
                st.rerun()

        df_oee_in = pd.DataFrame([{
            "Etap": s["name"],
            "C/T [h]": round(s["hours"], 2),
            "C/O [h]": oee_cfg[s["name"]]["co_h"],
            "Uptime [%]": oee_cfg[s["name"]]["uptime_pct"],
            "Dostępność [%]": oee_cfg[s["name"]]["availability_pct"],
            "Pass [%]": oee_cfg[s["name"]]["pass_pct"],
        } for s in process_steps])

        edited_oee = st.data_editor(
            df_oee_in, hide_index=True, use_container_width=True,
            disabled=["Etap", "C/T [h]"], key=f"oee_editor_{selected_vsm_family}",
            column_config={
                "Uptime [%]": st.column_config.NumberColumn(min_value=0.0, max_value=100.0),
                "Dostępność [%]": st.column_config.NumberColumn(min_value=0.0, max_value=100.0),
                "Pass [%]": st.column_config.NumberColumn(min_value=0.0, max_value=100.0),
                "C/O [h]": st.column_config.NumberColumn(min_value=0.0),
            }
        )
        for _, r in edited_oee.iterrows():
            oee_cfg[r["Etap"]] = {
                "co_h": float(r["C/O [h]"]),
                "uptime_pct": float(r["Uptime [%]"]),
                "availability_pct": float(r["Dostępność [%]"]),
                "pass_pct": float(r["Pass [%]"]),
            }

        for s in process_steps:
            o = oee_cfg[s["name"]]
            s["co_h"] = o["co_h"]
            s["oee_pct"] = (o["uptime_pct"] / 100.0) * (o["availability_pct"] / 100.0) * (o["pass_pct"] / 100.0) * 100.0

        st.markdown("---")

        # --- WIDOK: szczegółowy (7 etapów) lub zbiorczy (4 etapy, jak w dashboardzie referencyjnym) ---
        widok = st.radio(
            "Widok:", ["Szczegółowy (7 etapów)", "Zbiorczy (4 etapy, jak w dashboardzie referencyjnym)"],
            horizontal=True, key=f"vsm_widok_{selected_vsm_family}"
        )

        if widok.startswith("Szczegółowy"):
            display_steps = [{
                "name": s["name"], "hours": s["hours"], "value_added": s["value_added"],
                "co_h": s["co_h"], "wait_h": s["extra_wait_h"], "oee_pct": s["oee_pct"],
            } for s in process_steps]
            lead_start_wait = ("Bufor surowców", raw_material_buffer_h)
            lead_end_wait = ("Bufor wyrobów gotowych", fg_storage_h)
        else:
            # Grupowanie 4 makro-etapów zgodnie z układem dashboardu referencyjnego.
            def group_stats(names):
                members = [s for s in process_steps if s["name"] in names]
                ct_h = sum(m["hours"] for m in members)
                co_h = sum(m["co_h"] for m in members)
                wait_h = sum(m["extra_wait_h"] for m in members)
                va = any(m["value_added"] for m in members)
                if ct_h > 0:
                    uptime = sum(oee_cfg[m["name"]]["uptime_pct"] * m["hours"] for m in members) / ct_h
                    avail = sum(oee_cfg[m["name"]]["availability_pct"] * m["hours"] for m in members) / ct_h
                else:
                    uptime = avail = 100.0
                pass_combined = 100.0
                for m in members:
                    pass_combined *= oee_cfg[m["name"]]["pass_pct"] / 100.0
                pass_combined *= 100.0
                oee_pct = (uptime / 100.0) * (avail / 100.0) * (pass_combined / 100.0) * 100.0
                return {"hours": ct_h, "co_h": co_h, "wait_h": wait_h, "value_added": va, "oee_pct": oee_pct}

            blending = group_stats(["Dozowanie", "Grzanie", "Homogenizacja", "Pompowanie", "Chłodzenie"])
            qc_group = group_stats(["Zwolnienie QC"])
            filling_group = group_stats(["Rozlew"])

            display_steps = [
                {"name": "Blending/Cooking", **blending},
                {"name": "QC", **qc_group},
                {"name": "Filling/Packing", **filling_group},
            ]
            lead_start_wait = ("Receiving & Staging", raw_material_buffer_h)
            lead_end_wait = (None, 0.0)  # bufor WG dołączony do Filling/Packing, jak w dashboardzie referencyjnym
            display_steps[-1]["wait_h"] += fg_storage_h

        total_process_h = sum(s["hours"] for s in display_steps)
        total_co_h = sum(s["co_h"] for s in display_steps)
        total_wait_h = lead_start_wait[1] + lead_end_wait[1] + sum(s["wait_h"] for s in display_steps)
        value_added_h = sum(s["hours"] for s in display_steps if s["value_added"])
        total_lead_time_h = total_process_h + total_co_h + total_wait_h
        pce_pct = (value_added_h / total_lead_time_h * 100.0) if total_lead_time_h > 0 else 0.0

        st.markdown("### 📈 Kluczowe Metryki Strumienia Wartości")
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1: st.metric("⏳ Całkowity Lead Time", f"{total_lead_time_h / 24.0:.1f} dni")
        with m2: st.metric("⚙️ Czas przetwarzania (VA)", f"{value_added_h:.1f} h")
        with m3: st.metric("🔄 Suma C/O", f"{total_co_h:.1f} h")
        with m4: st.metric("🎯 Process Cycle Efficiency", f"{pce_pct:.1f}%")
        with m5: st.metric("🧪 Czas zwolnienia QC", f"{qc_time_h:.2f} h")

        if pce_pct < 10.0 and total_lead_time_h > 0:
            st.warning("⚠️ PCE poniżej 10% jest typowe dla procesów wsadowych z dużym buforowaniem magazynowym — "
                       "największa dźwignia poprawy leży zwykle w skróceniu dni bufora surowców/wyrobów gotowych "
                       "lub kolejki laboratoryjnej, a nie w przyspieszaniu samego procesu w reaktorze.")

        # --- DIAGRAM VSM: proste boksy/strzałki w HTML+CSS (bez zależności od graphviz) ---
        st.markdown("### 🗺️ Diagram Strumienia Wartości")

        def render_box(title, ct_txt, co_h=0.0, oee_pct=None, va=True):
            color = "#2E7D32" if va else "#B45309"
            bg = "#E8F5E9" if va else "#FEF3C7"
            extra = f'<div style="font-size:10px; color:#555;">C/O {co_h:.2f}h</div>' if co_h > 0 else ""
            oee_line = f'<div style="font-size:10px; color:#555;">OEE {oee_pct:.0f}%</div>' if oee_pct is not None else ""
            return (f'<div style="border:2px solid {color}; border-radius:6px; padding:8px 10px; min-width:118px; '
                    f'text-align:center; background:{bg}; flex-shrink:0;">'
                    f'<div style="font-size:12px; font-weight:600; color:#111;">{title}</div>'
                    f'<div style="font-size:14px; font-weight:700; color:{color};">{ct_txt}</div>{extra}{oee_line}</div>')

        def render_triangle(label, days_txt):
            return (f'<div style="display:flex; flex-direction:column; align-items:center; flex-shrink:0; margin:0 4px;">'
                    f'<div style="width:0; height:0; border-left:20px solid transparent; border-right:20px solid transparent; '
                    f'border-bottom:34px solid #FDE68A;"></div>'
                    f'<div style="font-size:11px; font-weight:600; margin-top:2px; white-space:nowrap;">{label} {days_txt}</div></div>')

        def render_arrow():
            return '<div style="display:flex; align-items:center; padding:0 2px; flex-shrink:0; color:#555; font-size:18px;">➜</div>'

        pieces = [render_triangle(lead_start_wait[0], f"{lead_start_wait[1] / 24.0:.0f} dni"), render_arrow()]
        for s in display_steps:
            pieces.append(render_box(s["name"], f"{s['hours']:.2f} h", co_h=s["co_h"], oee_pct=s.get("oee_pct"), va=s["value_added"]))
            if s.get("wait_h", 0.0) > 0:
                pieces.append(render_arrow())
                pieces.append(render_triangle("oczekiwanie", f"{s['wait_h'] / 24.0:.1f} dni"))
            pieces.append(render_arrow())
        if lead_end_wait[0] is not None:
            pieces.append(render_triangle(lead_end_wait[0], f"{lead_end_wait[1] / 24.0:.0f} dni"))
        else:
            pieces.pop()  # usuń ostatnią, niepotrzebną strzałkę, gdy nie ma końcowego bufora

        diagram_html = f'<div style="display:flex; align-items:center; overflow-x:auto; padding:14px 4px;">{"".join(pieces)}</div>'
        st.markdown(diagram_html, unsafe_allow_html=True)

        st.caption("🟢 Zielone pola = czas dodający wartość (przetwarzanie produktu). 🟠 Pomarańczowe pola = czas "
                   "niedodający wartości bezpośrednio produktowi (kontrola jakości, magazynowanie) — often konieczny "
                   "operacyjnie, ale to właśnie tu zwykle leży potencjał skrócenia lead time. **C/O** i **OEE** "
                   "pokazane pod nazwą etapu, gdy dotyczy.")

        # --- DRABINKA CZASU: pełny rozkład lead time vs. czas przetwarzania ---
        st.markdown("### ⏱️ Drabinka Czasu (Lead Time vs. Czas Przetwarzania)")
        ladder_rows = [{"Etap": lead_start_wait[0], "Waiting [dni]": round(lead_start_wait[1] / 24.0, 2),
                        "C/T [h]": 0.0, "C/O [h]": 0.0, "Typ": "Magazynowanie"}]
        for s in display_steps:
            ladder_rows.append({
                "Etap": s["name"], "Waiting [dni]": round(s.get("wait_h", 0.0) / 24.0, 2),
                "C/T [h]": round(s["hours"], 2), "C/O [h]": round(s["co_h"], 2),
                "Typ": "Wartość dodana" if s["value_added"] else "Kontrola / Oczekiwanie"
            })
        if lead_end_wait[0] is not None:
            ladder_rows.append({"Etap": lead_end_wait[0], "Waiting [dni]": round(lead_end_wait[1] / 24.0, 2),
                                 "C/T [h]": 0.0, "C/O [h]": 0.0, "Typ": "Magazynowanie"})

        df_ladder = pd.DataFrame(ladder_rows)
        st.dataframe(df_ladder, hide_index=True, use_container_width=True)

        total_waiting_days = df_ladder["Waiting [dni]"].sum()
        total_ct_days = df_ladder["C/T [h]"].sum() / 24.0
        total_co_days = df_ladder["C/O [h]"].sum() / 24.0
        st.markdown(
            f"**TOTAL** — Waiting: `{total_waiting_days:.2f} dni` · C/T: `{total_ct_days:.2f} dni` · "
            f"C/O: `{total_co_days:.2f} dni` · **Lead Time: `{(total_waiting_days + total_ct_days + total_co_days):.2f} dni`** · "
            f"**VA ratio: `{pce_pct:.1f}%`**"
        )

# ==========================================
# ==========================================
# ZAKŁADKA 7: RECEPTURY PRODUKTÓW (import z Excela)
# ==========================================
with tab7:
    st.header("📋 Receptury Produktów: Import z Excela")
    st.caption("Wgraj plik Excel z listą produktów (przypisanych do grupy produktowej), rocznym zapotrzebowaniem "
               "i dozowaniem surowców [kg/t] (bazy olejowe, dodatki, pakiety, zagęszczacze, smary stałe, woda DEMI, "
               "biocyd). Dane z tej zakładki zasilają dodatkowo wymiarowanie silosów **per surowiec** w Zakładce 5 "
               "oraz podpowiedź, dla których surowców opłaca się dedykowany zbiornik, a które lepiej zostawić "
               "w beczkach/IBC/workach.")

    st.markdown("### 📥 Krok 1: Pobierz szablon")
    st.caption("Szablon zawiera dokładną strukturę kolumn wymaganą przez aplikację (nie zmieniaj nazw/kolejności "
               "kolumn), listę rozwijaną grup produktowych, dwa przykładowe wiersze pokazujące format oraz formuły "
               "kontrolne — 'Suma Udziałów Składników' podświetla się na czerwono, jeśli odbiega od 1000 kg/t o "
               "więcej niż tolerancja, a 'Roczne Zapotrzebowanie Surowcowe' wylicza się z uwzględnieniem strat "
               "procesowych. Dodatkowy arkusz 'Opakowania' pozwala predefiniować typy opakowań i ich pojemności — "
               "opcjonalny, wypełniony domyślnymi wartościami z aplikacji, można dopisać nowe wiersze lub zostawić bez zmian.")

    template_bytes = generate_recipe_template_bytes()
    st.download_button(
        label="⬇️ Pobierz szablon Excel (Receptury_Szablon.xlsx)",
        data=template_bytes,
        file_name="Receptury_Szablon.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_download_recipe_template"
    )

    st.markdown("---")
    st.markdown("### 📤 Krok 2: Wgraj uzupełniony plik")
    uploaded_recipe_file = st.file_uploader(
        "Wybierz plik .xlsx z recepturami:", type=["xlsx"], key="recipe_uploader"
    )

    if uploaded_recipe_file is not None:
        uploaded_recipe_file.seek(0)
        parsed_df, parse_errors = parse_recipe_excel(uploaded_recipe_file)

        if parse_errors:
            for err in parse_errors:
                st.warning(f"⚠️ {err}")

        if parsed_df is not None and not parsed_df.empty:
            st.session_state.recipes_df = parsed_df
            st.success(f"✅ Wczytano {len(parsed_df)} poprawnych receptur produktowych.")
        elif parsed_df is None:
            st.error("❌ Nie udało się wczytać żadnych poprawnych receptur z tego pliku — popraw błędy powyżej i wgraj ponownie.")

        # Opcjonalny arkusz 'Opakowania' w tym samym pliku - jeśli obecny, nadpisuje/uzupełnia
        # domyślne typy opakowań i ich pojemności (Zakładki 1 i 3), z zachowaniem edycji w apce.
        uploaded_recipe_file.seek(0)
        packaging_result, packaging_errors = parse_packaging_excel(uploaded_recipe_file)
        for err in packaging_errors:
            st.warning(f"⚠️ {err}")
        if packaging_result is not None:
            st.session_state.pack_configs.update(packaging_result["pack_configs"])
            if "filling_lines_config" not in st.session_state:
                st.session_state.filling_lines_config = {}
            st.session_state.filling_lines_config.update(packaging_result["filling_defaults"])
            st.success(f"✅ Wczytano/zaktualizowano {len(packaging_result['pack_configs'])} typów opakowań z arkusza '{PACKAGING_SHEET_NAME}'.")

    st.markdown("---")

    if st.session_state.recipes_df is not None and not st.session_state.recipes_df.empty:
        st.markdown("### 📊 Krok 3: Wczytane receptury (edytowalne)")
        st.caption("Możesz jeszcze poprawić wartości tutaj przed przeliczeniem — zmiany nie są zapisywane z powrotem "
                   "do pliku Excel, tylko do tej sesji aplikacji. 'Suma Udziałów Składników' i 'Roczne Zapotrzebowanie "
                   "Surowcowe' przeliczają się na żywo pod tabelą.")

        edited_recipes_df = st.data_editor(
            st.session_state.recipes_df,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="recipes_data_editor",
            column_config={
                RECIPE_GROUP_COL: st.column_config.SelectboxColumn(options=RECIPE_PRODUCT_GROUPS),
                RECIPE_SOURCING_COL: st.column_config.SelectboxColumn(options=RECIPE_SOURCING_OPTIONS),
                RECIPE_IMPORT_TRANSITION_COL: st.column_config.SelectboxColumn(options=[""] + RECIPE_IMPORT_TRANSITION_OPTIONS),
            }
        )
        st.session_state.recipes_df = edited_recipes_df

        # Przeliczenie kolumn wyliczanych na żywo po edycji w tabeli (niezależnie od tego,
        # co ewentualnie zostało wpisane ręcznie w tych kolumnach w Excelu).
        edited_recipes_df[RECIPE_SUM_COL] = edited_recipes_df[RECIPE_RAW_MATERIALS].sum(axis=1)
        loss_safe = edited_recipes_df[RECIPE_LOSS_COL].clip(lower=0, upper=99.9)
        edited_recipes_df[RECIPE_RAW_DEMAND_COL] = edited_recipes_df[RECIPE_ANNUAL_COL] / (1.0 - loss_safe / 100.0)

        edited_recipes_df[RECIPE_BATCH_MASS_COL] = edited_recipes_df[RECIPE_MIXER_VOL_COL] * 1000.0 * edited_recipes_df[RECIPE_DENSITY_COL]
        edited_recipes_df[RECIPE_BATCHES_YEAR_COL] = 0.0
        has_bm = edited_recipes_df[RECIPE_BATCH_MASS_COL] > 0
        edited_recipes_df.loc[has_bm, RECIPE_BATCHES_YEAR_COL] = (
            edited_recipes_df.loc[has_bm, RECIPE_ANNUAL_COL] * 1000.0 / edited_recipes_df.loc[has_bm, RECIPE_BATCH_MASS_COL])
        edited_recipes_df[RECIPE_UTILIZATION_COL] = 0.0
        has_ah = edited_recipes_df[RECIPE_AVAIL_HOURS_COL] > 0
        edited_recipes_df.loc[has_ah, RECIPE_UTILIZATION_COL] = (
            edited_recipes_df.loc[has_ah, RECIPE_BATCHES_YEAR_COL] * edited_recipes_df.loc[has_ah, RECIPE_CYCLE_COL]
            / edited_recipes_df.loc[has_ah, RECIPE_AVAIL_HOURS_COL] * 100.0)

        bad_sum_live = edited_recipes_df[(edited_recipes_df[RECIPE_SUM_COL] - RECIPE_TARGET_SUM_KG).abs() > RECIPE_SUM_TOLERANCE_KG]
        if not bad_sum_live.empty:
            zle_produkty = ", ".join(f"{p} ({s:.0f} kg/t)" for p, s in zip(bad_sum_live[RECIPE_PRODUCT_COL], bad_sum_live[RECIPE_SUM_COL]))
            st.error(f"❌ Suma dozowania surowców odbiega od 1000 kg/t (± {RECIPE_SUM_TOLERANCE_KG:.0f} kg) dla: "
                     f"{zle_produkty}. Popraw przed dalszą analizą.")

        overloaded_live = edited_recipes_df[edited_recipes_df[RECIPE_UTILIZATION_COL] > RECIPE_UTILIZATION_WARN_PCT]
        if not overloaded_live.empty:
            zle_mieszalniki = ", ".join(f"{p} ({u:.0f}%)" for p, u in zip(overloaded_live[RECIPE_PRODUCT_COL], overloaded_live[RECIPE_UTILIZATION_COL]))
            st.warning(f"⚠️ Wykorzystanie mieszalnika powyżej {RECIPE_UTILIZATION_WARN_PCT:.0f}% dla: {zle_mieszalniki} — "
                       f"rozważ większy zbiornik, krótszy cykl, więcej zmian roboczych, lub kolejny mieszalnik.")

        st.markdown("---")
        st.markdown("### 🧮 Krok 4: Zagregowane roczne zużycie surowców")
        st.caption("Roczne zużycie surowca = Σ (roczne zapotrzebowanie SUROWCOWE produktu [t], czyli już z doliczonymi "
                   "stratami procesowymi × jego dozowanie [kg/t] / 1000), sumowane po wszystkich wgranych produktach.")

        consumption_tony = {}
        for mat in RECIPE_RAW_MATERIALS:
            consumption_tony[mat] = (edited_recipes_df[RECIPE_RAW_DEMAND_COL] * (edited_recipes_df[mat] / 1000.0)).sum()

        st.session_state.recipe_raw_material_consumption = consumption_tony

        consumption_rows = [
            {"Surowiec": mat, "Zużycie [t/rok]": round(t, 2)}
            for mat, t in sorted(consumption_tony.items(), key=lambda x: -x[1]) if t > 0
        ]
        if consumption_rows:
            st.dataframe(pd.DataFrame(consumption_rows), hide_index=True, use_container_width=True)
        else:
            st.info("Wszystkie dozowania [kg/t] są obecnie zerowe — sprawdź dane w tabeli powyżej.")

        total_annual_t_recipes = edited_recipes_df[RECIPE_ANNUAL_COL].sum()
        total_raw_demand_t = edited_recipes_df[RECIPE_RAW_DEMAND_COL].sum()
        c_r1, c_r2, c_r3, c_r4 = st.columns(4)
        with c_r1:
            st.metric("📦 Liczba produktów w recepturach", f"{len(edited_recipes_df)}")
        with c_r2:
            st.metric("📈 Roczne zapotrzebowanie (produkt)", f"{total_annual_t_recipes:,.0f} t")
        with c_r3:
            st.metric("🧪 Roczne zapotrzebowanie surowcowe (ze stratami)", f"{total_raw_demand_t:,.0f} t")
        with c_r4:
            st.metric("🛢️ Surowce z niezerowym zużyciem", f"{len(consumption_rows)}")

        st.markdown("##### 📦 Zestawienie po grupach produktowych")
        group_summary = (edited_recipes_df.groupby(RECIPE_GROUP_COL)[RECIPE_ANNUAL_COL]
                          .sum().reset_index().rename(columns={RECIPE_ANNUAL_COL: "Roczne zapotrzebowanie [t]"}))
        st.dataframe(group_summary, hide_index=True, use_container_width=True)

        st.info("💡 Przejdź do **Zakładki 6 (Surowce i Park Zbiorników)**, aby zobaczyć wymiarowanie silosów "
                "per pojedynczy surowiec oraz rekomendację zbiornik-vs-beczki na podstawie tego zużycia. "
                "Typy opakowań i ich rozbicie procentowe skonfigurujesz w **Zakładce 4 (Logistyka i Czas Rozlewu)**.")

    else:
        st.info("💡 Wgraj plik z recepturami powyżej, aby zobaczyć tu zagregowane zużycie surowców.")
