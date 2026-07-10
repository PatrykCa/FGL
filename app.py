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
# ZAKŁADKA 2: KARTA MASZYN, DOBÓR POMP I LMTD
# ==========================================
with tab2:
    st.header("Karta Maszyn, Parametryzacja Hydrauliczna i Termiczna (LMTD)")

    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych o flocie. Skonfiguruj i zatwierdź flotę w Zakładce 1, aby odblokować ten krok.")
    else:
        # Inicjalizacja słownika w sesji na zaawansowane parametry techniczne
        if "mixer_tech_params" not in st.session_state:
            st.session_state.mixer_tech_params = {}

        # --- REKONSTRUKCJA I AKTUALIZACJA DANYCH (ZASZYTE OBLICZENIA) ---
        summary_rows = []
        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            kat = mixer["product_family"]
            
            # Przywrócenie Twoich domyślnych, zaawansowanych parametrów inżynieryjnych
            if m_id not in st.session_state.mixer_tech_params:
                st.session_state.mixer_tech_params[m_id] = {
                    "viscosity_cps": 150.0,
                    "pump_flow_m3h": 15.0,
                    "pipe_dn": 80,
                    "t_product_in": 20.0,
                    "t_product_out": 70.0,
                    "t_utility_in": 90.0,
                    "t_utility_out": 80.0
                }
            
            p = st.session_state.mixer_tech_params[m_id]
            
            # --- ZASZYTE OBLICZENIA HYDRAULICZNE I REOLOGICZNE ---
            density = FUCHS_PORTFOLIO[kat]["density"]
            v_m3s = (p["pump_flow_m3h"] / 3600.0)
            area_m2 = math.pi * ((p["pipe_dn"] / 1000.0) ** 2) / 4.0
            velocity = v_m3s / area_m2 if area_m2 > 0 else 0.0
            
            # Liczba Reynoldsa (Re)
            reynolds = (density * velocity * (p["pipe_dn"] / 1000.0)) / (p["viscosity_cps"] / 1000.0) if p["viscosity_cps"] > 0 else 0
            flow_type = "Laminarny (⚠️ wysokie opory)" if reynolds < 2100 else ("Burzliwy (🟢 optymalny)" if reynolds > 4000 else "Przejściowy")
            
            # --- OBLICZENIA LMTD (Logarithmic Mean Temperature Difference) ---
            # Przeciwprąd: dt1 = T_ut_in - T_prod_out, dt2 = T_ut_out - T_prod_in
            dt1 = p["t_utility_in"] - p["t_product_out"]
            dt2 = p["t_utility_out"] - p["t_product_in"]
            
            if dt1 <= 0 or dt2 <= 0:
                lmtd = 0.0
                lmtd_status = "❌ Błędny profil temperatur"
            elif abs(dt1 - dt2) < 0.1:
                lmtd = dt1
                lmtd_status = "🟢 Poprawny ($dT_1 \approx dT_2$)"
            else:
                lmtd = (dt1 - dt2) / math.log(dt1 / dt2)
                lmtd_status = "🟢 Wyznaczony poprawnie"

            # Zapis wyliczonych parametrów do słownika, aby były dostępne globalnie
            st.session_state.mixer_tech_params[m_id]["calculated_velocity"] = velocity
            st.session_state.mixer_tech_params[m_id]["calculated_reynolds"] = reynolds
            st.session_state.mixer_tech_params[m_id]["calculated_lmtd"] = lmtd
            st.session_state.mixer_tech_params[m_id]["flow_type"] = flow_type

            summary_rows.append({
                "ID Urządzenia": m_id,
                "Linia": kat,
                "Pojemność [m³]": mixer["capacity_m3"],
                "Przepływ pompy [m³/h]": p["pump_flow_m3h"],
                "Prędkość cieczy [m/s]": round(velocity, 2),
                "Liczba Reynoldsa (Re)": int(reynolds),
                "Reżim przepływu": flow_type,
                "Wyznaczone LMTD [K]": round(lmtd, 1)
            })

        # --- 1. NA SAMEJ GÓRZE: TABELA ZBIORCZA Z PODSUMOWANIEM ---
        st.markdown("### 📋 Zbiorcza Karta Techniczna i Hydrauliczna Floty")
        st.caption("Zbiorcze podsumowanie wszystkich kluczowych wyliczeń inżynieryjnych dla całej fabryki:")
        st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)
        
        st.markdown("---")

        # --- 2. PONIŻEJ: SZCZEGÓŁOWE KONFIGURATORY WEJŚCIOWE ---
        st.markdown("### ⚙️ Indywidualne Konfiguratory Szczegółowe")
        st.caption("Zmień parametry poniżej, aby zaktualizować obliczenia w tabeli zbiorczej na górze strony.")

        for mixer in st.session_state.confirmed_mixers:
            m_id = mixer["tag"]
            kat = mixer["product_family"]
            p = st.session_state.mixer_tech_params[m_id]
            
            with st.expander(f"🛠️ Specyfikacja aparatu: {m_id} (Linia: {kat})", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**🌊 Parametry Hydrauliczne**")
                    p["viscosity_cps"] = st.number_input(f"Lepkość dynamiczna [cP] ({m_id}):", min_value=1.0, value=float(p["viscosity_cps"]), step=10.0, key=f"visc_t2_{m_id}")
                    p["pump_flow_m3h"] = st.number_input(f"Wydajność pompy [m³/h] ({m_id}):", min_value=1.0, value=float(p["pump_flow_m3h"]), step=5.0, key=f"pump_t2_{m_id}")
                    p["pipe_dn"] = st.number_input(f"Średnica rurociągu [DN] ({m_id}):", min_value=15, value=int(p["pipe_dn"]), step=5, key=f"dn_t2_{m_id}")

                with col2:
                    st.markdown("**🔥 Profil Termiczny Produktu**")
                    p["t_product_in"] = st.number_input(f"Temp. początkowa produktu $t_{{in}}$ [°C]:", value=float(p["t_product_in"]), step=5.0, key=f"tpin_{m_id}")
                    p["t_product_out"] = st.number_input(f"Temp. docelowa produktu $t_{{out}}$ [°C]:", value=float(p["t_product_out"]), step=5.0, key=f"tpout_{m_id}")

                with col3:
                    st.markdown("**⚡ Profil Medium Grzewczego**")
                    p["t_utility_in"] = st.number_input(f"Temp. wejścia medium $T_{{in}}$ [°C]:", value=float(p["t_utility_in"]), step=5.0, key=f"tuin_{m_id}")
                    p["t_utility_out"] = st.number_input(f"Temp. wyjścia medium $T_{{out}}$ [°C]:", value=float(p["t_utility_out"]), step=5.0, key=f"tuout_{m_id}")
                
                # Dynamiczna prezentacja wyników LMTD pod każdym urządzeniem
                if p["calculated_lmtd"] > 0:
                    st.info(f"📐 **Obliczenia wymiany ciepła ({m_id}):** Średnia logarytmiczna różnica temperatur **LMTD = {p['calculated_lmtd']:.2f} K**")
                else:
                    st.error(f"⚠️ **Błąd profilu termicznego ({m_id}):** Temperatura medium grzewczego musi być wyższa niż temperatura produktu!")

        st.markdown("---")
        
        # --- 3. GENEROWANIE I POBIERANIE PLIKU EXCEL ---
        st.markdown("### 📥 Eksport Kompletnego Modelu Matematycznego")
        st.caption("Pobierz arkusz Excel zawierający pełne, surowe zestawienie wszystkich zbiorników oraz zaszyte formuły i wyniki obliczeń.")
        
        # Tworzenie pliku Excel w pamięci podręcznej (BytesIO)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_to_export = pd.DataFrame(summary_rows)
            df_to_export.to_excel(writer, sheet_name='Karta Floty i Pomp', index=False)
            
            # Stylizacja arkusza Excel
            workbook  = writer.book
            worksheet = writer.sheets['Karta Floty i Pomp']
            header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1})
            
            for col_num, value in enumerate(df_to_export.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25)
                
        excel_data = output.getvalue()
        
        st.download_button(
            label="📊 Pobierz raport inżynieryjny (Excel .xlsx)",
            data=excel_data,
            file_name="Fuchs_Model_Floty_i_LMTD.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
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
