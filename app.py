import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
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

# --- 2. INICJALIZACJA STRUKTUR W SESJI ---
if "prod_dict" not in st.session_state:
    st.session_state.prod_dict = {
        k: {"roczna": 1200000, "user_vol_m3": 15.0, "skus": 1, "num_tanks": 1} for k in FUCHS_PORTFOLIO.keys()
    }

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

if "calculated_times" not in st.session_state:
    st.session_state.calculated_times = {}

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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja", 
    "📐 2. Karta Maszyn i Dobór Pomp", 
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Koszty Produkcji",
    "🛢️ 5. Surowce i Park Zbiorników"
])

# ==========================================
# ZAKŁADKA 1: POPRAWIONA I STABILNA FLOTA
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych")
    
    if wybrane_kategorie:
        st.markdown("##### 📥 Krok A: Parametryzacja Tonażu, Pojemności Mieszalnika oraz SKUs")
        st.caption("Wybierz linię z listy, aby błyskawicznie i płynnie zmienić jej parametry. Wyniki w tabeli poniżej przeliczą się natychmiast.")
        
        # Wybór linii do edycji - eliminuje całkowicie problem skakania tabeli
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

        # Dynamiczny Krok B: Wybór liczby mieszalników na podstawie SKUs
        current_skus = st.session_state.prod_dict[selected_family_to_edit]["skus"]
        if current_skus > 1:
            st.markdown("---")
            st.session_state.prod_dict[selected_family_to_edit]["num_tanks"] = st.number_input(
                f"🏭 **Wielkość floty dla {selected_family_to_edit}**: Na ile osobnych mieszalników chcesz rozbić produkcję tych {current_skus} SKUs?",
                min_value=1, max_value=int(current_skus), value=min(int(st.session_state.prod_dict[selected_family_to_edit].get("num_tanks", 1)), int(current_skus))
            )
        else:
            st.session_state.prod_dict[selected_family_to_edit]["num_tanks"] = 1

        # Generowanie bazowej struktury floty
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
            monthly_per_tank = annual_per_tank / 12.0
            
            batches_per_tank = math.ceil(monthly_per_tank / mass_per_batch) if mass_per_batch > 0 else 0
            real_utilization = (batches_per_tank * cyc_h) / AVAILABLE_HOURS_MONTH * 100.0 if AVAILABLE_HOURS_MONTH > 0 else 0.0
            
            for t_idx in range(tanks_count):
                tag_id = f"MT-{tag_counter}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                status_txt = "🟢 Optymalna" if real_utilization <= 85.0 else "⚠️ Przeciążenie (>85%)"
                if v_tank_user < 5.0: status_txt = "❌ Poniżej min. fabryki (<5 m³)"

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
        st.caption("💡 **Instrukcja:** Aby usunąć zbiornik, zaznacz pole wyboru po lewej stronie wiersza i naciśnij `Delete` na klawiaturze (lub użyj ikony kosza).")

        df_fleet = pd.DataFrame(final_fleet_rows)

        # NAPRAWA: Zmiana width="stretch" na use_container_width=True
        # Usunięto agresywny parametr 'disabled', aby zapobiec konfliktom renderowania przy usuwaniu wierszy
        edited_df = st.data_editor(
            df_fleet, 
            hide_index=True, 
            use_container_width=True,  # <-- TO ROZWIĄZUJE PROBLEM ZNIKANIA
            num_rows="dynamic",        
            key="fleet_data_editor_v3"
        )

        # Przeliczanie metryk
        if not edited_df.empty:
            total_annual_production_edited = sum(st.session_state.prod_dict[kat]["roczna"] for kat in wybrane_kategorie)
            total_batches_edited = edited_df["Szarż / miesiąc (per aparat)"].astype(int).sum()
            total_volume_edited = edited_df["Pojemność [m³]"].astype(float).sum()
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
                        "annual_volume": int(row["Masa Szarży [kg]"]) * int(row["Szarż / miesiąc (per aparat)"]) * 12
                    })
                
                st.session_state.confirmed_mixers = confirmed_mixers_blueprint
                st.success(f"🎉 Zapisano strukturę floty ({len(confirmed_mixers_blueprint)} urządzeń).")
# ==========================================
# ZAKŁADKA 2: REOLOGIA I PARAMETRY PROCESOWE
# ==========================================
with tab2:
    st.header("Konfiguracja Reologiczna i Technologiczna Floty")

    # 1. SPRAWDZENIE CZY FLOTA ZOSTAŁA ZATWIERDZONA W ZAKŁADCE 1
    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych o flocie. Skonfiguruj i zatwierdź flotę w Zakładce 1, aby odblokować ten krok.")
    else:
        # --- NA SAMEJ GÓRZE: TABELA ZBIORCZA (PODGLĄD AKTUALNEJ FLOTY) ---
        st.markdown("### 📋 Podsumowanie Floty Produkcyjnej")
        st.caption("Poniższa tabela przedstawia aktualnie wybrane urządzenia. Skonfiguruj szczegóły dla każdego z nich poniżej.")
        
        # Konwersja danych z sesji do wyświetlenia w tabeli zbiorczej
        summary_data = []
        for mixer in st.session_state.confirmed_mixers:
            summary_data.append({
                "ID Urządzenia": mixer["tag"],
                "Linia Produktowa": mixer["product_family"],
                "Pojemność [m³]": mixer["capacity_m3"],
                "Materiał": mixer["material"],
                "Liczba szarż/miesiąc": mixer["batches_count"],
                "Masa szarży [kg]": mixer["mass_per_batch"]
            })
        st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # Inicjalizacja słownika w sesji na szczegółowe parametry reologiczne, jeśli jeszcze nie istnieje
        if "mixer_rheology_params" not in st.session_state:
            st.session_state.mixer_rheology_params = {}

        # --- PONIŻEJ: SZCZEGÓŁOWE KONFIGURATORY DLA KAŻDEGO APARATU ---
        st.markdown("### ⚙️ Szczegółowa parametryzacja urządzeń")
        st.caption("Obliczenia są wykonywane niezależnie dla każdego aparatu, co pozwala na różną konfigurację podobnych składowych.")

        # Iterujemy po każdym zatwierdzonym mikserze, tworząc dla niego osobny blok/expander
        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            m_family = mixer["product_family"]
            
            # Tworzymy sekcję (np. Expander), aby strona była czytelna
            with st.expander(f"⚙️ Urządzenie: {m_id} (Linia: {m_family}, Pojemność: {mixer['capacity_m3']} m³)", expanded=True):
                
                # Inicjalizacja domyślnych wartości dla konkretnego ID urządzenia
                if m_id not in st.session_state.mixer_rheology_params:
                    st.session_state.mixer_rheology_params[m_id] = {
                        "viscosity_type": "Średnia (np. oleje silnikowe)",
                        "has_heating": True if "Kompaundy" in m_family or "Smary" in m_family else False,
                        "agitator_type": "Kotwicowe" if "Smary" in m_family else "Turbinowe",
                        "rpm_max": 150
                    }
                
                # Formularz konfiguracji specyficzny dla tego konkretnego zbiornika
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.session_state.mixer_rheology_params[m_id]["viscosity_type"] = st.selectbox(
                        f"Lepkość produktu ({m_id}):",
                        options=["Niska (wodnista)", "Średnia (np. oleje silnikowe)", "Wysoka (pasty, smary)", "Ekstremalna"],
                        index=["Niska (wodnista)", "Średnia (np. oleje silnikowe)", "Wysoka (pasty, smary)", "Ekstremalna"].index(
                            st.session_state.mixer_rheology_params[m_id]["viscosity_type"]
                        ),
                        key=f"visc_{m_id}"
                    )
                
                with col_r2:
                    st.session_state.mixer_rheology_params[m_id]["agitator_type"] = st.selectbox(
                        f"Typ mieszadła ({m_id}):",
                        options=["Turbinowe", "Kotwicowe", "Śrubowe", "Ramowe z zebrakami"],
                        index=["Turbinowe", "Kotwicowe", "Śrubowe", "Ramowe z zebrakami"].index(
                            st.session_state.mixer_rheology_params[m_id]["agitator_type"]
                        ),
                        key=f"agitator_{m_id}"
                    )
                    
                with col_r3:
                    st.session_state.mixer_rheology_params[m_id]["rpm_max"] = st.number_input(
                        f"Max obroty [RPM] ({m_id}):",
                        min_value=10, max_value=1500,
                        value=int(st.session_state.mixer_rheology_params[m_id]["rpm_max"]),
                        step=10,
                        key=f"rpm_{m_id}"
                    )
                
                # Dodatkowy parametr np. układ grzania/chłodzenia
                st.session_state.mixer_rheology_params[m_id]["has_heating"] = st.checkbox(
                    f"Wymagany płaszcz grzewczo-chłodzący dla {m_id}",
                    value=st.session_state.mixer_rheology_params[m_id]["has_heating"],
                    key=f"heat_{m_id}"
                )
                
                # --- PRZYKŁAD SPECYFICZNYCH OBLICZEŃ DLA TEGO APARATU ---
                # Wyliczanie szacowanej mocy silnika na podstawie niezależnych danych wejściowych
                visc_factor = {"Niska (wodnista)": 1.1, "Średnia (np. oleje silnikowe)": 2.2, "Wysoka (pasty, smary)": 5.5, "Ekstremalna": 11.0}
                selected_visc = st.session_state.mixer_rheology_params[m_id]["viscosity_type"]
                
                # Indywidualne wyliczenie mocy kW dla tego konkretnego zbiornika
                calculated_power_kw = mixer["capacity_m3"] * visc_factor[selected_visc] * (st.session_state.mixer_rheology_params[m_id]["rpm_max"] / 100)
                st.session_state.mixer_rheology_params[m_id]["calculated_power_kw"] = round(calculated_power_kw, 2)
                
                # Wyświetlenie wyniku dedykowanego dla tego zbiornika
                st.info(f"⚡ **Dedykowane obliczenia techniczne dla {m_id}:** Szacowana moc napędu mieszadła: **{st.session_state.mixer_rheology_params[m_id]['calculated_power_kw']} kW**")

        st.markdown("---")
        
        # Przycisk zapisu na samym dole Zakładki 2
        if st.button("📥 Zatwierdź parametry reologiczne floty", type="primary", use_container_width=True, key="btn_zatwierdz_reologie"):
            st.success("🎉 Pomyślnie zapisano niezależne konfiguracje reologiczne i obliczenia mocy dla wszystkich maszyn. Możesz przejść do kolejnej zakładki.")
        
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
        st.data_editor(pd.DataFrame(filling_table_rows), hide_index=True, width="stretch", disabled=["Typ Opakowania 🔒"], key="filling_editor")

        czas_skladowania_dni = st.number_input("Czas składowania palety (Rotacja) [dni]:", min_value=1, value=14)
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
                    m_parent = next((mx for mx in mixers_fleet if mx["product_family"] == kat), None)
                    q_pump_m3h = st.session_state.get("pump_flows", {}).get(m_parent["tag"], 15.0) if m_parent else 15.0

                    q_effective_flow_m3h = min(q_pump_m3h, sekcja_nalewania_m3_h)
                    czas_rozlewu_h = (masa_opakowania_month / (rho_linii * 1000.0)) / q_effective_flow_m3h if q_effective_flow_m3h > 0 else 0.0
                    liczba_palet_month = math.ceil(liczba_sztuk_month / PACK_CONFIGS[p]["per_pallet"])
                    miejsca_paletowe = math.ceil((liczba_palet_month / dni_robocze_miesiac) * czas_skladowania_dni)

                    real_split_rows.append({
                        "Linia 🔒": kat, "Opakowanie 📦": p, "Udział": f"{udzial_pct:.1f}%",
                        "Opakowań [/mies]": int(liczba_sztuk_month), "Palet [/mies] 🧱": int(liczba_palet_month),
                        "Miejsca magazynowe [szt] 📐": int(miejsca_paletowe), "Czas rozlewu strumienia [h] ⏱️": round(czas_rozlewu_h, 1)
                    })

        if real_split_rows:
            st.markdown("##### 🔀 Wyniki Symulacji Logistyczno-Magazynowej")
            st.dataframe(pd.DataFrame(real_split_rows), hide_index=True, width="stretch")

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
        cena_mwh = st.number_input(f"Cena energii elektrycznej i cieplnej [{waluta}/MWh]:", min_value=1.0, value=750.0)
        
        financial_summary = []
        total_monthly_saving_thermal = 0.0
        total_base_manuf_cost = 0.0
        total_energy_cost_el = 0.0
        calculated_times = st.session_state.get("calculated_times", {})

        for mixer in st.session_state.confirmed_mixers:
            tag = mixer["tag"]
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            m_monthly_kg = mixer["annual_volume"] / 12
            batches_per_month = mixer["batches_count"]
            
            m_data = calculated_times.get(tag, {"power_mix_kw": 5.5, "power_pump_kw": 1.5, "heating": 1.5, "pumping": 0.75, "t_max_mix": 60.0, "t_rozlew": 30.0})
            
            mixing_energy = m_data["power_mix_kw"] * prod_info["cycle_h"] * batches_per_month
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
            
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, width="stretch")
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
        st.dataframe(pd.DataFrame(time_analysis_rows), hide_index=True, width="stretch")

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
                daily_t = annual_tony / 250.0
                required_m3 = (daily_t * days_of_stock) / (1.00 if "Woda" in group_name else 0.88)
                needed_tanks = math.ceil(required_m3 / (selected_tank_capacity_m3 * 0.85))
                total_tanks += needed_tanks
                silos_rows.append({
                    "Grupa Surowcowa": group_name, "Konsumpcja [t/rok]": round(annual_tony, 1), "Wymagany Bufor [m³]": round(required_m3, 1), "Liczba silosów": f"{needed_tanks} szt."
                })
        st.dataframe(pd.DataFrame(silos_rows), hide_index=True, use_container_width=True)
        st.metric("🧱 Całkowita wymagana liczba silosów surowcowych", f"{total_tanks} szt.")
