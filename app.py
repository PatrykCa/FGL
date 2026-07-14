import streamlit as st
import pandas as pd
import math
import io

# --- USTAWIENIA STRONY ---
st.set_page_config(page_title="System Projektowania FO", layout="wide")

# Blokada CSS na przyklejone zakładki (Sticky Tabs) dla wygody użytkowania
st.markdown("""
    <style>
    div[data-testid="stTabs"] {
        position: sticky;
        top: 0rem;
        background-color: white;
        z-index: 999;
        padding-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FO")
st.subheader("Kompletna Platforma Wymiarowania Linii, Reologii, Logistyki i Surowców")
st.markdown("---")

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
    "Woda technologiczna": {"cp": 4.19, "latent_heat": 0.0},
    "Olej termiczny": {"cp": 2.00, "latent_heat": 0.0},
    "Para nasycona": {"cp": 2.15, "latent_heat": 2256.0} # latent_heat w kJ/kg (kondensacja)
}

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
AVAILABLE_HOURS_MONTH = (250 * godziny_dziennie) / 12  

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 3: Konfiguracja i Split Opakowań")
opakowania_podzial = st.session_state.setdefault("opakowania_podzial", {})

# Przykładowe czyszczenie nieaktywnych kluczy z pamięci, by zapobiec wyciekowi (Pruning)
active_pack_keys = set()
for kat in wybrane_kategorie:
    st.sidebar.markdown(f"##### 🏭 Linia: **{kat}**")
    packs = st.sidebar.multiselect(f"Dostępne opakowania:", list(PACK_CONFIGS.keys()), default=["5l (Karton)", "200l (Beczka)", "1000l (IBC)"], key=f"packs_{kat}")
    
    if packs:
        domyslny_procent = round(100.0 / len(packs), 1)
        suma_procentow_linii = 0.0
        for p in packs:
            key_id = f"pct_{kat}_{p}"
            active_pack_keys.add(key_id)
            current_val = opakowania_podzial.get(key_id, domyslny_procent)
            val = st.sidebar.number_input(f"    ↳ Udział {p} [%]", min_value=0.0, max_value=100.0, value=float(current_val), step=5.0, key=key_id)
            opakowania_podzial[key_id] = val
            suma_procentow_linii += val
        
        if round(suma_procentow_linii, 1) == 100.0:
            st.sidebar.success(f"    ✅ Bilans {kat}: 100%")
        else:
            st.sidebar.error(f"    ❌ Suma dla {kat}: {suma_procentow_linii}%")
    st.sidebar.markdown("---")

# Usuwanie starych, nieużywanych wpisów procentowych opakowań
for k in list(opakowania_podzial.keys()):
    if k not in active_pack_keys:
        opakowania_podzial.pop(k, None)

# --- STRUKTURA INTERFEJSU ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja", 
    "📐 2. Karta Maszyn i Dynamiczna Hydraulika", 
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Koszty Produkcji",
    "🛢️ 5. Surowce i Park Zbiorników"
])

# ==========================================
# ZAKŁADKA 1: FLOTA PRODUKCYJNA Z WALIDACJĄ WIRSZY
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych")
    
    if wybrane_kategorie:
        st.markdown("##### 📥 Krok A: Parametryzacja Tonażu, Pojemności Mieszalnika oraz SKUs")
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
                f"🏭 **Wielkość floty dla {selected_family_to_edit}**: Na ile osobnych mieszalników rozbić produkcję?",
                min_value=1, max_value=int(current_skus), value=min(int(st.session_state.prod_dict[selected_family_to_edit].get("num_tanks", 1)), int(current_skus))
            )
        else:
            st.session_state.prod_dict[selected_family_to_edit]["num_tanks"] = 1

        st.markdown("### 📊 Aktualne Zestawienie Floty Produkcyjnej (Dynamiczny Edytor)")
        
        final_fleet_rows = []
        tag_counter = 101

        for kat in wybrane_kategorie:
            m_annual = st.session_state.prod_dict[kat]["roczna"]
            v_tank_user = st.session_state.prod_dict[kat]["user_vol_m3"]
            tanks_count = st.session_state.prod_dict[kat]["num_tanks"]
            
            rho_product = FUCHS_PORTFOLIO[kat]["density"]
            cyc_h = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            mass_per_batch = v_tank_user * rho_product * 1000.0
            annual_per_tank = m_annual / tanks_count if tanks_count > 0 else 0
            monthly_per_tank = annual_per_tank / 12.0
            
            batches_per_tank = math.ceil(monthly_per_tank / mass_per_batch) if mass_per_batch > 0 else 0
            real_utilization = (batches_per_tank * cyc_h) / AVAILABLE_HOURS_MONTH * 100.0 if AVAILABLE_HOURS_MONTH > 0 else 0.0
            
            for t_idx in range(tanks_count):
                tag_id = f"MT-{tag_counter}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                status_txt = "🟢 Optymalna" if real_utilization <= 85.0 else "⚠️ Przeciążenie (>85%)"
                if v_tank_user < 5.0: status_txt = "❌ Poniżej min. fabryki"

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

        df_fleet = pd.DataFrame(final_fleet_rows)
        edited_df = st.data_editor(
            df_fleet, 
            hide_index=True, 
            use_container_width=True,
            num_rows="dynamic",
            key="fleet_data_editor_v4"
        )

        if not edited_df.empty:
            total_annual_production_edited = sum(st.session_state.prod_dict[kat]["roczna"] for kat in wybrane_kategorie)
            try:
                total_batches_edited = edited_df["Szarż / miesiąc (per aparat)"].fillna(0).astype(int).sum()
                total_volume_edited = edited_df["Pojemność [m³]"].fillna(0).astype(float).sum()
            except Exception:
                total_batches_edited, total_volume_edited = 0, 0.0
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
        if st.button("📥 Zatwierdź i wyślij konfigurację do kolejnych kroków", type="primary", use_container_width=True, key="btn_zatwierdz_flote_v4"):
            if edited_df.empty:
                st.error("❌ Flota nie może być pusta!")
            else:
                # KRUCAJALNA WALIDACJA WIERZY (Zabezpieczenie przed błędem arbitralnych stringów i KeyError)
                has_error = False
                confirmed_mixers_blueprint = []
                
                for idx, row in edited_df.iterrows():
                    kat = row.get("Przypisana Linia")
                    if pd.isna(kat) or str(kat).strip() == "" or kat not in FUCHS_PORTFOLIO:
                        st.error(f"❌ Wiersz {idx+1}: Niepoprawna lub pusta 'Przypisana Linia'. Dozwolone rodzaje: {list(FUCHS_PORTFOLIO.keys())}")
                        has_error = True
                        break
                    
                    try:
                        v_m3 = float(row["Pojemność [m³]"])
                        b_count = int(row["Szarż / miesiąc (per aparat)"])
                        m_batch = int(row["Masa Szarży [kg]"])
                    except Exception:
                        st.error(f"❌ Wiersz {idx+1}: Pola numeryczne zawierają błędne dane.")
                        has_error = True
                        break

                    confirmed_mixers_blueprint.append({
                        "tag": str(row["ID Urządzenia"]),
                        "product_family": kat,
                        "capacity_m3": v_m3,
                        "material": FUCHS_PORTFOLIO[kat]["material"],
                        "batches_count": b_count,
                        "mass_per_batch": m_batch,
                        "annual_volume": m_batch * b_count * 12
                    })
                
                if not has_error:
                    # Garbage collection starych osieroconych kluczy w st.session_state (Orphaned Keys Prevention)
                    current_tags = {m["tag"] for m in confirmed_mixers_blueprint}
                    for old_key in list(st.session_state.keys()):
                        if any(old_key.endswith(f"_{t}") for t in current_tags) is False and (old_key.startswith("dn_adv_") or old_key.startswith("q_adv_")):
                            st.session_state.pop(old_key, None)
                    
                    st.session_state.confirmed_mixers = confirmed_mixers_blueprint
                    st.success(f"🎉 Zapisano stabilną strukturę floty ({len(confirmed_mixers_blueprint)} urządzeń). Przejdź do karty nr 2.")

# ==========================================
# ZAKŁADKA 2: REALNE OBLICZENIA I POPRAWIONE REYNOLDS/STEAM/STATE
# ==========================================
with tab2:
    st.header("Karta Maszyn, Zaawansowana Hydraulika i Bilans Energii")

    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych o flocie. Skonfiguruj i zatwierdź flotę w Zakładce 1.")
    else:
        summary_combined_rows = []
        
        # Inicjalizacja słowników dla bezpiecznego przechowywania stanu
        current_tags = {m["tag"] for m in st.session_state.confirmed_mixers}
        
        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            kat = mixer["product_family"]
            
            if m_id not in st.session_state.mixer_tech_advanced_details:
                st.session_state.mixer_tech_advanced_details[m_id] = {}
            
            p = st.session_state.mixer_tech_advanced_details[m_id]
            
            defaults = {
                "pump_flow_m3h": 15.0, "pipe_dn": 80, "pipe_length_m": 25.0, "delta_h_m": 5.0, "roughness_mm": 0.05,
                "viscosity_min_cst": 30.0, "viscosity_max_cst": 300.0, "density_kg_m3": FUCHS_PORTFOLIO[kat]["density"] * 1000.0,
                "count_elbows_90": 4, "count_tees": 2, "count_valves": 3, "pump_efficiency": 0.65,
                "cp_product": FUCHS_PORTFOLIO[kat]["cp"], "t_product_in": 20.0, "t_product_out": 70.0, "process_time_h": 1.5,
                "tank_mass": 1200.0, "cp_steel": 0.46, "t_discharge_c": 30.0,
                "exchange_area_m2": 4.5, "utility_flow_lmin": 80.0,
                "utility_type_heat": "Woda technologiczna", "utility_type_cool": "Woda technologiczna",
                "t_utility_heat_in": 95.0, "t_utility_cool_in": 12.0, "k_coeff": 350.0,
                "agitator_geometry": "Turbinowe (Rushton)", "rpm_val": 90
            }
            for key, val in defaults.items():
                if key not in p: p[key] = val

            # --- OBLICZENIA HYDRODYNAMIKI Z BLASIUS CORRELATION ---
            visc_min = p["viscosity_min_cst"]
            visc_max = p["viscosity_max_cst"]
            visc_avg = (visc_min + visc_max) / 2.0
            
            zeta_sum_calculated = (p["count_elbows_90"] * 0.5) + (p["count_tees"] * 1.5) + (p["count_valves"] * 0.2)
            Q_m3s = p["pump_flow_m3h"] / 3600.0
            d_m = p["pipe_dn"] / 1000.0
            area_m2 = math.pi * (d_m ** 2) / 4.0
            velocity = Q_m3s / area_m2 if area_m2 > 0 else 0.0
            
            dynamic_pressure = p["density_kg_m3"] * (velocity ** 2) / 2.0
            p_hydrostatic = p["density_kg_m3"] * 9.81 * p["delta_h_m"]

            def calculate_hydraulics_v2(v_cst):
                v_m2s = v_cst * 1e-6
                re = (velocity * d_m) / v_m2s if v_m2s > 0 else 0
                
                # POPRAWKA TARCIA: Laminarny (64/Re) vs Burzliwy (Korelacja Blasiusa dla dokładności inżynieryjnej)
                if re <= 2320:
                    lam = 64.0 / re if re > 0 else 0.03
                else:
                    lam = 0.316 * (re ** -0.25) if re < 1e5 else 0.02
                
                p_loss_lin = lam * (p["pipe_length_m"] / d_m) * dynamic_pressure if d_m > 0 else 0.0
                tot_p_pa = p_loss_lin + (zeta_sum_calculated * dynamic_pressure) + p_hydrostatic
                tot_p_bar = tot_p_pa / 100000.0
                p_power_kw = (Q_m3s * tot_p_pa) / p["pump_efficiency"] / 1000.0 if p["pump_efficiency"] > 0 else 0.0
                return tot_p_bar, p_power_kw, re

            p_bar_min, power_kw_min, re_min = calculate_hydraulics_v2(visc_min)
            p_bar_avg, power_kw_avg, re_avg = calculate_hydraulics(visc_avg) if 'calculate_hydraulics' in locals() else calculate_hydraulics_v2(visc_avg)
            p_bar_max, power_kw_max, re_max = calculate_hydraulics_v2(visc_max)

            # --- POPRAWKA DANYCH MIESZADŁA (AGITATOR_TYPES WPIĘTE DO MODELU) ---
            geom_data = AGITATOR_TYPES[p["agitator_geometry"]]
            d_impeller = (2.2 * ((mixer["capacity_m3"] / 10.0) ** (1/3))) / 3.0
            visc_avg_pas = (visc_avg / 1_000_000.0) * p["density_kg_m3"]
            
            re_mix = ((p["rpm_val"] / 60.0) * (d_impeller ** 2) * p["density_kg_m3"]) / max(visc_avg_pas, 0.0001)
            ne_power = geom_data["laminar_C"] / re_mix if re_mix < 50 else geom_data["turbulent_Ne"]
            power_shaft_w = ne_power * ((p["rpm_val"] / 60.0) ** 3) * (d_impeller ** 5) * p["density_kg_m3"]
            power_mix_kw = max((power_shaft_w / 0.85 * 1.25) / 1000.0, 1.5)

            # --- POPRAWKA TERMIKI DLA PARY (LATENT HEAT CONDENSTATION BILANS) ---
            mass_product = mixer["mass_per_batch"]
            delta_t_heating = p["t_product_out"] - p["t_product_in"]
            Q_heating_kj = (mass_product * p["cp_product"] * delta_t_heating) + (p["tank_mass"] * p["cp_steel"] * delta_t_heating)
            Q_heating_mj = Q_heating_kj / 1000.0
            power_heating_kw = Q_heating_kj / (p["process_time_h"] * 3600.0) if p["process_time_h"] > 0 else 0.0
            
            # Realny wydatek masowy nośnika
            medium_data = MEDIA_PROCESOWE[p["utility_type_heat"]]
            if medium_data["latent_heat"] > 0:
                # Jeśli to para, zużycie zależy od ciepła utajonego kondensacji! (Korekta fizyczna)
                utility_mass_flow_kgh = (Q_heating_kj / medium_data["latent_heat"]) / p["process_time_h"]
                t_utility_heat_out = p["t_utility_heat_in"] # Kondensacja izotermiczna
            else:
                # Ciecz (Sensible heat fluid math)
                mass_utility_heat_kg = p["utility_flow_lmin"] * (p["process_time_h"] * 60.0)
                if mass_utility_heat_kg > 0:
                    delta_t_utility_heat = Q_heating_kj / (mass_utility_heat_kg * medium_data["cp"])
                    t_utility_heat_out = p["t_utility_heat_in"] - delta_t_utility_heat
                else:
                    t_utility_heat_out = p["t_utility_heat_in"] - 5.0
                utility_mass_flow_kgh = p["utility_flow_lmin"] * 60.0

            # Bezpieczny math.log bez ryzyka wysypania aplikacji (try/except)
            try:
                dt1_h = p["t_utility_heat_in"] - p["t_product_out"]
                dt2_h = t_utility_heat_out - p["t_product_in"]
                if dt1_h <= 0 or dt2_h <= 0: raise ValueError()
                lmtd_h = (dt1_h - dt2_h) / math.log(dt1_h / dt2_h) if abs(dt1_h - dt2_h) > 0.1 else dt1_h
                lmtd_trigger = "optimal" if 15.0 <= lmtd_h <= 60.0 else "warning"
            except Exception:
                lmtd_h = 0.0
                lmtd_trigger = "error"

            # Odzysk ciepła i czas chłodzenia do rozlewu
            delta_t_cooling = p["t_product_out"] - p["t_discharge_c"]
            if delta_t_cooling > 0:
                Q_cooling_kj = (mass_product * p["cp_product"] * delta_t_cooling)
                Q_cooling_mj = Q_cooling_kj / 1000.0
                approx_dt_cooling = max(((p["t_product_out"] + p["t_discharge_c"]) / 2.0) - p["t_utility_cool_in"], 1.0)
                cooling_power_kw = (p["k_coeff"] * p["exchange_area_m2"] * approx_dt_cooling) / 1000.0
                cooling_time_h = Q_cooling_kj / (cooling_power_kw * 3600.0) if cooling_power_kw > 0 else 0.0
            else:
                Q_cooling_mj, cooling_time_h = 0.0, 0.0

            # Realna wyliczona objętość rurociągu na zrzucie i czas pompowania
            v_pipe_total_m3 = area_m2 * p["pipe_length_m"]
            pumping_time_h = (mixer["capacity_m3"] / p["pump_flow_m3h"]) if p["pump_flow_m3h"] > 0 else 0.0

            # CRITICAL BUG FIX 1: Zapisujemy dane do st.session_state.calculated_times dla Tab 4!
            st.session_state.calculated_times[m_id] = {
                "power_mix_kw": float(power_mix_kw),
                "power_pump_kw": float(power_kw_max), # bierzemy max obciążenie (zimny start)
                "heating": float(p["process_time_h"]),
                "pumping": float(pumping_time_h),
                "t_max_mix": float(p["t_product_out"]),
                "t_rozlew": float(p["t_discharge_c"])
            }

            summary_combined_rows.append({
                "ID Urządzenia": m_id,
                "Linia": kat,
                "Prędkość [m/s]": round(velocity, 2),
                "Opór [bar] (Min/Śr/Max)": f"{p_bar_min:.2f}/{p_bar_avg:.2f}/{p_bar_max:.2f}",
                "Moc Pompy [kW] (Min/Śr/Max)": f"{power_kw_min:.2f}/{power_kw_avg:.2f}/{power_kw_max:.2f}",
                "Moc Mieszadła [kW]": round(power_mix_kw, 1),
                "Energia Grzania [MJ]": round(Q_heating_mj, 1),
                "LMTD Grzania [K]": round(lmtd_h, 1),
                "Energia Chłodzenia [MJ]": round(Q_cooling_mj, 1),
                "Czas chłodzenia [h]": round(cooling_time_h, 2),
                "_velocity_val": velocity,
                "_lmtd_trigger": lmtd_trigger
            })

        st.markdown("### 📋 Zbiorcza Specyfikacja Techniczna Maszyn i Pompy")
        df_summary = pd.DataFrame(summary_combined_rows)
        columns_to_show = [c for c in df_summary.columns if not c.startswith('_')]

        def style_basic_with_alerts(df_data):
            style_matrix = pd.DataFrame('', index=df_data.index, columns=df_data.columns)
            for idx, row in df_data.iterrows():
                v = df_summary.loc[idx, "_velocity_val"]
                if v < 0.5 or v > 2.5:
                    if "Prędkość [m/s]" in style_matrix.columns:
                        style_matrix.loc[idx, "Prędkość [m/s]"] = 'background-color: #FFC7CE; color: #9C0006; font-weight: bold;'
                lmtd_flag = df_summary.loc[idx, "_lmtd_trigger"]
                if lmtd_flag == "error" and "LMTD Grzania [K]" in style_matrix.columns:
                    style_matrix.loc[idx, "LMTD Grzania [K]"] = 'background-color: #FCE4D6; color: #C00000; font-weight: bold;'
            return style_matrix

        st.dataframe(df_summary[columns_to_show].style.apply(style_basic_with_alerts, axis=None), hide_index=True, use_container_width=True)
        st.markdown("---")

        st.markdown("### ⚙️ Parametryzatory Szczegółowe Maszyn i Mediów")
        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            p = st.session_state.mixer_tech_advanced_details[m_id]
            
            with st.expander(f"🛠️ Konfiguracja aparatu: {m_id}", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**🌊 Średnice i Zakres Reologiczny**")
                    p["pipe_dn"] = st.number_input(f"Średnica rury [DN] ({m_id}):", min_value=15, value=int(p["pipe_dn"]), key=f"dn_adv_{m_id}")
                    p["pump_flow_m3h"] = st.number_input(f"Przepływ pompy [m³/h] ({m_id}):", min_value=1.0, value=float(p["pump_flow_m3h"]), key=f"q_adv_{m_id}")
                    p["viscosity_min_cst"] = st.number_input(f"Lepkość MIN [cSt] ({m_id}):", min_value=0.5, value=float(p["viscosity_min_cst"]), key=f"v_min_{m_id}")
                    p["viscosity_max_cst"] = st.number_input(f"Lepkość MAX [cSt] ({m_id}):", min_value=1.0, value=float(p["viscosity_max_cst"]), key=f"v_max_{m_id}")
                with c2:
                    st.markdown("**📐 Rurociąg i Mieszadło**")
                    p["pipe_length_m"] = st.number_input(f"Długość rury L [m] ({m_id}):", min_value=0.1, value=float(p["pipe_length_m"]), key=f"l_len_{m_id}")
                    p["delta_h_m"] = st.number_input(f"Różnica wysokości h [m] ({m_id}):", min_value=0.0, value=float(p["delta_h_m"]), key=f"h_delta_{m_id}")
                    p["agitator_geometry"] = st.selectbox(f"Typ mieszadła ({m_id}):", list(AGITATOR_TYPES.keys()), index=list(AGITATOR_TYPES.keys()).index(p["agitator_geometry"]), key=f"agit_g_{m_id}")
                    p["rpm_val"] = st.number_input(f"Obroty [RPM] ({m_id}):", min_value=10, value=int(p["rpm_val"]), key=f"rpm_val_{m_id}")
                with c3:
                    st.markdown("**🔥 Bilans Termiczny i Wymiennik**")
                    p["utility_type_heat"] = st.selectbox(f"Medium grzewcze ({m_id}):", list(MEDIA_PROCESOWE.keys()), index=list(MEDIA_PROCESOWE.keys()).index(p["utility_type_heat"]), key=f"ut_h_{m_id}")
                    p["t_utility_heat_in"] = st.number_input(f"Temp. zasilania medium [°C] ({m_id}):", value=float(p["t_utility_heat_in"]), key=f"t_ut_h_{m_id}")
                    p["t_product_out"] = st.number_input(f"Temp. końcowa procesu [°C] ({m_id}):", value=float(p["t_product_out"]), key=f"tpout_adv_{m_id}")
                    p["t_discharge_c"] = st.number_input(f"Temp. rozlewu produktu [°C] ({m_id}):", value=float(p["t_discharge_c"]), key=f"tdisc_{m_id}")
                    p["exchange_area_m2"] = st.number_input(f"Powierzchnia [$m^2$] ({m_id}):", min_value=0.1, value=float(p["exchange_area_m2"]), key=f"area_{m_id}")
                    p["process_time_h"] = st.number_input(f"Czas grzania [h] ({m_id}):", min_value=0.1, value=float(p["process_time_h"]), key=f"time_adv_{m_id}")

        st.markdown("---")
        csv_buffer = io.StringIO()
        df_summary[columns_to_show].to_csv(csv_buffer, index=False, sep=";")
        st.download_button(
            label="📊 Pobierz raport z bilansami (Format CSV)",
            data=csv_buffer.getvalue(), file_name="Fuchs_Model_Procesowy.csv", mime="text/csv", use_container_width=True, key="btn_csv_t2"
        )

# ==========================================
# ZAKŁADKA 3: LOGISTYKA I CZAS ROZLEWU
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
        edited_fill_df = st.data_editor(pd.DataFrame(filling_table_rows), hide_index=True, use_container_width=True, disabled=["Typ Opakowania 🔒"], key="filling_editor_v4")

        # Aktualizacja konfiguracji na podstawie edytora danych
        if edited_fill_df is not None and not edited_fill_df.empty:
            for _, row_f in edited_fill_df.iterrows():
                p_type = row_f["Typ Opakowania 🔒"]
                if p_type in st.session_state.filling_lines_config:
                    st.session_state.filling_lines_config[p_type]["nozzles"] = row_f["Liczba głowic nalewaka [szt] 🟦"]
                    st.session_state.filling_lines_config[p_type]["speed_kg_min"] = row_f["Wydajność 1 głowicy [kg/min] 🟦"]

        czas_skladowania_dni = st.number_input("Czas składowania palety (Rotacja) [dni]:", min_value=1, value=14, key="storage_days")
        dni_robocze_miesiac = 250.0 / 12.0

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
                    
                    # CRITICAL BUG FIX 2: Wyciągamy pump_flow z prawidłowej struktury zamiast z nieistniejącego pump_flows!
                    m_parent = next((mx for mx in mixers_fleet if mx["product_family"] == kat), None)
                    if m_parent and m_parent["tag"] in st.session_state.mixer_tech_advanced_details:
                        q_pump_m3h = st.session_state.mixer_tech_advanced_details[m_parent["tag"]].get("pump_flow_m3h", 15.0)
                    else:
                        q_pump_m3h = 15.0

                    q_effective_flow_m3h = min(q_pump_m3h, sekcja_nalewania_m3_h)
                    czas_rozlewu_h = (masa_opakowania_month / (rho_linii * 1000.0)) / q_effective_flow_m3h if q_effective_flow_m3h > 0 else 0.0
                    liczba_palet_month = math.ceil(liczba_sztuk_month / PACK_CONFIGS[p]["per_pallet"]) if PACK_CONFIGS[p]["per_pallet"] > 0 else 0
                    miejsca_paletowe = math.ceil((liczba_palet_month / dni_robocze_miesiac) * czas_skladowania_dni)

                    real_split_rows.append({
                        "Linia 🔒": kat, "Opakowanie 📦": p, "Udział": f"{udzial_pct:.1f}%",
                        "Opakowań [/mies]": int(liczba_sztuk_month), "Palet [/mies] 🧱": int(liczba_palet_month),
                        "Miejsca magazynowe [szt] 📐": int(miejsca_paletowe), "Czas rozlewu strumienia [h] ⏱️": round(czas_rozlewu_h, 1)
                    })

        if real_split_rows:
            st.markdown("##### 🔀 Wyniki Symulacji Logistyczno-Magazynowej")
            st.dataframe(pd.DataFrame(real_split_rows), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 4: ANALIZA FINANSOWA (Z REALNYMI DANYMI Z TAB 2)
# ==========================================
with tab4:
    st.header("💰 Optymalizacja Kosztów Energii i Bilans Finansowy")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Najpierw zatwierdź flotę w Zakładce 1.")
    else:
        waluta = st.selectbox("Wybierz walutę operacyjną:", ["PLN", "EUR", "USD"])
        manuf_cost_per_kg = st.number_input(f"Bazowy Manufacturing Cost [za kg] w {waluta}:", min_value=0.01, value=2.12, format="%.3f")
        cena_mwh = st.number_input(f"Cena energii elektrycznej i cieplnej [{waluta}/MWh]:", min_value=1.0, value=750.0)
        
        financial_summary = []
        total_monthly_saving_thermal = 0.0
        total_base_manuf_cost = 0.0
        total_energy_cost_el = 0.0
        
        # calculated_times pobiera teraz realne dane z Tab 2, a nie fikcyjne defaults!
        calculated_times = st.session_state.get("calculated_times", {})

        for mixer in st.session_state.confirmed_mixers:
            tag = mixer["tag"]
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            m_monthly_kg = mixer["annual_volume"] / 12
            batches_per_month = mixer["batches_count"]
            
            # Pobranie wyliczonych parametrów w Tab 2
            m_data = calculated_times.get(tag, {"power_mix_kw": 5.5, "power_pump_kw": 1.5, "heating": 1.5, "pumping": 0.75, "t_max_mix": 70.0, "t_rozlew": 30.0})
            
            mixing_energy = m_data["power_mix_kw"] * m_data["heating"] * batches_per_month
            pumping_energy = m_data["power_pump_kw"] * m_data["pumping"] * batches_per_month
            cost_el = ((mixing_energy + pumping_energy) / 1000.0) * cena_mwh
            total_energy_cost_el += cost_el

            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg
            total_base_manuf_cost += base_manuf_cost_monthly
            
            oszczednosc_cieplna = 0.0
            if m_data["t_rozlew"] < m_data["t_max_mix"]:
                oszczednosc_cieplna = ((m_monthly_kg * prod_info["cp"] * (m_data["t_max_mix"] - m_data["t_rozlew"])) / 3_600_000.0) * cena_mwh
                total_monthly_saving_thermal += oszczednosc_cieplna
                
            financial_summary.append({
                "Reaktor": tag, "Miesięczny tonaż [kg]": int(m_monthly_kg),
                "Energia Mieszania [kWh]": round(mixing_energy, 1), "Energia Pompowania [kWh]": round(pumping_energy, 1),
                "Koszt prądu": f"{cost_el:.2f} {waluta}", "Odzysk ciepła": f"- {oszczednosc_cieplna:.2f} {waluta}"
            })
            
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, use_container_width=True)
        final_cost = total_base_manuf_cost + total_energy_cost_el - total_monthly_saving_thermal
        st.metric(label="🚀 ZOPTYMALIZOWANY REALNY KOSZT WYTWORZENIA (Miesięcznie)", value=f"{final_cost:,.2f} {waluta}")

        st.markdown("### ⏱️ 2. Pełna Analiza Czasu Cyklu Szarży")
        time_analysis_rows = []
        for mixer in st.session_state.confirmed_mixers:
            tag = mixer["tag"]
            kat = mixer["product_family"]
            m_data = calculated_times.get(tag, {"heating": 1.5, "pumping": 0.75})
            
            with st.expander(f"⏱️ Składniki czasu operacyjnego dla: {tag}", expanded=False):
                t_dosing = st.number_input("Dozowanie surowców [h]:", min_value=0.1, value=1.0, key=f"tdos_{tag}")
                t_homog = st.number_input("Homogenizacja właściwa [h]:", min_value=0.1, value=2.0, key=f"thom_{tag}")
                t_qc = st.number_input("Zwolnienie laboratoryjne QC [h]:", min_value=0.1, value=1.0, key=f"tqc_{tag}")

            t_total_chain = t_dosing + m_data["heating"] + t_homog + t_qc + m_data["pumping"]
            time_analysis_rows.append({
                "ID Mieszalnika": tag, "Linia": kat, "Pełny łańcuch szarży [h]": round(t_total_chain, 2),
                "Rekomendacja operacyjna": "🟢 Dwuzmianowa (Cykl <= 8h)" if t_total_chain <= 8.0 else "🔴 Jednozmianowa (Wymagany nadzór nocny)"
            })
        st.dataframe(pd.DataFrame(time_analysis_rows), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 5: PARK ZBIORNIKÓW (TANK FARM)
# ==========================================
with tab5:
    st.header("🛢️ Logistyka Surowcowa i Grupy Magazynowe (Tank Farm)")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych technicznych.")
    else:
        active_chemical_ratio = st.slider("Średni udział bazy płynnej w recepturze [%]:", 50, 95, 85, key="chem_ratio") / 100.0
        days_of_stock = st.number_input("Wymagany zapas bezpieczeństwa surowca [dni]:", min_value=5, value=14, key="stock_days")
        
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
        selected_tank_capacity_m3 = st.selectbox("Wybierz pojemność pojedynczego silosu [m³]:", [30, 50, 60, 80, 100, 150, 200], index=4, key="tank_cap")
        
        silos_rows = []
        total_tanks = 0
        for group_name, annual_tony in silos_aggregation.items():
            if annual_tony > 0:
                daily_t = annual_tony / 250.0
                required_m3 = (daily_t * days_of_stock) / (1.00 if "Woda" in group_name else 0.88)
                needed_tanks = math.ceil(required_m3 / (selected_tank_capacity_m3 * 0.85))
                total_tanks += needed_tanks
                silos_rows.append({
                    "Grupa Surowcowa": group_name, "Konsumpcja [t/rok]": round(annual_tony, 1), "Wymagany Bufor [m³]": round(required_m3, 1), "Liczba silosów": f"{needed_tanks} szt."
                })
        st.dataframe(pd.DataFrame(silos_rows), hide_index=True, use_container_width=True)
        st.metric("🧱 Całkowita wymagana liczba silosów surowcowych", f"{total_tanks} szt.")
