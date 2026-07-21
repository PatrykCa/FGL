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

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Hydraulic Oils (RENOLIN)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0},
    "Gear & Turbine Oils (RENOLIN)": {"material": "Stal zwykła", "density": 0.89, "cycle_h": 5, "cp": 1.9, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0},
    "Slideway & Machine Oils (RENAX)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0},
    "Engine Oils (TITAN)": {"material": "Stal zwykła", "density": 0.87, "cycle_h": 5, "cp": 2.1, "oil_group": "Syntetyczne (Gr. III/IV)", "water_content": 0.0},
    "Gear & Transmission Oils (TITAN)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 5, "cp": 2.0, "oil_group": "Syntetyczne (Gr. III/IV)", "water_content": 0.0},
    "Water-miscible (ECOCOOL)": {"material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.65},
    "Non-water-miscible (ECOCUT)": {"material": "Stal zwykła", "density": 0.87, "cycle_h": 4, "cp": 2.0, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0},
    "Cleaners (RENOCLEAN)": {"material": "Stal nierdzewna", "density": 1.01, "cycle_h": 4, "cp": 3.9, "oil_group": "Brak (Specjalistyczne)", "water_content": 0.85}
}

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
# laboratoryjnej - EDYTOWALNE bezpośrednio w Zakładce 6 (VSM), bo rzeczywisty czas zależy
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
                             tank_mass_kg, cp_steel, utility_type_heat, utility_flow_lmin,
                             t_utility_heat_in):
    """
    Bilans grzania — analogicznie do compute_cooling: moc grzania wynika z fizyki wymiennika
    (k*A*ΔT), a CZAS grzania jest z niej WYLICZANY (Q/moc), a nie odwrotnie. ΔT liczone jest
    w uproszczeniu jako różnica temperatury medium grzewczego i średniej temperatury produktu
    (wejście/wyjście), tak samo jak w compute_cooling.
    Dla mediów sensybilnych (woda/olej termiczny) dalej liczy klasyczny bilans cp*dT dla
    strony medium. Dla pary nasyconej liczy zapotrzebowanie przez ciepło skraplania,
    ponieważ para oddaje energię głównie w procesie kondensacji, a nie schładzania.
    Zwraca dict z energią, mocą, wyliczonym czasem grzania, temperaturą wyjścia medium i LMTD.
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

    if is_steam:
        # Para: energia pochodzi ze skraplania, temperatura pary ~stała (nasycenie).
        mass_utility_heat_kg = q_heating_kj / STEAM_LATENT_HEAT_KJKG if STEAM_LATENT_HEAT_KJKG > 0 else 0.0
        t_utility_heat_out = t_utility_heat_in  # kondensat opuszcza wymiennik ~w temp. nasycenia
    else:
        cp_heat_utility = media_cfg["cp"]
        mass_utility_heat_kg = utility_flow_lmin * (process_time_h * 60.0) if heating_status == "ok" else 0.0
        if mass_utility_heat_kg > 0 and cp_heat_utility > 0:
            delta_t_utility_heat = q_heating_kj / (mass_utility_heat_kg * cp_heat_utility)
            t_utility_heat_out = t_utility_heat_in - delta_t_utility_heat
        else:
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
        "mass_utility_heat_kg": mass_utility_heat_kg,
        "t_utility_heat_out": t_utility_heat_out,
        "lmtd_h": lmtd_h,
        "lmtd_trigger": lmtd_trigger,
        "is_steam": is_steam,
    }


def compute_cooling(mass_product_kg, cp_product, t_out, t_discharge, t_utility_cool_in,
                     k_coeff, exchange_area_m2):
    """Bilans chłodzenia produktu do temperatury rozlewu. Zwraca (MJ, moc kW, czas h, ostrzeżenie)."""
    delta_t_cooling = t_out - t_discharge
    if delta_t_cooling <= 0:
        return 0.0, 0.0, 0.0, "brak_potrzeby"

    q_cooling_kj = mass_product_kg * cp_product * delta_t_cooling
    q_cooling_mj = q_cooling_kj / 1000.0

    approx_dt_cooling = ((t_out + t_discharge) / 2.0) - t_utility_cool_in
    if approx_dt_cooling <= 0:
        # Medium chłodzące jest zbyt ciepłe względem produktu - wymiennik nie zadziała.
        return q_cooling_mj, 0.0, float("nan"), "niewystarczajace_dt"

    cooling_power_kw = (k_coeff * exchange_area_m2 * approx_dt_cooling) / 1000.0
    cooling_time_h = q_cooling_kj / (cooling_power_kw * 3600.0) if cooling_power_kw > 0 else float("nan")

    return q_cooling_mj, cooling_power_kw, cooling_time_h, "ok"


# --- 2. INICJALIZACJA STRUKTUR W SESJI ---
if "prod_dict" not in st.session_state:
    st.session_state.prod_dict = {
        k: {"roczna": 1200000, "user_vol_m3": 15.0, "skus": 1, "num_tanks": 1} for k in FUCHS_PORTFOLIO.keys()
    }

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

if "calculated_times" not in st.session_state:
    st.session_state.calculated_times = {}

if "mixer_tech_advanced_details" not in st.session_state:
    st.session_state.mixer_tech_advanced_details = {}

if "batch_time_components" not in st.session_state:
    st.session_state.batch_time_components = {}

# ==========================================
# PANEL BOCZNY (Wybór Rodzin i Opakowań)
# ==========================================
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne linie produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Hydraulic Oils (RENOLIN)", "Engine Oils (TITAN)", "Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")

st.sidebar.header("⏱️ KROK 2: Założenia Czasu Pracy")
liczba_zmian = st.sidebar.slider("Liczba zmian produkcyjnych:", min_value=1.0, max_value=3.0, value=1.0, step=0.5)
godziny_na_zmiane = st.sidebar.slider("Liczba godzin na jedną zmianę:", min_value=4.0, max_value=12.0, value=8.0, step=0.5)

godziny_dziennie = liczba_zmian * godziny_na_zmiane
AVAILABLE_HOURS_MONTH = (WORKING_DAYS_YEAR * godziny_dziennie) / MONTHS_PER_YEAR

st.sidebar.markdown("---")

st.sidebar.header("⚙️ KROK 3: Konfiguracja i Split Opakowań")
opakowania_podzial = st.session_state.setdefault("opakowania_podzial", {})

# Porządkowanie: usuń wpisy procentowe dla linii, które nie są już wybrane,
# żeby stare wartości nie "odżywały" po ponownym dodaniu linii.
for stale_key in [k for k in list(opakowania_podzial.keys())
                   if not any(k.startswith(f"pct_{kat}_") for kat in wybrane_kategorie)]:
    opakowania_podzial.pop(stale_key, None)

for kat in wybrane_kategorie:
    st.sidebar.markdown(f"##### 🏭 Linia: **{kat}**")
    packs = st.sidebar.multiselect(f"Dostępne opakowania:", list(PACK_CONFIGS.keys()), default=["5l (Karton)", "200l (Beczka)", "1000l (IBC)"], key=f"packs_{kat}")

    if packs:
        domyslny_procent = round(100.0 / len(packs), 1)
        suma_procentow_linii = 0.0
        for p in packs:
            key_id = f"pct_{kat}_{p}"
            current_val = opakowania_podzial.get(key_id, domyslny_procent)
            val = st.sidebar.number_input(f"    ↳ Udział {p} [%]", min_value=0.0, max_value=100.0, value=float(current_val), step=5.0, key=key_id)
            opakowania_podzial[key_id] = val
            suma_procentow_linii += val

        if round(suma_procentow_linii, 1) == 100.0:
            st.sidebar.success(f"    ✅ Bilans {kat}: 100%")
        else:
            st.sidebar.error(f"    ❌ Suma dla {kat}: {suma_procentow_linii}%")
    st.sidebar.markdown("---")

# --- STRUKTURA INTERFEJSU ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja",
    "📐 2. Karta Maszyn, Kocioł i Zasilanie",
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Koszty Produkcji",
    "🛢️ 5. Surowce i Park Zbiorników",
    "🧵 6. Mapa Strumienia Wartości (VSM)"
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

        c_ed1, c_ed2, c_ed3 = st.columns(3)
        with c_ed1:
            st.session_state.prod_dict[selected_family_to_edit]["roczna"] = st.number_input(
                "Roczna produkcja [kg]:", min_value=0, value=int(st.session_state.prod_dict[selected_family_to_edit]["roczna"]), step=50000
            )
        with c_ed2:
            st.session_state.prod_dict[selected_family_to_edit]["user_vol_m3"] = st.number_input(
                "Pojemność Mieszalnika [m³]:", min_value=0.5, value=float(st.session_state.prod_dict[selected_family_to_edit]["user_vol_m3"]), step=0.5
            )
        with c_ed3:
            st.session_state.prod_dict[selected_family_to_edit]["skus"] = st.number_input(
                "Liczba aktywnych SKUs:", min_value=1, value=int(st.session_state.prod_dict[selected_family_to_edit]["skus"]), step=1
            )

        current_skus = st.session_state.prod_dict[selected_family_to_edit]["skus"]
        if current_skus > 1:
            st.markdown("---")
            st.session_state.prod_dict[selected_family_to_edit]["num_tanks"] = st.number_input(
                f"🏭 **Wielkość floty dla {selected_family_to_edit}**: Na ile osobnych mieszalników chcesz rozbić produkcję tych {current_skus} SKUs?",
                min_value=1, max_value=int(current_skus), value=min(int(st.session_state.prod_dict[selected_family_to_edit].get("num_tanks", 1)), int(current_skus))
            )
        else:
            st.session_state.prod_dict[selected_family_to_edit]["num_tanks"] = 1

        final_fleet_rows = []
        tag_counter = 101

        for kat in wybrane_kategorie:
            m_annual = st.session_state.prod_dict[kat]["roczna"]
            v_tank_user = st.session_state.prod_dict[kat]["user_vol_m3"]
            tanks_count = st.session_state.prod_dict[kat].get("num_tanks", 1)

            rho_product = FUCHS_PORTFOLIO[kat]["density"]
            cyc_h = FUCHS_PORTFOLIO[kat]["cycle_h"]

            mass_per_batch = v_tank_user * rho_product * 1000.0
            annual_per_tank = m_annual / tanks_count
            monthly_per_tank = annual_per_tank / MONTHS_PER_YEAR

            batches_per_tank = math.ceil(monthly_per_tank / mass_per_batch) if mass_per_batch > 0 else 0
            real_utilization = (batches_per_tank * cyc_h) / AVAILABLE_HOURS_MONTH * 100.0 if AVAILABLE_HOURS_MONTH > 0 else 0.0

            for t_idx in range(tanks_count):
                tag_id = f"MT-{tag_counter}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                status_txt = "🟢 Optymalna" if real_utilization <= MAX_TANK_UTILIZATION_PCT else "⚠️ Przeciążenie (>85%)"
                if v_tank_user < MIN_TANK_VOLUME_M3:
                    status_txt = "❌ Poniżej min. fabryki (<5 m³)"

                final_fleet_rows.append({
                    "ID Urządzenia": tag_id,
                    "Przypisana Linia": kat,
                    "Pojemność [m³]": round(v_tank_user, 1),
                    "Masa Szarży [kg]": int(mass_per_batch),
                    "Szarż / miesiąc (per aparat)": int(batches_per_tank),
                    "Utylizacja Czasowa": f"{real_utilization:.1f}%",
                    "Status": status_txt
                })

            tag_counter += 1

        st.markdown("### 📊 Aktualne Zestawienie Floty Produkcyjnej (Możesz usuwać wiersze)")
        st.caption("💡 **Instrukcja:** Aby usunąć zbiornik, zaznacz pole wyboru po lewej stronie wiersza i naciśnij `Delete` na klawiaturze (lub użyj ikony kosza). "
                    "Kolumnę **Przypisana Linia** można edytować tylko na wartości z aktywnie wybranych linii produktowych - inne wartości zostaną odrzucone przy zatwierdzaniu.")

        df_fleet = pd.DataFrame(final_fleet_rows)

        edited_df = st.data_editor(
            df_fleet,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="fleet_data_editor_v3"
        )

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
                # KeyError przy próbie odczytu nieistniejącej linii z FUCHS_PORTFOLIO.
                invalid_rows = edited_df[~edited_df["Przypisana Linia"].isin(FUCHS_PORTFOLIO.keys())]
                numeric_cols = ["Pojemność [m³]", "Masa Szarży [kg]", "Szarż / miesiąc (per aparat)"]
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
                            "material": FUCHS_PORTFOLIO[kat]["material"],
                            "batches_count": int(row["Szarż / miesiąc (per aparat)"]),
                            "mass_per_batch": int(row["Masa Szarży [kg]"]),
                            "annual_volume": int(row["Masa Szarży [kg]"]) * int(row["Szarż / miesiąc (per aparat)"]) * MONTHS_PER_YEAR
                        })

                    st.session_state.confirmed_mixers = confirmed_mixers_blueprint
                    st.success(f"🎉 Zapisano strukturę floty ({len(confirmed_mixers_blueprint)} urządzeń).")
    else:
        st.info("💡 Wybierz co najmniej jedną linię produktową w panelu bocznym, aby rozpocząć.")

# ==========================================
# ZAKŁADKA 2: KARTA MASZYN, HYDRAULIKA, MIESZANIE I BILANS CIEPLNY
# ==========================================
with tab2:
    st.header("Karta Maszyn: Zaawansowane Projektowanie Procesowe")

    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych o flocie. Skonfiguruj i zatwierdź flotę w Zakładce 1, aby odblokować ten krok.")
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
                "density_kg_m3": FUCHS_PORTFOLIO[kat]["density"] * 1000.0,
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
                "utility_flow_lmin": 80.0,
                "utility_type_heat": "Woda technologiczna",
                "utility_type_cool": "Woda technologiczna",
                "t_utility_heat_in": 95.0,
                "t_utility_cool_in": 12.0,
                "k_coeff": 350.0,
                "agitator_type": "Turbinowe (Rushton)",
                "agitator_rpm": 90.0,
                "agitator_diameter_m": 0.6,
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
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown("**🌊 Średnice, Przepływ i Reologia**")
                    p["pipe_dn"] = st.number_input(f"Średnica rury [DN]:", min_value=15, value=int(p["pipe_dn"]), key=f"dn_adv_{m_id}")
                    p["pump_flow_m3h"] = st.number_input(f"Przepływ pompy [m³/h]:", min_value=1.0, value=float(p["pump_flow_m3h"]), key=f"q_adv_{m_id}")
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
                        st.caption("ℹ️ Para nasycona: bilans liczony przez ciepło skraplania, nie cp·ΔT.")
                    p["k_coeff_grzania"] = st.number_input(f"Współczynnik przenikania ciepła — grzanie k [W/m²K]:", min_value=1.0, value=float(p["k_coeff_grzania"]), key=f"k_grz_{m_id}")
                    p["utility_type_cool"] = st.selectbox(f"Medium chłodzące:", list(MEDIA_PROCESOWE.keys()), index=list(MEDIA_PROCESOWE.keys()).index(p["utility_type_cool"]), key=f"ut_c_type_{m_id}")
                    p["t_utility_cool_in"] = st.number_input(f"Temp. wody chłodzącej [°C]:", value=float(p["t_utility_cool_in"]), key=f"t_ut_c_{m_id}")
                    p["exchange_area_m2"] = st.number_input(f"Powierzchnia wymiany (wspólny płaszcz) [m²]:", min_value=0.1, value=float(p["exchange_area_m2"]), key=f"area_{m_id}")
                    p["utility_flow_lmin"] = st.number_input(f"Przepływ medium [l/min]:", min_value=1.0, value=float(p["utility_flow_lmin"]), key=f"ut_flow_{m_id}")
                    p["t_product_in"] = st.number_input(f"Temp. początkowa płynu [°C]:", value=float(p["t_product_in"]), key=f"tpin_adv_{m_id}")
                    p["t_product_out"] = st.number_input(f"Temp. procesu (gorący) [°C]:", value=float(p["t_product_out"]), key=f"tpout_adv_{m_id}")
                    p["t_discharge_c"] = st.number_input(f"Temp. rozlewu (docelowa) [°C]:", value=float(p["t_discharge_c"]), key=f"tdisc_{m_id}")
                    st.caption("ℹ️ Czas grzania nie jest już wpisywany ręcznie — jest wyliczany z mocy grzania "
                               "(k × A × ΔT) i wymaganej energii, tak samo jak czas chłodzenia.")

        st.markdown("---")

        # --- KROK 3: Przeliczenie hydrauliki/bilansu cieplnego — TERAZ z aktualnymi wartościami z KROKU 2. ---
        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            kat = mixer["product_family"]
            p = st.session_state.mixer_tech_advanced_details[m_id]

            try:
                # --- 1. HYDRAULIKA POMPY (Re / opór / moc), po 3 punktach lepkości ---
                visc_min = p["viscosity_min_cst"]
                visc_max = p["viscosity_max_cst"]
                visc_avg = (visc_min + visc_max) / 2.0

                zeta_sum_calculated = (p["count_elbows_90"] * 0.5) + (p["count_tees"] * 1.5) + (p["count_valves"] * 0.2)

                re_min, p_bar_min, power_kw_min, velocity = compute_hydraulics(
                    p["pump_flow_m3h"], p["pipe_dn"], p["pipe_length_m"], p["delta_h_m"],
                    visc_min, p["density_kg_m3"], zeta_sum_calculated, p["pump_efficiency"])
                re_avg, p_bar_avg, power_kw_avg, _ = compute_hydraulics(
                    p["pump_flow_m3h"], p["pipe_dn"], p["pipe_length_m"], p["delta_h_m"],
                    visc_avg, p["density_kg_m3"], zeta_sum_calculated, p["pump_efficiency"])
                re_max, p_bar_max, power_kw_max, _ = compute_hydraulics(
                    p["pump_flow_m3h"], p["pipe_dn"], p["pipe_length_m"], p["delta_h_m"],
                    visc_max, p["density_kg_m3"], zeta_sum_calculated, p["pump_efficiency"])

                # --- 2. MOC MIESZANIA (dawniej zdefiniowane, ale nigdy nie używane) ---
                re_mix, mix_regime, agitator_power_kw = compute_agitator_power(
                    p["agitator_type"], p["agitator_rpm"], p["agitator_diameter_m"],
                    p["density_kg_m3"], visc_avg)

                # --- 3. BILANS CIEPLNY: GRZANIE (woda/olej sensybilnie, para przez ciepło skraplania) ---
                mass_product = mixer["mass_per_batch"]
                thermal = compute_thermal_balance(
                    mass_product, p["cp_product"], p["t_product_in"], p["t_product_out"],
                    p["k_coeff_grzania"], p["exchange_area_m2"], p["tank_mass"], p["cp_steel"],
                    p["utility_type_heat"], p["utility_flow_lmin"], p["t_utility_heat_in"])

                # --- 4. CHŁODZENIE DO ROZLEWU ---
                q_cooling_mj, cooling_power_kw, cooling_time_h, cooling_status = compute_cooling(
                    mass_product, p["cp_product"], p["t_product_out"], p["t_discharge_c"],
                    p["t_utility_cool_in"], p["k_coeff"], p["exchange_area_m2"])

                # --- 5. Zapis wyników z powrotem do stanu sesji, aby Zakładka 4 mogła z nich realnie korzystać ---
                # Czas pompowania: objętość szarży / wydajność pompy.
                pumping_time_h = (mass_product / p["density_kg_m3"]) / p["pump_flow_m3h"] if p["pump_flow_m3h"] > 0 else 0.0

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
                    "medium_grz": p["utility_type_heat"],
                    "is_steam": thermal["is_steam"],
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
                    "Czas Grzania [h]": heating_txt,
                    "LMTD Grzania [K]": round(thermal["lmtd_h"], 1),
                    "Moc Chłodzenia [kW]": round(cooling_power_kw, 1),
                    "Czas chłodzenia [h]": cooling_txt,
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
        # DOBÓR KOTŁA GRZEWCZEGO (agregacja zapotrzebowania cieplnego floty)
        # ============================================================
        st.markdown("### 🔥 Dobór Kotła Grzewczego")
        st.caption("Sumuje moc grzania (Zakładka 2) po wszystkich mieszalnikach, z uwzględnieniem tego, że nie wszystkie "
                   "reaktory grzeją jednocześnie (współczynnik jednoczesności).")

        heat_by_medium = {}
        for m in st.session_state.confirmed_mixers:
            ct = st.session_state.calculated_times.get(m["tag"])
            if ct is None:
                continue
            medium = ct.get("medium_grz", "Woda technologiczna")
            heat_by_medium.setdefault(medium, {"power_kw": 0.0, "is_steam": ct.get("is_steam", False)})
            heat_by_medium[medium]["power_kw"] += ct.get("power_heating_kw", 0.0)

        if not heat_by_medium:
            st.info("ℹ️ Skonfiguruj bilans cieplny mieszalników powyżej, aby dobrać kocioł.")
            total_heating_power_installed = 0.0
        else:
            c_b1, c_b2 = st.columns(2)
            with c_b1:
                wspolczynnik_jednoczesnosci_cieplny = st.slider(
                    "Współczynnik jednoczesności grzania [%]:", min_value=20, max_value=100, value=70,
                    help="Odsetek zainstalowanej mocy grzania, który realnie występuje jednocześnie w szczycie "
                         "(rzadko wszystkie reaktory grzeją w tej samej minucie).") / 100.0
            with c_b2:
                margines_kotla = st.slider("Margines bezpieczeństwa kotła [%]:", min_value=0, max_value=50, value=20) / 100.0

            boiler_rows = []
            total_heating_power_installed = 0.0
            for medium, data in heat_by_medium.items():
                installed = data["power_kw"]
                total_heating_power_installed += installed
                needed = installed * wspolczynnik_jednoczesnosci_cieplny * (1 + margines_kotla)
                STANDARD_BOILER_SIZES_KW = [50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 800, 1000, 1250, 1600, 2000]
                recommended = next((s for s in STANDARD_BOILER_SIZES_KW if s >= needed), needed)
                row = {
                    "Medium": medium,
                    "Moc zainstalowana [kW]": round(installed, 1),
                    "Moc wymagana (ze wsp. jednocz.) [kW]": round(needed, 1),
                    "Zalecana moc kotła [kW]": round(recommended, 1),
                }
                if data["is_steam"]:
                    row["Wydajność pary [kg/h]"] = round(recommended * 3600 / STEAM_LATENT_HEAT_KJKG, 1)
                boiler_rows.append(row)
            st.dataframe(pd.DataFrame(boiler_rows), hide_index=True, use_container_width=True)

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

        installed_electric_load_kw = total_mix_power + total_pump_power + electric_boiler_load + cooling_electric_load
        demand_kw = installed_electric_load_kw * wspolczynnik_jednoczesnosci_el
        demand_kva = (demand_kw / cos_phi) * (1 + margines_transformatora) if cos_phi > 0 else 0.0

        STANDARD_TRANSFORMER_SIZES_KVA = [100, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500]
        recommended_transformer = next((s for s in STANDARD_TRANSFORMER_SIZES_KVA if s >= demand_kva), demand_kva)

        load_rows = [
            {"Odbiornik": "Silniki mieszadeł (suma floty)", "Moc [kW]": round(total_mix_power, 1)},
            {"Odbiornik": "Silniki pomp (suma floty)", "Moc [kW]": round(total_pump_power, 1)},
            {"Odbiornik": "Kocioł elektryczny" if typ_kotla == "Elektryczny" else "Kocioł (gazowy — brak obciążenia elektrycznego)",
             "Moc [kW]": round(electric_boiler_load, 1)},
            {"Odbiornik": "Chłodzenie (agregaty, przez COP)" if uwzglednij_chlodzenie_el else "Chłodzenie (nieuwzględnione)",
             "Moc [kW]": round(cooling_electric_load, 1)},
        ]
        st.dataframe(pd.DataFrame(load_rows), hide_index=True, use_container_width=True)

        m_e1, m_e2, m_e3, m_e4 = st.columns(4)
        with m_e1: st.metric("Moc zainstalowana", f"{installed_electric_load_kw:.1f} kW")
        with m_e2: st.metric("Moc szczytowa (ze wsp. jednocz.)", f"{demand_kw:.1f} kW")
        with m_e3: st.metric("Moc pozorna wymagana", f"{demand_kva:.1f} kVA")
        with m_e4: st.metric("🔌 Zalecany transformator", f"{recommended_transformer:.0f} kVA")

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
        st.info("💡 Najpierw zatwierdź konfigurację floty w Zakładce 1.")
    else:
        mixers_fleet = st.session_state.confirmed_mixers
        opakowania_podzial = st.session_state.get("opakowania_podzial", {})

        tonaz_miesieczny_per_rodzina = {}
        for m in mixers_fleet:
            kat = m["product_family"]
            tonaz_miesieczny_per_rodzina[kat] = tonaz_miesieczny_per_rodzina.get(kat, 0) + (m["batches_count"] * m["mass_per_batch"])

        aktywne_opakowania = set()
        for kat in wybrane_kategorie:
            for p in st.session_state.get(f"packs_{kat}", []): aktywne_opakowania.add(p)
        if not aktywne_opakowania: aktywne_opakowania = set(PACK_CONFIGS.keys())

        if "filling_lines_config" not in st.session_state: st.session_state.filling_lines_config = {}
        for p in aktywne_opakowania:
            if p not in st.session_state.filling_lines_config:
                st.session_state.filling_lines_config[p] = {"nozzles": 4, "speed_kg_min": 15.0} if "5l" in p.lower() or "1l" in p.lower() else {"nozzles": 1, "speed_kg_min": 60.0}

        filling_table_rows = []
        for p in aktywne_opakowania:
            cfg = st.session_state.filling_lines_config[p]
            filling_table_rows.append({
                "Typ Opakowania 🔒": p, "Liczba głowic nalewaka [szt] 🟦": int(cfg["nozzles"]), "Wydajność 1 głowicy [kg/min] 🟦": float(cfg["speed_kg_min"])
            })

        st.markdown("##### Konfiguracja Sekcji Głowic Rozlewniczych")
        edited_filling_df = st.data_editor(
            pd.DataFrame(filling_table_rows), hide_index=True, use_container_width=True,
            disabled=["Typ Opakowania 🔒"], key="filling_editor"
        )
        # POPRAWKA: edytowana tabela była wcześniej tylko wyświetlana i nigdy nie zapisywana
        # z powrotem do filling_lines_config, więc wpisane tu wartości nigdy nie trafiały do
        # obliczeń poniżej ("czas rozlewu" wyglądał na "zamrożony" na wartościach domyślnych).
        for _, row in edited_filling_df.iterrows():
            p_name = row["Typ Opakowania 🔒"]
            st.session_state.filling_lines_config[p_name] = {
                "nozzles": float(row["Liczba głowic nalewaka [szt] 🟦"]),
                "speed_kg_min": float(row["Wydajność 1 głowicy [kg/min] 🟦"]),
            }

        czas_skladowania_dni = st.number_input("Czas składowania palety (Rotacja) [dni]:", min_value=1, value=14)
        st.session_state["czas_skladowania_tab3"] = czas_skladowania_dni
        dni_robocze_miesiac = WORKING_DAYS_YEAR / MONTHS_PER_YEAR

        real_split_rows = []
        for kat, total_mass_month in tonaz_miesieczny_per_rodzina.items():
            rho_linii = FUCHS_PORTFOLIO[kat]["density"]
            for p in st.session_state.get(f"packs_{kat}", []):
                udzial_pct = opakowania_podzial.get(f"pct_{kat}_{p}", 0.0)
                if udzial_pct > 0:
                    masa_opakowania_month = total_mass_month * (udzial_pct / 100.0)
                    pack_capacity_kg = PACK_CONFIGS[p]["size_l"] * rho_linii
                    liczba_sztuk_month = math.ceil(masa_opakowania_month / pack_capacity_kg) if pack_capacity_kg > 0 else 0

                    cfg_fill = st.session_state.filling_lines_config.get(p, {"nozzles": 1, "speed_kg_min": 30.0})
                    sekcja_nalewania_m3_h = (cfg_fill["nozzles"] * cfg_fill["speed_kg_min"] * 60.0) / (rho_linii * 1000.0)
                    m_parent = next((mx for mx in mixers_fleet if mx["product_family"] == kat), None)

                    # POPRAWKA: rzeczywisty przepływ pompy pochodzi z Zakładki 2
                    # (dawniej odczytywany z nieistniejącego klucza "pump_flows" i zawsze
                    # spadał na wartość domyślną 15.0 m³/h niezależnie od konfiguracji).
                    q_pump_m3h = 15.0
                    if m_parent is not None:
                        tech_details = st.session_state.get("mixer_tech_advanced_details", {}).get(m_parent["tag"], {})
                        q_pump_m3h = tech_details.get("pump_flow_m3h", 15.0)

                    q_effective_flow_m3h = min(q_pump_m3h, sekcja_nalewania_m3_h)
                    czas_rozlewu_h = (masa_opakowania_month / (rho_linii * 1000.0)) / q_effective_flow_m3h if q_effective_flow_m3h > 0 else 0.0
                    liczba_palet_month = math.ceil(liczba_sztuk_month / PACK_CONFIGS[p]["per_pallet"])
                    miejsca_paletowe = math.ceil((liczba_palet_month / dni_robocze_miesiac) * czas_skladowania_dni)

                    real_split_rows.append({
                        "Linia 🔒": kat, "Opakowanie 📦": p, "Udział": f"{udzial_pct:.1f}%",
                        "Opakowań [/mies]": int(liczba_sztuk_month), "Palet [/mies] 🧱": int(liczba_palet_month),
                        "Miejsca magazynowe [szt] 📐": int(miejsca_paletowe), "Czas rozlewu strumienia [h] ⏱️": round(czas_rozlewu_h, 1),
                        "Wąskie gardło": "Pompa" if q_pump_m3h < sekcja_nalewania_m3_h else "Sekcja nalewania"
                    })

        st.session_state["logistics_results"] = real_split_rows

        if real_split_rows:
            st.markdown("##### 🔀 Wyniki Symulacji Logistyczno-Magazynowej")
            st.caption("Kolumna **Wąskie gardło** pokazuje, czy czas rozlewu jest dziś limitowany przez wydajność pompy z Zakładki 2, "
                       "czy przez sekcję głowic nalewczych skonfigurowaną powyżej.")
            st.dataframe(pd.DataFrame(real_split_rows), hide_index=True, use_container_width=True)
        else:
            st.info("Brak skonfigurowanego podziału opakowań o niezerowym udziale — uzupełnij procenty w panelu bocznym.")

# ==========================================
# ZAKŁADKA 4: ANALIZA FINANSOWA
# ==========================================
with tab4:
    st.header("💰 Optymalizacja Kosztów Energii i Bilans Finansowy")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Najpierw zatwierdź flotę w Zakładce 1.")
    else:
        waluta = st.selectbox("Wybierz walutę operacyjną:", ["PLN", "EUR", "USD"])
        manuf_cost_per_kg = st.number_input(f"Bazowy Manufacturing Cost [za kg] w {waluta}:", min_value=0.01, value=2.12, format="%.3f")
        cena_mwh = st.number_input(f"Cena energii elektrycznej (mieszanie/pompowanie) [{waluta}/MWh]:", min_value=1.0, value=750.0)
        st.session_state["cena_mwh_tab4"] = cena_mwh

        if not st.session_state.calculated_times:
            st.info("ℹ️ Skonfiguruj urządzenia w Zakładce 2, aby koszty energii odzwierciedlały rzeczywistą hydraulikę i bilans cieplny "
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
            prod_info = FUCHS_PORTFOLIO[kat]
            m_monthly_kg = mixer["annual_volume"] / MONTHS_PER_YEAR
            batches_per_month = mixer["batches_count"]

            # POPRAWKA: te dane teraz faktycznie pochodzą z Zakładki 2 (patrz zapis do
            # st.session_state.calculated_times w pętli obliczeniowej Zakładki 2).
            # Wartości domyślne poniżej są używane wyłącznie, jeśli użytkownik jeszcze
            # nie odwiedził Zakładki 2 dla danego urządzenia.
            m_data = calculated_times.get(tag, {"power_mix_kw": 5.5, "power_pump_kw": 1.5, "heating": 1.5, "pumping": 0.75, "t_max_mix": 60.0, "t_rozlew": 30.0})

            mixing_energy = m_data["power_mix_kw"] * prod_info["cycle_h"] * batches_per_month
            pumping_energy = m_data["power_pump_kw"] * m_data["pumping"] * batches_per_month
            cost_el = ((mixing_energy + pumping_energy) / 1000.0) * cena_mwh
            total_energy_cost_el += cost_el

            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg
            total_base_manuf_cost += base_manuf_cost_monthly

            oszczednosc_cieplna = 0.0
            if m_data["t_rozlew"] < m_data["t_max_mix"]:
                oszczednosc_cieplna = ((m_monthly_kg * prod_info["cp"] * (m_data["t_max_mix"] - m_data["t_rozlew"])) / 3_600_000.0) * heating_fuel_price / heating_fuel_efficiency
                total_monthly_saving_thermal += oszczednosc_cieplna

            financial_summary.append({
                "Reaktor": tag, "Miesięczny tonaż [kg]": int(m_monthly_kg),
                "Energia Mieszania [kWh]": round(mixing_energy, 1), "Energia Pompowania [kWh]": round(pumping_energy, 1),
                "Koszt prądu": f"{cost_el:.2f} {waluta}", "Odzysk ciepła": f"- {oszczednosc_cieplna:.2f} {waluta}",
                "Źródło danych": "Zakładka 2" if tag in calculated_times else "Wartości domyślne"
            })

        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, use_container_width=True)

        koszt_paliwa_grzewczego = st.session_state.get("koszt_paliwa_grzewczego_month", 0.0)
        if koszt_paliwa_grzewczego > 0:
            typ_kotla_disp = st.session_state.get("typ_kotla", "—")
            st.metric(label=f"🔥 Koszt paliwa grzewczego ({typ_kotla_disp}, z Zakładki 2)",
                      value=f"{koszt_paliwa_grzewczego:,.2f} {waluta}")
        else:
            st.info("ℹ️ Skonfiguruj kocioł i typ paliwa w Zakładce 2 (sekcja 'Dobór Kotła Grzewczego'), aby doliczyć "
                    "koszt ogrzewania do kosztu wytworzenia.")

        final_cost = total_base_manuf_cost + total_energy_cost_el + koszt_paliwa_grzewczego - total_monthly_saving_thermal
        st.metric(label="🚀 ZOPTYMALIZOWANY REALNY KOSZT WYTWORZENIA (Miesięcznie)", value=f"{final_cost:,.2f} {waluta}")

        st.info("💡 Pełna analiza czasu cyklu szarży (dozowanie, grzanie, homogenizacja, QC, pompowanie, chłodzenie, "
                "rozlew) oraz rekomendacja liczby zmian znajdują się teraz w **Zakładce 6 (Mapa Strumienia Wartości)**, "
                "razem z resztą analizy czasu procesu.")

# ==========================================
# ZAKŁADKA 5: PARK ZBIORNIKÓW (TANK FARM)
# ==========================================
with tab5:
    st.header("🛢️ Logistyka Surowcowa i Grupy Magazynowe (Tank Farm)")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych technicznych. Uruchom konfigurację w Zakładce 1.")
    else:
        active_chemical_ratio = st.slider("Średni udział fazy ciekłej (baza + woda) w recepturze [%]:", 50, 95, 85) / 100.0
        days_of_stock = st.number_input("Wymagany zapas bezpieczeństwa surowca [dni]:", min_value=5, value=14)
        st.session_state["days_of_stock_tab5"] = days_of_stock

        raw_material_summary = []
        silos_aggregation = {"Mineralne (Gr. I/II)": 0.0, "Syntetyczne (Gr. III/IV)": 0.0, "Woda Procesowa DEMI": 0.0, "Inne / Pakiety płynne": 0.0}

        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
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

        st.markdown("### 🏢 Wymiarowanie Silosów Magazynowych")
        selected_tank_capacity_m3 = st.selectbox("Wybierz pojemność pojedynczego silosu [m³]:", [30, 50, 60, 80, 100, 150, 200], index=4)

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
        st.metric("🧱 Całkowita wymagana liczba silosów surowcowych", f"{total_tanks} szt.")

# ==========================================
# ZAKŁADKA 6: MAPA STRUMIENIA WARTOŚCI (VSM)
# ==========================================
with tab6:
    st.header("🧵 Mapa Strumienia Wartości (Value Stream Mapping)")
    st.caption("Ta zakładka **nie liczy niczego od nowa** — składa w jeden łańcuch czasy już policzone w Zakładkach 2-5 "
               "(hydraulika/bilans cieplny, rozlew, bufory magazynowe), więc automatycznie aktualizuje się razem z nimi.")

    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Najpierw zatwierdź flotę w Zakładce 1.")
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
            st.info("ℹ️ Skonfiguruj hydraulikę i bilans cieplny dla tej linii w Zakładce 2, aby uzyskać rzeczywiste czasy "
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
                   "niedodający wartości bezpośrednio produktowi (kontrola jakości, magazynowanie) — często konieczny "
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
