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

# --- BEZPIECZNA INICJALIZACJA STRUKTUR W SESJI ---
if "prod_dict" not in st.session_state:
    st.session_state.prod_dict = {
        k: {"roczna": 1200000, "utilization": 75.0} for k in FUCHS_PORTFOLIO.keys()
    }

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

# KLUCZOWE FIXY: Domyślne wartości zapobiegające awariom przed kliknięciem
if "heat_temps" not in st.session_state:
    st.session_state.heat_temps = {f"MT-{i}": 60.0 for i in range(101, 120)}
    for i in range(101, 120):
        st.session_state.heat_temps[f"MT-{i}A"] = 60.0
        st.session_state.heat_temps[f"MT-{i}B"] = 60.0

if "filling_temps" not in st.session_state:
    st.session_state.filling_temps = {f"MT-{i}": 30.0 for i in range(101, 120)}
    for i in range(101, 120):
        st.session_state.filling_temps[f"MT-{i}A"] = 30.0
        st.session_state.filling_temps[f"MT-{i}B"] = 30.0

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

# Rejestracja kart interfejsu
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja", 
    "📐 2. Karta Maszyn i Dobór Pomp", 
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Koszty Produkcji"
])

# ==========================================
# ZAKŁADKA 1: TABELA Z INTERAKTYWNYM SPLITEM ZBIORNIKÓW > 31m³
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych (Baza: {godziny_dziennie:.1f}h/dzień)")
    
    if wybrane_kategorie:
        calculated_matrix_rows = []
        total_annual_production = 0
        total_batches_per_month = 0
        total_calculated_volume_m3 = 0.0
        oversized_reactors = {}

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
            
            if calculated_vol_m3 > 31.0:
                oversized_reactors[kat] = calculated_vol_m3
            
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
        
        split_decisions = {}
        if oversized_reactors:
            st.markdown("<br>", unsafe_allow_html=True)
            st.warning("⚠️ **Wykryto przekroczenie dopuszczalnych gabarytów zbiornika (> 31 m³)!**")
            for kat_over, vol_over in oversized_reactors.items():
                split_decisions[kat_over] = st.checkbox(
                    f"Czy stworzyć dodatkową pozycję zbiornika (rozbić na 2 bliźniacze reaktory o pojemności {vol_over/2:.1f} m³) dla linii {kat_over}?",
                    value=True, key=f"chk_split_{kat_over}"
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
            tag_counter = 101
            
            for idx, r in df_complete_matrix.iterrows():
                kat = r["1. Nazwa rodziny 🔒"]
                vol_base = r["h_vol"]
                
                if split_decisions.get(kat, False):
                    confirmed_list_temp.append({
                        "tag": f"MT-{tag_counter}A", "product_family": kat, "capacity_m3": max(vol_base / 2, 0.5),
                        "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": math.ceil(r["h_batches"] / 2),
                        "mass_per_batch": math.ceil(r["h_kg"] / 2), "annual_volume": r["h_annual"] / 2
                    })
                    confirmed_list_temp.append({
                        "tag": f"MT-{tag_counter}B", "product_family": kat, "capacity_m3": max(vol_base / 2, 0.5),
                        "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": math.ceil(r["h_batches"] / 2),
                        "mass_per_batch": math.ceil(r["h_kg"] / 2), "annual_volume": r["h_annual"] / 2
                    })
                else:
                    confirmed_list_temp.append({
                        "tag": f"MT-{tag_counter}", "product_family": kat, "capacity_m3": max(vol_base, 0.5),
                        "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": r["h_batches"],
                        "mass_per_batch": r["h_kg"], "annual_volume": r["h_annual"]
                    })
                tag_counter += 1
                
            st.session_state.confirmed_mixers = confirmed_list_temp
            st.success("✅ Dane przetworzone! Przejdź do kolejnej zakładki.")
    else:
        st.info("Zaznacz aktywne rodziny produktów w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA MASZYN, REOLOGIA I DOBÓR POMP (KOLOROWANIE LMTD)
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
            
            cfg = AGITATOR_TYPES[agitator_choice]
            eta_dyn = (visc_max / 1_000_000.0) * rho  
            Re = (n_speed * (d_agitor ** 2) * rho) / max(eta_dyn, 0.001)
            Ne = cfg["laminar_C"] / Re if Re < 50 else cfg["turbulent_Ne"]
            P_max_w = Ne * (n_speed ** 3) * (d_agitor ** 5) * rho
            required_motor_power_kw = (P_max_w / 0.85 * 1.20) / 1000.0
            
            # --- PROJEKTOWANIE UKŁADU ROZŁADUNKOWEGO ---
            st.markdown("##### 📐 Projektowanie Układu Rozładunkowego i Strat Przepływu (Równanie Darcy-Weisbacha)")
            default_discharge_flow = round((V_m3 / 0.75) * 1.25, 1)
            
            c_label1, c_label2, c_label3, c_label4 = st.columns(4)
            with c_label1: st.markdown("**Wydajność pompy Q [m³/h]**")
            with c_label2: st.markdown("**Długość rurociągu L [m]**")
            with c_label3: st.markdown("**Średnica rury D [mm]**")
            with c_label4: st.markdown("**Wysokość H_stat [m]**")
            
            c_pump1, c_pump2, c_pump3, c_pump4 = st.columns(4)
            with c_pump1: q_pump = st.number_input("Q", min_value=0.5, value=float(max(default_discharge_flow, 5.0)), key=f"q_p_{mixer['tag']}", label_visibility="collapsed")
            with c_pump2: pipe_length = st.number_input("L", min_value=1.0, value=15.0, key=f"pipe_l_{mixer['tag']}", label_visibility="collapsed")
            with c_pump3: pipe_diameter_mm = st.number_input("D", min_value=25, max_value=250, value=80, key=f"pipe_d_{mixer['tag']}", label_visibility="collapsed")
            with c_pump4: pump_static_head = st.number_input("H", min_value=0.0, value=3.0, key=f"p_stat_{mixer['tag']}", label_visibility="collapsed")

            D_m = pipe_diameter_mm / 1000.0
            pipe_area = (math.pi * (D_m ** 2)) / 4.0
            velocity_m_s = (q_pump / 3600.0) / pipe_area
            eta_dyn_max = (visc_max / 1_000_000.0) * rho
            Re_pipe = (velocity_m_s * D_m * rho) / max(eta_dyn_max, 0.001)
            
            if Re_pipe < 2100:
                lambda_friction = 64.0 / max(Re_pipe, 1.0)
            else:
                lambda_friction = 0.3164 / (Re_pipe ** 0.25)
                
            g_gravity = 9.81
            head_loss_m = lambda_friction * (pipe_length / D_m) * ((velocity_m_s ** 2) / (2.0 * g_gravity))
            total_required_head_m = pump_static_head + head_loss_m
            required_pressure_bar = (rho * g_gravity * total_required_head_m) / 100000.0
            
            pump_type = "Śrubowa (Wyporowa)" if visc_max > 150 else ("Krzywkowa (Rotacyjna)" if visc_max > 50 else "Odśrodkowa")
            eta_pump = 0.60
            pump_power_kw = (q_pump * required_pressure_bar) / (36.0 * eta_pump) * 1.15
            
            st.success(f"⚡ **Mieszadło:** Silnik: **{required_motor_power_kw:.2f} kW** | **Pompa Rozładunkowa ({pump_type}):** Przepływ {q_pump:.1f} m³/h @ {required_pressure_bar:.2f} bar")
            
            # --- BILANSE CIEPLNE I OBLICZANIE LMTD ---
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

            engineering_table_data.append({
                "Mieszalnik": mixer["tag"], "Materiał korpusu": prod_info["material"], "Pojemność [m³]": round(V_m3, 2), 
                "Masa szarży [kg]": int(mixer["mass_per_batch"]), "Typ Mieszadła": agitator_choice,
                "Moc Mieszadła [kW]": round(required_motor_power_kw, 2), "Typ Pompy": pump_type, "Przepływ [m³/h]": round(q_pump, 1),
                "Moc Pompy [kW]": round(pump_power_kw, 2), "Moc Grzania [kW]": round(req_p_heat_kw, 1), 
                "LMTD Grzania [°C]": round(calculated_lmtd_h, 1),
                "Moc Chłodzenia [kW]": round(req_p_cool_kw, 1),
                "LMTD Chłodzenia [°C]": round(calculated_lmtd_c, 1)
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcza Karta Techniczna Linii Mieszania, Rozładunku i Termodynamiki")
        df_eng = pd.DataFrame(engineering_table_data)

        # --- FUNKCJA MAPOWANIA STYLÓW DLA ZAKRESÓW LMTD ---
        def style_lmtd(val):
            if isinstance(val, (int, float)):
                if val < 20.0:
                    return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'  # Krytycznie mała siła napędowa
                elif val <= 50.0:
                    return 'background-color: #d4edda; color: #155724; font-weight: bold;'  # Zakres optymalny
                else:
                    return 'background-color: #fff3cd; color: #856404; font-weight: bold;'  # Zakres wysoki (ryzyko przegrzania)
            return ''

        # Stosujemy mapowanie kolorów wyłącznie do dwóch kolumn LMTD
        styled_df_eng = df_eng.style.map(style_lmtd, subset=["LMTD Grzania [°C]", "LMTD Chłodzenia [°C]"])

        st.dataframe(styled_df_eng, hide_index=True, use_container_width=True)
        
        # Szybka legenda dla operatora
        st.caption("ℹ️ **Legenda LMTD:** 🟢 20-50°C (Optymalny) | 🟡 >50°C (Wysoki - ryzyko przegrzania medium) | 🔴 <20°C (Zbyt niski - proces będzie trwał bardzo długo)")

# ==========================================
# ZAKŁADKA 3: ZINTEGROWANA LOGISTYKA OPAKOWAŃ I CZAS ROZLEWU (JEDNA TABELA ZBIORCZA)
# ==========================================
with tab3:
    st.header("📦 Harmonogramowanie i Zbiorczy Bilans Rozlewu Opakowań")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych danych z Zakładki 1. Uruchom konfigurację i kliknij przycisk zatwierdzenia.")
    else:
        st.markdown("### 🛠️ 1. Parametry Sterowania Rozlewem")
        
        # Sekcja konfiguracji parametrów wejściowych (temperatury i edycja udziałów)
        all_logistics_rows = []
        
        # Dla przejrzystości wyświetlamy najpierw szybkie doprecyzowanie temperatur rozlewu w kolumnach
        st.markdown("**Konfiguracja temperatur rozlewu dla poszczególnych reaktorów:**")
        temp_cols = st.columns(min(len(st.session_state.confirmed_mixers), 4))
        
        for idx, mixer in enumerate(st.session_state.confirmed_mixers):
            kat = mixer["product_family"]
            t_reaktor_max = st.session_state.heat_temps.get(mixer["tag"], 60.0)
            
            with temp_cols[idx % min(len(st.session_state.confirmed_mixers), 4)]:
                t_filling = st.number_input(
                    f"Temp. rozlewu {mixer['tag']} [°C]:", 
                    min_value=10.0, max_value=120.0, 
                    value=float(min(30.0, t_reaktor_max)), 
                    key=f"t_fill_{mixer['tag']}"
                )
                st.session_state.filling_temps[mixer["tag"]] = t_filling

        st.markdown("---")
        st.markdown("### 📊 2. Zbiorcze Zestawienie Strumieni Logistycznych Zakładu")
        
        # Budujemy dane do jednej, potężnej tabeli logistycznej
        master_logistics_data = []
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            v_annual = mixer["annual_volume"]
            chosen_packs = input_packs.get(kat, [])
            
            if v_annual > 0 and chosen_packs:
                m_monthly_kg = v_annual / 12
                dens = FUCHS_PORTFOLIO[kat]["density"]
                total_volume_l = m_monthly_kg / dens
                
                # Zarządzanie stanem udziałów procentowych
                state_key = f"pct_df_{mixer['tag']}"
                if state_key not in st.session_state:
                    init_pct = [round(100.0 / len(chosen_packs), 1)] * len(chosen_packs)
                    st.session_state[state_key] = pd.DataFrame({"Typ Opakowania": chosen_packs, "Udział w rozlewie %": init_pct})
                
                # Pobieramy udziały (w tle użytkownik może je edytować, domyślnie równe)
                pct_df = st.session_state[state_key]
                
                # Dla każdego opakowania danej linii tworzymy osobny wiersz do wielkiej tabeli
                for _, p_row in pct_df.iterrows():
                    p_name = p_row["Typ Opakowania"]
                    pct = p_row["Udział w rozlewie %"] / 100.0
                    config = PACK_CONFIGS[p_name]
                    
                    allocated_liters = total_volume_l * pct
                    total_szt = math.ceil(allocated_liters / config["size_l"]) if allocated_liters > 0 else 0
                    needed_pallets = math.ceil(total_szt / config["per_pallet"]) if total_szt > 0 else 0
                    filling_hours = total_szt / config["rate_szt_h"] if total_szt > 0 else 0.0
                    
                    if allocated_liters > 0:
                        master_logistics_data.append({
                            "ID Reaktora 🔒": mixer["tag"],
                            "Linia Produktowa 🔒": kat,
                            "Typ Opakowania 🔒": p_name,
                            "Udział % 🔒": f"{p_row['Udział w rozlewie %']:.1f}%",
                            "Objętość Strumienia [l] 🔒": int(allocated_liters),
                            "Zapotrzebowanie [szt./mies] 🔒": int(total_szt),
                            "Palety [EPAL/mies] 🔒": int(needed_pallets),
                            "Czas pracy linii rozlewu [h] 🔒": round(filling_hours, 1)
                        })
        
        if master_logistics_data:
            df_master_logistics = pd.DataFrame(master_logistics_data)
            
            #Wyświetlenie JEDNEJ, zunifikowanej tabeli dla całej fabryki
            st.dataframe(
                df_master_logistics,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Objętość Strumienia [l] 🔒": st.column_config.NumberColumn(format="%d"),
                    "Zapotrzebowanie [szt./mies] 🔒": st.column_config.NumberColumn(format="%d"),
                    "Palety [EPAL/mies] 🔒": st.column_config.NumberColumn(format="%d"),
                    "Czas pracy linii rozlewu [h] 🔒": st.column_config.NumberColumn(format="%.1f h")
                }
            )
            
            # --- SEKCJA KPI POD TABELĄ ---
            st.markdown("<br>", unsafe_allow_html=True)
            total_factory_hours = df_master_logistics["Czas pracy linii rozlewu [h] 🔒"].sum()
            total_factory_pallets = df_master_logistics["Palety [EPAL/mies] 🔒"].sum()
            total_factory_szt = df_master_logistics["Zapotrzebowanie [szt./mies] 🔒"].sum()
            
            st.subheader("📦 Łączne podsumowanie potoku logistycznego fabryki:")
            sum_col1, sum_col2, sum_col3 = st.columns(3)
            with sum_col1:
                st.metric(label="🔄 Sumaryczny wolumen opakowań", value=f"{total_factory_szt:,} szt./miesiąc")
            with sum_col2:
                st.metric(label="🧱 Całkowity obrót magazynowy palet", value=f"{total_factory_pallets} EPAL/miesiąc")
            with sum_col3:
                factory_days = total_factory_hours / godziny_dziennie if godziny_dziennie > 0 else 0
                st.metric(
                    label="⏱️ Globalny czas pracy konfekcji", 
                    value=f"{total_factory_hours:.1f} h/miesiąc",
                    delta=f"Obciążenie: {factory_days:.1f} dni roboczych"
                )
            
            st.info("💡 *Wskazówka:* Procentowe podziały strumieni (split opakowań) dla każdej rodziny konfiguruje się bezpośrednio w sekcjach dynamicznych w Zakładce 1 lub w panelu bocznym. Powyższa tabela automatycznie agreguje dane i przedstawia spójny raport dla działu planowania i logistyki.")
        else:
            st.info("Brak przypisanych opakowań. Wybierz rodzaje opakowań w kroku 3 panelu bocznego.")
# ==========================================
# ZAKŁADKA 4: FINANSE - ENERGIA ELEKTRYCZNA I KOSZT WYTWORZENIA
# ==========================================
with tab4:
    st.header("💰 Optymalizacja Kosztów Energii i Bilans Finansowy")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych technicznych. Uruchom konfigurację w Zakładce 1 i zatwierdź urządzenia.")
    else:
        st.markdown("### ⚡ 1. Taryfy i Parametry Ekonomiczne")
        waluta = st.selectbox("Wybierz walutę operacyjną:", ["PLN", "EUR", "USD"])
        
        # Domyślne stawki bazowe
        default_cost = 2.119 if waluta == "PLN" else 0.535
        default_energy_rate = 750.0 if waluta == "PLN" else 160.0 # Stawka za MWh dla przemysłu
        
        c_fin1, c_fin2 = st.columns(2)
        with c_fin1:
            manuf_cost_per_kg = st.number_input(f"Bazowy Manufacturing Cost (bez energii) [za kg] w {waluta}:", min_value=0.01, value=default_cost, format="%.3f")
        with c_fin2:
            cena_mwh = st.number_input(f"Cena energii elektrycznej i cieplnej [{waluta}/MWh]:", min_value=1.0, value=default_energy_rate, format="%.2f")
        
        st.markdown("---")
        st.markdown("### 📊 2. Szczegółowy Bilans Energetyczny i Kosztowy Urządzeń")
        
        financial_summary = []
        total_monthly_saving_thermal = 0.0
        total_base_manuf_cost = 0.0
        total_mixing_energy_kwh = 0.0
        total_pumping_energy_kwh = 0.0
        
        # Przechodzimy przez zatwierdzone maszyny, aby ściągnąć parametry mechaniczne z Zakładki 2 w locie
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            # Pobieramy tonaż miesięczny i liczbę szarż
            m_monthly_kg = mixer["annual_volume"] / 12
            batches_per_month = mixer["batches_count"]
            
            # --- ODTWORZENIE DANYCH TECHNICZNYCH MOCY (Zsynchronizowane z Zakładką 2) ---
            V_m3 = mixer["capacity_m3"]
            rho = prod_info["density"] * 1000.0
            D_tank = round(2.2 * ((V_m3 / 10.0) ** (1/3)), 2)
            H_tank = round((4 * V_m3) / (math.pi * (D_tank ** 2)) * 1.2, 2)
            d_agitor = round(D_tank / 3, 2)
            
            # Wyliczenie szacunkowej mocy mieszadła (identycznie jak w Zakładce 2)
            Re_ag = (1.5 * (d_agitor ** 2) * rho) / 0.220 # przyjmowane dla max lepkości
            Ne_ag = 2.5 / Re_ag if Re_ag < 50 else 2.5 # uproszczony model Rushton/Łapowe
            P_max_w = Ne_ag * (1.5 ** 3) * (d_agitor ** 5) * rho
            motor_power_kw = max((P_max_w / 0.85 * 1.20) / 1000.0, 0.75) # Minimalnie silnik 0.75kW
            
            # Wyliczenie szacunkowej mocy pompy (identycznie jak w Zakładce 2)
            default_q_pump = float(max(round((V_m3 / 0.75) * 1.25, 1), 5.0))
            pump_power_kw = max((default_q_pump * 2.5) / (36.0 * 0.60) * 1.15, 0.37) # Szacunek oparty na średnich 2.5 bar
            
            # --- OBLICZENIA ZUŻYCIA ENERGII ELEKTRYCZNEJ ---
            # 1. Mieszanie: Moc silnika * czas cyklu (godziny) * liczba szarż w miesiącu
            hours_mixing_per_batch = prod_info["cycle_h"]
            mixing_energy_month_kwh = motor_power_kw * hours_mixing_per_batch * batches_per_month
            
            # 2. Przepompowywanie: Czas pracy pompy = Objętość szarży / Wydajność pompy
            hours_pumping_per_batch = (V_m3 / default_q_pump)
            pumping_energy_month_kwh = pump_power_kw * hours_pumping_per_batch * batches_per_month
            
            # Agregacja globalna prądu
            total_mixing_energy_kwh += mixing_energy_month_kwh
            total_pumping_energy_kwh += pumping_energy_month_kwh
            
            # Koszt prądu dla tego konkretnego węzła
            total_node_el_kwh = mixing_energy_month_kwh + pumping_energy_month_kwh
            cost_el_node = (total_node_el_kwh / 1000.0) * cena_mwh
            
            # --- ENERGIA CIEPLNA (ODZYSK) ---
            t_max_mix = st.session_state.heat_temps.get(mixer["tag"], 60.0)
            t_rozlew = st.session_state.filling_temps.get(mixer["tag"], 30.0)
            
            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg
            total_base_manuf_cost += base_manuf_cost_monthly
            
            oszczednosc_cieplna_mies = 0.0
            energia_cieplna_mwh_mies = 0.0
            if t_rozlew < t_max_mix:
                delta_t = t_max_mix - t_rozlew
                Q_recovered = m_monthly_kg * prod_info["cp"] * delta_t
                energia_cieplna_mwh_mies = Q_recovered / 3_600_000.0
                oszczednosc_cieplna_mies = energia_cieplna_mwh_mies * cena_mwh
                total_monthly_saving_thermal += oszczednosc_cieplna_mies
                
            financial_summary.append({
                "Reaktor 🔒": mixer["tag"],
                "Miesięczny tonaż [kg] 🔒": int(m_monthly_kg),
                "Moc Mieszadła [kW] 🔒": round(motor_power_kw, 1),
                "Energia Mieszania [kWh/m] 🔒": round(mixing_energy_month_kwh, 1),
                "Moc Pompy [kW] 🔒": round(pump_power_kw, 1),
                "Energia Pompowania [kWh/m] 🔒": round(pumping_energy_month_kwh, 1),
                "Koszt energii el. 🔒": f"{cost_el_node:.2f} {waluta}",
                "Odzysk Ciepła [MWh] 🔒": round(energia_cieplna_mwh_mies, 2),
                "Oszczędność termiczna 🔒": f"- {oszczednosc_cieplna_mies:.2f} {waluta}"
            })
            
        # Wyświetlenie zintegrowanej tabeli energetyczno-finansowej
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, use_container_width=True)
        
        # --- SEKCJA PODSUMOWANIA KPI DLA ENERGII ELEKTRYCZNEJ ---
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("⚡ Globalne wskaźniki zużycia energii elektrycznej i koszty:")
        
        total_factory_el_kwh = total_mixing_energy_kwh + total_pumping_energy_kwh
        total_factory_el_mwh = total_factory_el_kwh / 1000.0
        cost_total_el = total_factory_el_mwh * cena_mwh
        
        sum_el1, sum_el2, sum_el3 = st.columns(3)
        with sum_el1:
            st.metric(
                label="⚙️ Zużycie prądu: Mieszanie", 
                value=f"{total_mixing_energy_kwh:,.1f} kWh/miesiąc",
                delta=f"{total_mixing_energy_kwh/1000.0*cena_mwh:,.2f} {waluta}/mies"
            )
        with sum_el2:
            st.metric(
                label="🔄 Zużycie prądu: Przepompowanie", 
                value=f"{total_pumping_energy_kwh:,.1f} kWh/miesiąc",
                delta=f"{total_pumping_energy_kwh/1000.0*cena_mwh:,.2f} {waluta}/mies"
            )
        with sum_el3:
            st.metric(
                label="🔌 Sumaryczny koszt energii elektrycznej", 
                value=f"{cost_total_el:,.2f} {waluta}/miesiąc",
                delta=f"Łącznie: {total_factory_el_mwh:.2f} MWh"
            )
            
        st.markdown("---")
        st.subheader("💰 Końcowe zestawienie ekonomiczne fabryki (Manufacturing Cost):")
        
        # Obliczenie ostatecznego, skorygowanego kosztu wytworzenia
        # Realny Koszt = Koszt Bazowy + Koszt Prądu (Mieszanie+Pompy) - Oszczędności z Odzysku Ciepła
        final_manufacturing_cost = total_base_manuf_cost + cost_total_el - total_monthly_saving_thermal
        
        col_final1, col_final2 = st.columns(2)
        with col_final1:
            st.info(f"**Podstawowy koszt stały i zmienny operacji (wszystkie linie):** {total_base_manuf_cost:,.2f} {waluta}/miesiąc")
            st.info(f"**Koszt zasilania silników elektrycznych (mieszadła + pompy):** + {cost_total_el:,.2f} {waluta}/miesiąc")
            st.info(f"**Finansowy ekwiwalent odzyskanego ciepła procesowego:** - {total_monthly_saving_thermal:,.2f} {waluta}/miesiąc")
        with col_final2:
            st.metric(
                label="🚀 ZOPTYMALIZOWANY REALNY KOSZT WYTWORZENIA (Miesięcznie)", 
                value=f"{final_manufacturing_cost:,.2f} {waluta}",
                delta=f"Skorygowany koszt prądu i ciepła"
            )
