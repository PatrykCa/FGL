import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Stabilna Platforma Projektowania Linii z Automatycznym Doborem Pomp i Reologii")
st.markdown("---")

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Hydraulic Oils (RENOLIN)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0},
    "Gear & Turbine Oils (RENOLIN)": {"material": "Stal zwykła", "density": 0.89, "cycle_h": 5, "cp": 1.9},
    "Slideway & Machine Oils (RENAX)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0},
    "Engine Oils (TITAN)": {"material": "Stal zwykła", "density": 0.87, "cycle_h": 5, "cp": 2.1},
    "Gear & Transmission Oils (TITAN)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 5, "cp": 2.0},
    "Water-miscible (ECOCOOL)": {"material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8},
    "Non-water-miscible (ECOCUT)": {"material": "Stal zwykła", "density": 0.87, "cycle_h": 4, "cp": 2.0},
    "Cleaners (RENOCLEAN)": {"material": "Stal nierdzewna", "density": 1.01, "cycle_h": 4, "cp": 3.9}
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

# --- PANEL BOCZNY ---
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
st.sidebar.header("⚙️ KROK 3: Wybór Opakowań do Splitu")
input_packs = {}
for kat in wybrane_kategorie:
    packs = st.sidebar.multiselect(
        f"Dostępne opakowania dla {kat}:", list(PACK_CONFIGS.keys()), default=["5l (Karton)", "200l (Beczka)", "1000l (IBC)"], key=f"packs_{kat}"
    )
    input_packs[kat] = packs

# --- ZABEZPIECZONA INICJALIZACJA STRUKTURY SŁOWNIKOWEJ W SESJI ---
if "prod_dict" not in st.session_state:
    st.session_state.prod_dict = {
        k: {"roczna": 1200000, "utilization": 75.0} for k in FUCHS_PORTFOLIO.keys()
    }

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []
if "heat_temps" not in st.session_state:
    st.session_state.heat_temps = {}
if "filling_temps" not in st.session_state:
    st.session_state.filling_temps = {}

# --- BEZBŁĘDNA FUNKCJA CALLBACK SYNCHRONIZUJĄCA DANE ---
def sync_production_data():
    if "main_production_editor" in st.session_state:
        edits = st.session_state.main_production_editor.get("edited_rows", {})
        active_families = [k for k in FUCHS_PORTFOLIO.keys() if k in wybrane_kategorie]
        for idx, changes in edits.items():
            if idx < len(active_families):
                family_name = active_families[idx]
                if "2. Roczna produkcja [kg] 🟦" in changes:
                    st.session_state.prod_dict[family_name]["roczna"] = changes["2. Roczna produkcja [kg] 🟦"]
                if "3. Utilization % 🟦" in changes:
                    st.session_state.prod_dict[family_name]["utilization"] = changes["3. Utilization % 🟦"]

# Definiowanie widoku wejściowego
view_rows = []
for kat in wybrane_kategorie:
    view_rows.append({
        "1. Nazwa rodziny 🔒": kat,
        "2. Roczna produkcja [kg] 🟦": st.session_state.prod_dict[kat]["roczna"],
        "3. Utilization % 🟦": st.session_state.prod_dict[kat]["utilization"]
    })
df_view_input = pd.DataFrame(view_rows)

# --- REJESTRACJA KART INTERFEJSU ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja", 
    "📐 2. Karta Maszyn i Dobór Pomp", 
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Koszty Produkcji"
])

# ==========================================
# ZAKŁADKA 1: JEDNA INTERAKTYWNA TABELA Z SYNCHRONIZACJĄ CALLBACK
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych (Baza: {godziny_dziennie:.1f}h/dzień)")
    
    if wybrane_kategorie:
        calculated_matrix_rows = []
        total_annual_production = 0
        total_batches_per_month = 0
        total_calculated_volume_m3 = 0.0

        for kat in wybrane_kategorie:
            m_annual = st.session_state.prod_dict[kat]["roczna"]
            util_val = st.session_state.prod_dict[kat]["utilization"]
            
            m_monthly = m_annual / 12
            util_fraction = util_val / 100.0
            dens = FUCHS_PORTFOLIO[kat]["density"]
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            allocated_hours = AVAILABLE_HOURS_MONTH * util_fraction
            needed_batches = math.ceil(allocated_hours / cyc) if allocated_hours > 0 else 1
            batch_size_kg = math.ceil(m_monthly / needed_batches) if needed_batches > 0 else 0
            calculated_vol_m3 = batch_size_kg / (dens * 1000.0) if batch_size_kg > 0 else 0.0
            
            total_annual_production += m_annual
            total_batches_per_month += needed_batches
            total_calculated_volume_m3 += calculated_vol_m3
            
            calculated_matrix_rows.append({
                "1. Nazwa rodziny 🔒": kat,
                "2. Roczna produkcja [kg] 🟦": int(m_annual),
                "3. Utilization % 🟦": float(util_val),
                "4. Liczba szarż / miesiąc 🔒": int(needed_batches),
                "5. Gabaryt reaktora 🔒": f"{calculated_vol_m3:.1f} m³",
                "6. Masa szarży [kg] 🔒": int(batch_size_kg),
                "h_vol": calculated_vol_m3, "h_batches": needed_batches, "h_kg": batch_size_kg, "h_annual": m_annual
            })
            
        df_complete_matrix = pd.DataFrame(calculated_matrix_rows)
        
        edited_table = st.data_editor(
            df_complete_matrix,
            hide_index=True,
            use_container_width=True,
            disabled=["1. Nazwa rodziny 🔒", "4. Liczba szarż / miesiąc 🔒", "5. Gabaryt reaktora 🔒", "6. Masa szarży [kg] 🔒"],
            column_config={
                "2. Roczna produkcja [kg] 🟦": st.column_config.NumberColumn(min_value=0, step=50000, format="%d"),
                "3. Utilization % 🟦": st.column_config.NumberColumn(min_value=1.0, max_value=300.0, step=5.0, format="%.1f%%"),
                "h_vol": None, "h_batches": None, "h_kg": None, "h_annual": None
            },
            key="main_production_editor",
            on_change=sync_production_data
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📊 Sumaryczne wskaźniki operacyjne zakładu (Łącznie):")
        
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1:
            st.metric(label="📈 Całkowity tonaż roczny", value=f"{total_annual_production:,} kg")
        with sum_col2:
            st.metric(label="🔄 Łączna liczba szarż / miesiąc", value=f"{total_batches_per_month} szarż")
        with sum_col3:
            st.metric(label="📐 Całkowita gabarytowość linii (Suma m³)", value=f"{total_calculated_volume_m3:.1f} m³")
            
        st.markdown("---")
        if st.button("📥 Zatwierdź i wyślij konfigurację do kolejnych kroków", type="primary", use_container_width=True):
            confirmed_list_temp = []
            for idx, r in df_complete_matrix.iterrows():
                kat = r["1. Nazwa rodziny 🔒"]
                confirmed_list_temp.append({
                    "tag": f"MT-{101 + idx}", "product_family": kat, "capacity_m3": max(r["h_vol"], 0.5),
                    "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": r["h_batches"],
                    "mass_per_batch": r["h_kg"], "annual_volume": r["h_annual"]
                })
            st.session_state.confirmed_mixers = confirmed_list_temp
            st.success("✅ Dane przetworzone! Zaktualizowano parametry maszyn w kolejnych zakładkach.")
    else:
        st.info("Zaznacz aktywne rodziny produktów w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA MASZYN I ZAAWANSOWANY DOBÓR POMP (DARCY-WEISBACH)
# ==========================================
with tab2:
    st.header("Wymiarowanie Układu Mieszania i Zaawansowany Dobór Hydrauliki")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych. Wróć do Zakładki 1 i kliknij przycisk zatwierdzenia.")
    else:
        engineering_table_data = []
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            st.markdown(f"### ⚙️ Specyfikacja Aparatury: **{mixer['tag']}** (Linia: *{kat}*)")
            
            V_m3 = mixer["capacity_m3"]
            rho = prod_info["density"] * 1000.0  
            D_tank = round(2.2 * ((V_m3 / 10.0) ** (1/3)), 2)
            H_tank = round((4 * V_m3) / (math.pi * (D_tank ** 2)) * 1.2, 2)
            suggested_F = math.pi * D_tank * H_tank  
            d_agitor = round(D_tank / 3, 2)
            n_speed = 1.5  
            
            # --- BLOK WEJŚCIOWY REOLOGII ---
            c_mix1, c_mix2, c_mix3 = st.columns(3)
            with c_mix1:
                agitator_choice = st.selectbox(f"Typ wirnika mieszadła dla {mixer['tag']}:", list(AGITATOR_TYPES.keys()), key=f"agit_{mixer['tag']}", index=1)
            with c_mix2:
                visc_min = st.number_input(f"Lepkość MIN (startowa) [cSt] ({mixer['tag']}):", min_value=1.0, value=22.0, key=f"v_min_{mixer['tag']}")
            with c_mix3:
                visc_max = st.number_input(f"Lepkość MAKS (końcowa) [cSt] ({mixer['tag']}):", min_value=5.0, value=220.0, key=f"v_max_{mixer['tag']}")
            
            # Kalkulacja mocy hydrodynamicznej wirnika
            cfg = AGITATOR_TYPES[agitator_choice]
            def calculate_visc_power(v_kin_cst):
                eta_dyn = (v_kin_cst / 1_000_000.0) * rho  
                Re = (n_speed * (d_agitor ** 2) * rho) / eta_dyn
                Ne = cfg["laminar_C"] / Re if Re < 50 else (cfg["turbulent_Ne"] * 1.3 if Re < 10000 else cfg["turbulent_Ne"])
                return Ne * (n_speed ** 3) * (d_agitor ** 5) * rho

            P_max_w = calculate_visc_power(visc_max)
            required_motor_power_kw = (P_max_w / 0.85 * 1.20) / 1000.0
            
           # --- ZAAWANSOWANY DOBÓR POMPY ROZŁADUNKOWEJ (STRATY WG DARCY-WEISBACHA) ---
            st.markdown("##### 📐 Projektowanie Układu Rozładunkowego i Strat Przepływu (Równanie Darcy-Weisbacha)")
            default_discharge_flow = round((V_m3 / 0.75) * 1.25, 1)
            
            # Wyrównane kolumny o ujednoliconych i czytelnych etykietach
            c_pump1, c_pump2, c_pump3, c_pump4 = st.columns(4)
            with c_pump1:
                q_pump = st.number_input(f"Wydajność pompy Q [m³/h] ({mixer['tag']}):", min_value=0.5, value=float(max(default_discharge_flow, 5.0)), key=f"q_p_{mixer['tag']}")
            with c_pump2:
                pipe_length = st.number_input(f"Długość rurociągu L [m] ({mixer['tag']}):", min_value=1.0, value=15.0, key=f"pipe_l_{mixer['tag']}")
            with c_pump3:
                pipe_diameter_mm = st.number_input(f"Średnica rury D [mm] ({mixer['tag']}):", min_value=25, max_value=250, value=80, key=f"pipe_d_{mixer['tag']}")
            with c_pump4:
                pump_static_head = st.number_input(f"Wysokość podnoszenia H_stat [m] ({mixer['tag']}):", min_value=0.0, value=3.0, key=f"p_stat_{mixer['tag']}")

            # Obliczenia hydrauliczne strat liniowych (Wzory Darcy-Weisbacha z literatury)
            D_m = pipe_diameter_mm / 1000.0
            pipe_area = (math.pi * (D_m ** 2)) / 4.0
            velocity_m_s = (q_pump / 3600.0) / pipe_area
            
            # Liczba Reynoldsa w rurze dla maksymalnej lepkości
            eta_dyn_max = (visc_max / 1_000_000.0) * rho
            Re_pipe = (velocity_m_s * D_m * rho) / eta_dyn_max
            
            if Re_pipe < 2100:
                lambda_friction = 64.0 / max(Re_pipe, 1.0)
                flow_regime = "Laminarny"
            else:
                lambda_friction = 0.3164 / (Re_pipe ** 0.25)  # Wzór Blasiusa
                flow_regime = "Burzliwy"
                
            g_gravity = 9.81
            head_loss_m = lambda_friction * (pipe_length / D_m) * ((velocity_m_s ** 2) / (2.0 * g_gravity))
            total_required_head_m = pump_static_head + head_loss_m
            
            # Konwersja wysokości podnoszenia na ciśnienie [bar]
            required_pressure_bar = (rho * g_gravity * total_required_head_m) / 100000.0
            
            pump_type = "Śrubowa (Wyporowa)" if visc_max > 150 else ("Krzywkowa (Rotacyjna)" if visc_max > 50 else "Odśrodkowa")
            eta_pump = 0.60
            pump_power_kw = (q_pump * required_pressure_bar) / (36.0 * eta_pump) * 1.15
            
            st.success(f"⚡ **Mieszadło:** Silnik: **{required_motor_power_kw:.2f} kW** | **Pompa Rozładunkowa ({pump_type}):** Przepływ {q_pump:.1f} m³/h @ {required_pressure_bar:.2f} bar → Silnik pompy: **{pump_power_kw:.2f} kW** (Opory tarcia: {head_loss_m:.2f} m, ruch {flow_regime})")
            
            # --- BILANSE CIEPLNE ---
            st.markdown("##### 🧊 Parametry Wymiany Ciepła w Zbiorniku")
            col_geom, _ = st.columns([1, 1])
            with col_geom:
                user_F_surface = st.number_input(f"Powierzchnia wymiany ciepła F [m²] ({mixer['tag']}):", min_value=0.1, value=float(round(suggested_F, 2)), key=f"uf_surf_{mixer['tag']}")
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("**🔥 Proces Grzania**")
                user_time_heat = st.number_input(f"Zadany czas grzania [min] ({mixer['tag']}):", min_value=1.0, value=45.0, key=f"ut_h_{mixer['tag']}")
                user_K_heat = st.number_input(f"Współczynnik K grzania ({mixer['tag']}):", min_value=10.0, value=500.0, key=f"uk_h_{mixer['tag']}")
                t_init_h = st.number_input(f"Temp. startowa grzania [°C] ({mixer['tag']}):", value=20, key=f"t_ih_{mixer['tag']}")
                t_final_h = st.number_input(f"Temp. docelowa [°C] ({mixer['tag']}):", value=60, key=f"t_fh_{mixer['tag']}")
                st.session_state.heat_temps[mixer["tag"]] = t_final_h
                
                Q_heat_j = mixer["mass_per_batch"] * (prod_info["cp"] * 1000.0) * (t_final_h - t_init_h)
                req_p_heat_kw = (Q_heat_j / (user_time_heat * 60.0)) / 1000.0
                calculated_lmtd_h = Q_heat_j / (user_K_heat * user_F_surface * (user_time_heat * 60.0)) if (user_K_heat * user_F_surface * user_time_heat) > 0 else 0.0
                st.write(f"Moc grzania: **{req_p_heat_kw:.1f} kW** | LMTD grzania: **{calculated_lmtd_h:.1f} °C**")
                
            with col_t2:
                st.markdown("**❄️ Proces Chłodzenia**")
                user_time_cool = st.number_input(f"Zadany czas chłodzenia [min] ({mixer['tag']}):", min_value=1.0, value=60.0, key=f"ut_c_{mixer['tag']}")
                user_K_cool = st.number_input(f"Współczynnik K chłodzenia ({mixer['tag']}):", min_value=10.0, value=500.0, key=f"uk_c_{mixer['tag']}")
                t_init_c = st.number_input(f"Temp. startowa chłodzenia [°C] ({mixer['tag']}):", value=60, key=f"t_ic_{mixer['tag']}")
                t_final_c = st.number_input(f"Temp. końcowa [°C] ({mixer['tag']}):", value=30, key=f"t_fc_{mixer['tag']}")
                
                Q_cool_j = mixer["mass_per_batch"] * (prod_info["cp"] * 1000.0) * (t_init_c - t_final_c)
                req_p_cool_kw = (Q_cool_j / (user_time_cool * 60.0)) / 1000.0
                calculated_lmtd_c = Q_cool_j / (user_K_cool * user_F_surface * (user_time_cool * 60.0)) if (user_K_cool * user_F_surface * user_time_cool) > 0 else 0.0
                st.write(f"Moc chłodzenia: **{req_p_cool_kw:.1f} kW** | LMTD chłodzenia: **{calculated_lmtd_c:.1f} °C**")

            # Gromadzenie danych do końcowej tabeli zbiorczej w zakładce 2
            engineering_table_data.append({
                "Mieszalnik": mixer["tag"], "Materiał korpusu i pompy": prod_info["material"], "Pojemność [m³]": round(V_m3, 2), 
                "Masa szarży [kg]": int(mixer["mass_per_batch"]), "Typ Mieszadła": agitator_choice,
                "Moc Mieszadła [kW]": round(required_motor_power_kw, 2), "Typ Pompy": pump_type, "Przepływ [m³/h]": round(q_pump, 1),
                "Ciśnienie pompy [bar]": round(required_pressure_bar, 2), "Moc Pompy [kW]": round(pump_power_kw, 2),
                "Moc Grzania [kW]": round(req_p_heat_kw, 1), "Moc Chłodzenia [kW]": round(req_p_cool_kw, 1),
                "Temp. Procesowa": f"{t_final_h} °C", "Temp. Końcowa": f"{t_final_c} °C"
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcza Karta Techniczna Linii Mieszania i Rozładunku")
        st.dataframe(pd.DataFrame(engineering_table_data), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 3: LOGISTYKA OPAKOWAŃ I CZAS ROZLEWU
# ==========================================
with tab3:
    st.header("Harmonogramowanie Rozlewu Opakowań")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych danych z Zakładki 1.")
    else:
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            v_annual = mixer["annual_volume"]
            chosen_packs = input_packs.get(kat, [])
            
            if v_annual > 0 and chosen_packs:
                m_monthly_kg = v_annual / 12
                dens = FUCHS_PORTFOLIO[kat]["density"]
                total_volume_l = m_monthly_kg / dens
                t_reaktor_max = st.session_state.heat_temps.get(mixer["tag"], 60.0)
                
                st.markdown(f"### 🧪 Bilans Rozlewu: **{kat}** (Miesięczny tonaż: **{int(m_monthly_kg):,} kg**)")
                
                col_t_fill, _ = st.columns([1, 2])
                with col_t_fill:
                    t_filling = st.number_input(
                        f"Temperatura na rozlewie dla {mixer['tag']} [°C]:", 
                        min_value=10.0, max_value=120.0, value=float(min(30.0, t_reaktor_max)), key=f"t_fill_{mixer['tag']}"
                    )
                    st.session_state.filling_temps[mixer["tag"]] = t_filling
                
                st.markdown("👇 *Podział procentowy strumienia rozlewu (Suma = 100%):*")
                state_key = f"pct_df_{mixer['tag']}"
                
                if state_key not in st.session_state:
                    init_pct = [round(100.0 / len(chosen_packs), 1)] * len(chosen_packs)
                    st.session_state[state_key] = pd.DataFrame({"Typ Opakowania": chosen_packs, "Udział w rozlewie %": init_pct})
                
                edited_pct_df = st.data_editor(
                    st.session_state[state_key], 
                    hide_index=True, 
                    key=f"editor_widget_{mixer['tag']}", 
                    use_container_width=True, 
                    disabled=["Typ Opakowania"],
                    column_config={"Udział w rozlewie %": st.column_config.NumberColumn("Udział w rozlewie % 🟦", min_value=0.0, max_value=100.0, step=1.0, format="%.1f%%")}
                )
                st.session_state[state_key] = edited_pct_df
                
                total_sum = edited_pct_df["Udział w rozlewie %"].sum()
                if not math.isclose(total_sum, 100.0, abs_tol=0.5):
                    st.error(f"❌ Suma udziałów wynosi obecnie {total_sum:.1f}%. Skoryguj do równego 100%.")
                
                local_results = []
                total_family_filling_hours = 0.0
                
                for _, p_row in edited_pct_df.iterrows():
                    p_name = p_row["Typ Opakowania"]
                    pct = p_row["Udział w rozlewie %"] / 100.0
                    config = PACK_CONFIGS[p_name]
                    allocated_liters = total_volume_l * pct
                    
                    total_szt = math.ceil(allocated_liters / config["size_l"]) if allocated_liters > 0 else 0
                    needed_pallets = math.ceil(total_szt / config["per_pallet"]) if total_szt > 0 else 0
                    filling_hours = total_szt / config["rate_szt_h"] if total_szt > 0 else 0.0
                    total_family_filling_hours += filling_hours
                    
                    local_results.append({
                        "Opakowanie": p_name, "Objętość [l]": f"{int(allocated_liters):,}", "Zapotrzebowanie [szt./mies]": f"{total_szt:,}",
                        "Palety [epal]": needed_pallets, "Wydajność linii [szt./h]": config["rate_szt_h"], "Czas rozlewu [h/mies]": f"{filling_hours:.1f} h"
                    })
                
                st.dataframe(pd.DataFrame(local_results), hide_index=True, use_container_width=True)
                filling_days = total_family_filling_hours / godziny_dziennie if godziny_dziennie > 0 else 0
                st.info(f"⏱️ **Zajętość linii rozlewczych: {total_family_filling_hours:.1f} h/miesiąc** (~**{filling_days:.1f} dni roboczych**).")
                st.markdown("---")

# ==========================================
# ZAKŁADKA 4: FINANSE - MANUFACTURING COST
# ==========================================
with tab4:
    st.header("💰 Finansowa Optymalizacja i Koszt Wytworzenia (Manufacturing Cost)")
    
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych maszyn. Uruchom konfigurację w Zakładce 1.")
    else:
        st.subheader("📊 1. Parametry wejściowe budżetu")
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        with c_fin1:
            waluta = st.selectbox("Wybierz walutę operacyjną:", ["EUR", "PLN", "USD"])
        with c_fin2:
            default_cost = 0.535 if waluta == "EUR" else 2.119
            manuf_cost_per_kg = st.number_input(f"Bazowy Manuf. Cost [za kg produktu w {waluta}]:", min_value=0.01, value=default_cost, format="%.3f")
        with c_fin3:
            cena_mwh = st.number_input(f"Stawka za energię technologiczną [{waluta}/MWh]:", min_value=1.0, value=450.0, step=10.0)
        
        st.markdown("---")
        st.subheader("📈 2. Analiza rentowności i Odzysku Ciepła")
        
        financial_summary = []
        total_monthly_saving = 0.0
        total_base_manuf_cost = 0.0
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            t_max_mix = st.session_state.heat_temps.get(mixer["tag"], 60.0)
            t_rozlew = st.session_state.filling_temps.get(mixer["tag"], 30.0)
            m_monthly_kg = mixer["annual_volume"] / 12
            
            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg
            total_base_manuf_cost += base_manuf_cost_monthly
            
            energia_mwh_mies = 0.0
            oszczednosc_mies = 0.0
            
            if t_rozlew < t_max_mix:
                delta_t_cooling = t_max_mix - t_rozlew
                Q_recovered_kj = m_monthly_kg * prod_info["cp"] * delta_t_cooling
                energia_mwh_mies = Q_recovered_kj / 3_600_000.0
                oszczednosc_mies = energia_mwh_mies * cena_mwh
                total_monthly_saving += oszczednosc_mies
            
            optimized_manuf_cost_monthly = base_manuf_cost_monthly - oszczednosc_mies
            
            financial_summary.append({
                "Reaktor / Linia": mixer["tag"],
                "Miesięczny tonaż [kg]": int(m_monthly_kg),
                f"Bazowy Koszt Produkcji [{waluta}]": round(base_manuf_cost_monthly, 2),
                "Odzysk energii [MWh]": round(energia_mwh_mies, 3),
                f"Wartość odzysku [{waluta}]": round(oszczednosc_mies, 2),
                f"Zoptymalizowany Koszt Produkcji [{waluta}]": round(optimized_manuf_cost_monthly, 2)
            })
            
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### 🏁 Podsumowanie Efektywności Finansowej Zakładu (Skala Miesięczna)")
        
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        with col_kpi1:
            st.metric(label=f"🔴 Całkowity bazowy koszt wytworzenia", value=f"{total_base_manuf_cost:,.2f} {waluta}")
        with col_kpi2:
            st.metric(label=f"🟢 Wygenerowane oszczędności (Rekuperacja)", value=f"{total_monthly_saving:,.2f} {waluta}")
        with col_kpi3:
            real_saving_pct = (total_monthly_saving / total_base_manuf_cost * 100) if total_base_manuf_cost > 0 else 0.0
            st.metric(
                label=f"🔵 Zoptymalizowany realny koszt wytworzenia", 
                value=f"{(total_base_manuf_cost - total_monthly_saving):,.2f} {waluta}",
                delta=f"Redukcja kosztów o {real_saving_pct:.2f}%"
            )
            
        st.info(f"💰 **Prognoza roczna:** Oszczędności z tytułu odzysku energii wyniosą **{total_monthly_saving * 12:,.2f} {waluta}/rok**, co bezpośrednio obniża globalny wskaźnik Manufacturing Cost fabryki.")
