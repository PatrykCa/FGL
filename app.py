import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Kompletna Platforma Wymiarowania Linii, Reologii, Logistyki i Surowców")
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

# ==========================================
# ZINTEGROWANY PANEL BOCZNY (WYBÓR OPAKOWAŃ I PROCENTÓW RAZEM)
# ==========================================

# KROK 1: Wybór Rodzin Produktowych
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne linie produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Hydraulic Oils (RENOLIN)", "Engine Oils (TITAN)", "Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")

# KROK 2: Założenia Czasu Pracy
st.sidebar.header("⏱️ KROK 2: Założenia Czasu Pracy")
liczba_zmian = st.sidebar.slider("Liczba zmian produkcyjnych:", min_value=1.0, max_value=3.0, value=1.0, step=0.5)
godziny_na_zmiane = st.sidebar.slider("Liczba godzin na jedną zmianę:", min_value=4.0, max_value=12.0, value=8.0, step=0.5)

godziny_dziennie = liczba_zmian * godziny_na_zmiane
AVAILABLE_HOURS_MONTH = (250 * godziny_dziennie) / 12  

st.sidebar.markdown("---")

# KROK 3: Zintegrowany Wybór Opakowań i Procentów (Linia po Linii)
st.sidebar.header("⚙️ KROK 3: Konfiguracja i Split Opakowań")

input_packs = {}
# Słownik przechowujący udziały procentowe przypisane do konkretnej rodziny i opakowania
if "opakowania_podzial" not in st.session_state:
    st.session_state.opakowania_podzial = {}

for kat in wybrane_kategorie:
    st.sidebar.markdown(f"##### 🏭 Linia: **{kat}**")
    
    # Wybór opakowań dla danej rodziny
    packs = st.sidebar.multiselect(
        f"Dostępne opakowania:", 
        list(PACK_CONFIGS.keys()), 
        default=["5l (Karton)", "200l (Beczka)", "1000l (IBC)"], 
        key=f"packs_{kat}"
    )
    input_packs[kat] = packs
    
    # Jeśli użytkownik wybrał jakiekolwiek opakowanie, od razu pod spodem wyświetlamy pola %
    if packs:
        domyslny_procent = round(100.0 / len(packs), 1)
        suma_procentow_linii = 0.0
        
        for p in packs:
            # Unikalny klucz dla kombinacji: Rodzina + Opakowanie
            key_id = f"pct_{kat}_{p}"
            current_val = st.session_state.opakowania_podzial.get(key_id, domyslny_procent)
            
            val = st.sidebar.number_input(
                f"   ↳ Udział {p} [%]",
                min_value=0.0,
                max_value=100.0,
                value=float(current_val),
                step=5.0,
                key=key_id
            )
            st.session_state.opakowania_podzial[key_id] = val
            suma_procentow_linii += val
        
        # Walidacja sumy 100% niezależnie dla KAŻDEJ linii produktowej
        if round(suma_procentow_linii, 1) == 100.0:
            st.sidebar.success(f"   ✅ Bilans {kat}: 100%")
        else:
            st.sidebar.error(f"   ❌ Suma dla {kat}: {suma_procentow_linii}% (Musi być 100%!)")
    else:
        st.sidebar.info("   ⚠️ Wybierz min. jedno opakowanie dla tej linii.")
    
    st.sidebar.markdown("---")
# --- BEZPIECZNA INICJALIZACJA STRUKTUR W SESJI ---
if "prod_dict" not in st.session_state:
    st.session_state.prod_dict = {
        k: {"roczna": 1200000, "utilization": 75.0} for k in FUCHS_PORTFOLIO.keys()
    }

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

# Definiowanie domyślnych wartości struktur temperatur
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

# --- FUNKCJA CALLBACK BEZ ZALEŻNOŚCI OD ZMIENNYCH LOKALNYCH ---
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

# --- STRUKTURA PIĘCIU KART INTERFEJSU ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja", 
    "📐 2. Karta Maszyn i Dobór Pomp", 
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Koszty Produkcji",
    "🛢️ 5. Surowce i Park Zbiorników"
])

# ==========================================
# ZAKŁADKA 1: OPCJA AKCEPTACJI TYPOSZEREGU + SKUs + PODZIAŁ NA ZBIORNIKI
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych (Baza: {godziny_dziennie:.1f}h/dzień)")
    
    # Definicja dopuszczalnego typoszeregu pojemności mikserów fabryki
    TYPOSZEREG_MIKSEROW = [5, 7, 10, 15, 18, 21, 25, 31]
    
    if wybrane_kategorie:
        # Inicjalizacja struktur w session_state (zachowanie edycji użytkownika)
        for kat in wybrane_kategorie:
            if kat not in st.session_state.prod_dict:
                st.session_state.prod_dict[kat] = {"roczna": 1200000, "utilization": 75.0, "skus": 1, "num_tanks": 1, "use_typoszereg": False}
            if "skus" not in st.session_state.prod_dict[kat]:
                st.session_state.prod_dict[kat]["skus"] = 1
            if "num_tanks" not in st.session_state.prod_dict[kat]:
                st.session_state.prod_dict[kat]["num_tanks"] = 1
            if "use_typoszereg" not in st.session_state.prod_dict[kat]:
                st.session_state.prod_dict[kat]["use_typoszereg"] = False

        # Funkcja synchronizacji po edycji tabeli st.data_editor
        def sync_tab1_data():
            if "tab1_editor" in st.session_state:
                edits = st.session_state.tab1_editor.get("edited_rows", {})
                active_families = [k for k in FUCHS_PORTFOLIO.keys() if k in wybrane_kategorie]
                for idx, changes in edits.items():
                    if idx < len(active_families):
                        family_name = active_families[idx]
                        if "2. Roczna produkcja [kg] 🟦" in changes:
                            st.session_state.prod_dict[family_name]["roczna"] = changes["2. Roczna produkcja [kg] 🟦"]
                        if "3. Docelowa Utylizacja [%] 🟦" in changes:
                            st.session_state.prod_dict[family_name]["utilization"] = float(changes["3. Docelowa Utylizacja [%] 🟦"])
                        if "4. Liczba SKUs 🟦" in changes:
                            st.session_state.prod_dict[family_name]["skus"] = int(changes["4. Liczba SKUs 🟦"])
                        if "5. Użyj Typoszeregu 🟦" in changes:
                            st.session_state.prod_dict[family_name]["use_typoszereg"] = bool(changes["5. Użyj Typoszeregu 🟦"])

        calculated_matrix_rows = []
        oversized_reactors = {}

        # Przetwarzanie matematyczne każdej rodziny produktowej
        for kat in wybrane_kategorie:
            m_annual = st.session_state.prod_dict[kat]["roczna"]
            util_target = st.session_state.prod_dict[kat]["utilization"]
            skus = st.session_state.prod_dict[kat]["skus"]
            use_typo = st.session_state.prod_dict[kat]["use_typoszereg"]
            
            dens = FUCHS_PORTFOLIO[kat]["density"]
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            m_monthly = m_annual / 12
            allocated_hours = AVAILABLE_HOURS_MONTH * (util_target / 100.0)
            
            # Wyznaczenie bazowego gabarytu z docelowej utylizacji czasu
            raw_batches = math.ceil(allocated_hours / cyc) if allocated_hours > 0 else 1
            raw_batch_size_kg = math.ceil(m_monthly / raw_batches) if raw_batches > 0 else 0
            calculated_vol_m3 = raw_batch_size_kg / (dens * 1000.0) if raw_batch_size_kg > 0 else 0.0

            # Dopasowanie do najbliższego wyższego typoszeregu mikserów
            sug_vol = 0
            for v in TYPOSZEREG_MIKSEROW:
                if v >= calculated_vol_m3:
                    sug_vol = v
                    break
            if sug_vol == 0 and calculated_vol_m3 > 0:
                sug_vol = 31  # Limit górny konstrukcji transportowej

            # REAKCJA NA AKCEPTACJĘ TYPOSZEREGU:
            if use_typo and sug_vol > 0:
                final_vol_m3 = sug_vol
                batch_size_kg = final_vol_m3 * (dens * 1000.0)
                needed_batches = math.ceil(m_monthly / batch_size_kg) if batch_size_kg > 0 else 1
            else:
                final_vol_m3 = calculated_vol_m3
                batch_size_kg = raw_batch_size_kg
                needed_batches = raw_batches

            if final_vol_m3 > 31.0:
                oversized_reactors[kat] = final_vol_m3

            calculated_matrix_rows.append({
                "1. Nazwa rodziny 🔒": kat,
                "2. Roczna produkcja [kg] 🟦": int(m_annual),
                "3. Docelowa Utylizacja [%] 🟦": float(util_target),
                "4. Liczba SKUs 🟦": int(skus),
                "5. Użyj Typoszeregu 🟦": bool(use_typo),
                "6. Wyliczony gabaryt reaktora 🔒": round(calculated_vol_m3, 2),
                "7. Sugerowany Mikser (Typoszereg) 🔒": f"{sug_vol} m³" if sug_vol > 0 else "Poniżej minimum (<5 m³)",
                "h_vol": final_vol_m3, "h_batches": needed_batches, "h_kg": batch_size_kg, "h_annual": m_annual
            })

        df_complete_matrix = pd.DataFrame(calculated_matrix_rows)

        st.markdown("##### 📥 Krok A: Parametryzacja Tonażu, Utylizacji oraz SKUs")
        
        # Funkcja podświetlająca komórki, gdzie gabaryt jest mniejszy niż 5 m³
        def style_small_volumes(row):
            styles = [''] * len(row)
            val = row["6. Wyliczony gabaryt reaktora 🔒"]
            if isinstance(val, (int, float)) and val < 5.0:
                idx = row.index.get_loc("6. Wyliczony gabaryt reaktora 🔒")
                styles[idx] = 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
            return styles

        styled_matrix = df_complete_matrix.style.apply(style_small_volumes, axis=1)

        # Wyświetlenie tabeli edytowalnej w standardzie Streamlit v2026
        edited_table = st.data_editor(
            styled_matrix,
            hide_index=True,
            width="stretch",
            disabled=["1. Nazwa rodziny 🔒", "6. Wyliczony gabaryt reaktora 🔒", "7. Sugerowany Mikser (Typoszereg) 🔒"],
            column_config={
                "2. Roczna produkcja [kg] 🟦": st.column_config.NumberColumn(min_value=0, step=50000, format="%d"),
                "3. Docelowa Utylizacja [%] 🟦": st.column_config.NumberColumn(min_value=1.0, max_value=100.0, step=5.0, format="%.1f%%"),
                "4. Liczba SKUs 🟦": st.column_config.NumberColumn(min_value=1, step=1),
                "5. Użyj Typoszeregu 🟦": st.column_config.CheckboxColumn(),
                "6. Wyliczony gabaryt reaktora 🔒": st.column_config.NumberColumn(format="%.2f m³"),
                "h_vol": None, "h_batches": None, "h_kg": None, "h_annual": None
            },
            key="tab1_editor",
            on_change=sync_tab1_data
        )

        # Krok B: Dynamiczne pytania o przydział fizycznych zbiorników dla rodzin posiadających SKUs > 1
        st.markdown("<br>", unsafe_allow_html=True)
        any_sku_trigger = False
        for kat in wybrane_kategorie:
            current_skus = st.session_state.prod_dict[kat]["skus"]
            if current_skus > 1:
                if not any_sku_trigger:
                    st.markdown("##### 🛢️ Krok B: Przydział zbiorników dla rodzin z wieloma SKUs")
                    any_sku_trigger = True
                
                st.session_state.prod_dict[kat]["num_tanks"] = st.number_input(
                    f"Wykryto **{current_skus} SKUs** dla linii **{kat}**. Do ilu osobnych zbiorników przypisać tę rodzinę?",
                    min_value=1,
                    max_value=int(current_skus),
                    value=min(int(st.session_state.prod_dict[kat].get("num_tanks", 1)), int(current_skus)),
                    key=f"tanks_input_{kat}"
                )

        # Krok C: Obsługa sytuacji awaryjnej (przekroczenie gabarytu transportowego 31 m³)
        split_decisions = {}
        if oversized_reactors:
            st.warning("⚠️ **Wykryto przekroczenie dopuszczalnych gabarytów transportowych pojedynczego zbiornika (> 31 m³)!**")
            chk_cols = st.columns(len(oversized_reactors))
            for idx, (kat_over, vol_over) in enumerate(oversized_reactors.items()):
                with chk_cols[idx]:
                    split_decisions[kat_over] = st.checkbox(
                        f"Rozbij reaktor {kat_over} ({vol_over:.1f} m³) na mniejsze jednostki?",
                        value=True, key=f"chk_split_{kat_over}"
                    )

        # Krok D: Generowanie Końcowej Floty Mieszalników (z uwzględnieniem realnej utylizacji)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🏭 3. Skorygowana i Zweryfikowana Flota Mieszalników")
        
        final_fleet_rows = []
        total_annual_production = 0
        total_batches_per_month = 0
        total_calculated_volume_m3 = 0.0
        confirmed_mixers_blueprint = []
        tag_counter = 101

        for idx, r in df_complete_matrix.iterrows():
            kat = r["1. Nazwa rodziny 🔒"]
            vol_base = r["h_vol"]
            total_batches = r["h_batches"]
            total_annual = r["h_annual"]
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            tanks_count = st.session_state.prod_dict[kat]["num_tanks"]
            vol_per_tank = vol_base / tanks_count if tanks_count > 0 else vol_base
            batches_per_tank = math.ceil(total_batches / tanks_count) if tanks_count > 0 else total_batches
            annual_per_tank = total_annual / tanks_count

            if AVAILABLE_HOURS_MONTH > 0:
                real_utilization = (batches_per_tank * cyc) / AVAILABLE_HOURS_MONTH * 100.0
            else:
                real_utilization = 0.0

            if split_decisions.get(kat, False) and vol_per_tank > 31.0:
                remaining_vol = vol_per_tank
                sub_letter_ascii = 65 
                while remaining_vol > 62.0:
                    weight_fraction = 31.0 / vol_per_tank
                    mixer_annual = annual_per_tank * weight_fraction
                    mixer_batches = math.ceil(batches_per_tank * weight_fraction)
                    mixer_mass_batch = math.ceil((r["h_kg"]/tanks_count) * (31.0 / vol_per_tank))
                    
                    if AVAILABLE_HOURS_MONTH > 0:
                        split_util = (mixer_batches * cyc) / AVAILABLE_HOURS_MONTH * 100.0
                    else:
                        split_util = 0.0
                    
                    for t_idx in range(tanks_count):
                        tag_id = f"MT-{tag_counter}{chr(sub_letter_ascii)}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                        final_fleet_rows.append({
                            "ID Urządzenia 🔒": tag_id, "Przypisana Linia 🔒": kat,
                            "Liczba szarż [/mies] 🔒": int(mixer_batches), "Realna Utylizacja [%] 🔒": round(split_util, 1),
                            "Realna Pojemność [m³] 🔒": 31.0, "Masa Szarży [kg] 🔒": int(mixer_mass_batch), 
                            "Status 🔒": "🧱 Max Gabaryt (31.0 m³)"
                        })
                        confirmed_mixers_blueprint.append({
                            "tag": tag_id, "product_family": kat, "capacity_m3": 31.0,
                            "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": mixer_batches,
                            "mass_per_batch": mixer_mass_batch, "annual_volume": mixer_annual
                        })
                        total_calculated_volume_m3 += 31.0
                        total_batches_per_month += mixer_batches
                    
                    remaining_vol -= 31.0
                    sub_letter_ascii += 1
                
                if remaining_vol > 0:
                    split_tail_vol = remaining_vol / 2.0
                    weight_fraction_tail = split_tail_vol / vol_per_tank
                    tail_annual = annual_per_tank * weight_fraction_tail
                    tail_batches = math.ceil(batches_per_tank * weight_fraction_tail)
                    tail_mass_batch = math.ceil((r["h_kg"]/tanks_count) * (split_tail_vol / vol_per_tank))
                    
                    if AVAILABLE_HOURS_MONTH > 0:
                        tail_util = (tail_batches * cyc) / AVAILABLE_HOURS_MONTH * 100.0
                    else:
                        tail_util = 0.0
                    
                    for t_idx in range(tanks_count):
                        for _ in range(2):
                            tag_id = f"MT-{tag_counter}{chr(sub_letter_ascii)}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                            final_fleet_rows.append({
                                "ID Urządzenia 🔒": tag_id, "Przypisana Linia 🔒": kat,
                                "Liczba szarż [/mies] 🔒": int(tail_batches), "Realna Utylizacja [%] 🔒": round(tail_util, 1),
                                "Realna Pojemność [m³] 🔒": round(split_tail_vol, 1), "Masa Szarży [kg] 🔒": int(tail_mass_batch), 
                                "Status 🔒": "🟢 Bliźniak Konstrukcyjny"
                            })
                            confirmed_mixers_blueprint.append({
                                "tag": tag_id, "product_family": kat, "capacity_m3": max(split_tail_vol, 0.5),
                                "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": tail_batches,
                                "mass_per_batch": tail_mass_batch, "annual_volume": tail_annual
                            })
                            total_calculated_volume_m3 += split_tail_vol
                            total_batches_per_month += tail_batches
                            sub_letter_ascii += 1
            else:
                if vol_per_tank < 5.0:
                    status_txt = "⚠️ Poniżej minimum typoszeregu"
                elif vol_per_tank > 31.0:
                    status_txt = "🔴 Za duży (>31 m³)"
                else:
                    status_txt = "✅ Przydział SKUs" if tanks_count > 1 else "✅ Optymalny"
                
                for t_idx in range(tanks_count):
                    tag_id = f"MT-{tag_counter}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                    mass_batch = math.ceil(r["h_kg"] / tanks_count)
                    
                    final_fleet_rows.append({
                        "ID Urządzenia 🔒": tag_id, "Przypisana Linia 🔒": kat,
                        "Liczba szarż [/mies] 🔒": int(batches_per_tank), "Realna Utylizacja [%] 🔒": round(real_utilization, 1),
                        "Realna Pojemność [m³] 🔒": round(vol_per_tank, 1), "Masa Szarży [kg] 🔒": int(mass_batch), 
                        "Status 🔒": status_txt
                    })
                    confirmed_mixers_blueprint.append({
                        "tag": tag_id, "product_family": kat, "capacity_m3": max(vol_per_tank, 0.5),
                        "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": batches_per_tank,
                        "mass_per_batch": mass_batch, "annual_volume": annual_per_tank
                    })
                    total_calculated_volume_m3 += vol_per_tank
                    total_batches_per_month += batches_per_tank

            total_annual_production += total_annual
            tag_counter += 1

        df_final_fleet = pd.DataFrame(final_fleet_rows)
        st.dataframe(
            df_final_fleet,
            hide_index=True,
            width="stretch",
            column_config={
                "Realna Utylizacja [%] 🔒": st.column_config.NumberColumn(format="%.1f%%"),
                "Realna Pojemność [m³] 🔒": st.column_config.NumberColumn(format="%.1f m³"),
                "Masa Szarży [kg] 🔒": st.column_config.NumberColumn(format="%d kg")
            }
        )

        st.markdown("<br>", unsafe_allow_html=True)
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1: st.metric(label="📈 Sumaryczny tonaż roczny", value=f"{total_annual_production:,} kg")
        with sum_col2: st.metric(label="🔄 Całkowita liczba szarż / miesiąc", value=f"{total_batches_per_month} szarż")
        with sum_col3: st.metric(label="📐 Sumaryczna pojemność floty", value=f"{total_calculated_volume_m3:.1f} m³")
            
        st.markdown("---")
        if st.button("📥 Zatwierdź i wyślij konfigurację do kolejnych kroków", type="primary", use_container_width=True):
            st.session_state.confirmed_mixers = confirmed_mixers_blueprint
            if "master_logistics_df" in st.session_state:
                del st.session_state["master_logistics_df"]
            st.success(f"🎉 Sukces! Zapisano stabilną strukturę floty złożoną z {len(confirmed_mixers_blueprint)} urządzeń.")
# ==========================================
# ZAKŁADKA 2: ZAAWANSOWANE DEDYKOWANE KONFIGURATORY PROCESOWE PER REAKTOR
# ==========================================
with tab2:
    st.header("📐 Specyfikacja Maszyn i Zaawansowane Konfiguratory Układów")

    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.info("💡 Aby wygenerować specyfikację, najpierw zatwierdź konfigurację floty w **Zakładce 1**.")
    else:
        st.markdown("### ⚙️ Interaktywne Wymiarowanie i Dostrajanie Floty Maszynowej")
        st.caption("Poniższe sekcje pozwalają na niezależne symulowanie i optymalizację parametrów termodynamicznych, mieszania i rozładunku dla każdego zbiornika osobno.")

        mixers_fleet = st.session_state.confirmed_mixers
        spec_rows = []

        # Pętla generuje niezależny, pełny konfigurator inżynieryjny dla każdego zatwierdzonego reaktora
        for m in mixers_fleet:
            tag = m["tag"]
            kat = m["product_family"]
            v_working = m["capacity_m3"]
            mass_batch_kg = m["mass_per_batch"]
            
            # Pobranie wyjściowej gęstości z bazy globalnej FUCHS
            rho_product = FUCHS_PORTFOLIO[kat]["density"] * 1000.0  # kg/m³
            default_material = FUCHS_PORTFOLIO[kat]["material"]

            st.markdown(f"---")
            st.markdown(f"### 🔮 Zaawansowany Konfigurator Instancji: **{tag}** ({kat})")

            # GŁÓWNY PODZIAŁ NA TRZY SPECJALISTYCZNE BLOKI KONFIGURACYJNE
            tab_grzanie, tab_mieszadlo, tab_pompa = st.tabs([
                "🔥 1. Układ Termiczny i Grzanie", 
                "⚙️ 2. Kinematyka i Moc Mieszadła", 
                "🔄 3. Układ Hydrauliczny i Pompa"
            ])

            # ------------------------------------------------------------------
            # CONFIGURATOR 1: UKŁAD TERMICZNY (GRZANIE / CHŁODZENIE)
            # ------------------------------------------------------------------
            with tab_grzanie:
                st.markdown("##### Parametryzacja Bilansu Cieplnego i Mediów Energetycznych")
                
                col_h1, col_h2, col_h3 = st.columns(3)
                with col_h1:
                    mat_reaktora = st.selectbox(f"Materiał korpusu ({tag}):", ["Stal węglowa (zwykła)", "Stal nierdzewna (SS316L)"], index=0 if "zwykła" in default_material else 1, key=f"mat_{tag}")
                    medium_term = st.selectbox(f"Typ nośnika energii ({tag}):", ["Para wodna nasycona", "Olej termalny", "Gorąca woda procesowa"], key=f"med_{tag}")
                with col_h2:
                    T_in_prod = st.number_input(f"Temp. początkowa oleju T1 [°C] ({tag}):", value=20.0, step=5.0, key=f"t1_{tag}")
                    T_out_prod = st.number_input(f"Temp. docelowa oleju T2 [°C] ({tag}):", value=70.0, step=5.0, key=f"t2_{tag}")
                with col_h3:
                    t_in_carrier = st.number_input(f"Temp. wlotowa nośnika t1 [°C] ({tag}):", value=120.0, step=5.0, key=f"t_car_{tag}")
                    fouling_factor = st.slider(f"Współczynnik zabrudzenia wężownicy (Fouling) [%]:", min_value=0, max_value=40, value=15, step=5, key=f"foul_{tag}")

                # Dobór fizycznego współczynnika k na bazie dobranych materiałów
                if "nierdzewna" in mat_reaktora:
                    k_base = 0.55 if "Para" in medium_term else (0.30 if "Olej" in medium_term else 0.40)
                else:
                    k_base = 0.95 if "Para" in medium_term else (0.45 if "Olej" in medium_term else 0.60)
                
                # Korekta k o naddatek zabrudzenia (fouling)
                k_actual = k_base * (1.0 - (fouling_factor / 100.0))
                
                # Dodatkowe zaawansowane parametry wejściowe strumienia mediów
                col_h4, col_h5 = st.columns(2)
                with col_h4:
                    v_flow_l_min = st.number_input(f"Strumień objętościowy nośnika [l/min] ({tag}):", min_value=10.0, max_value=2000.0, value=410.0, step=10.0, key=f"vflow_{tag}")
                with col_h5:
                    c_p_product = st.number_input(f"Ciepło właściwe produktu [kJ/(kg·K)] ({tag}):", value=float(FUCHS_PORTFOLIO[kat]["cp"]), step=0.1, key=f"cpprod_{tag}")

                # Geometria: Automatyczne nieliniowe skalowanie powierzchni wymiany ciepła na bazie T5 (A=17m2 dla 10m3)
                scaled_area_m2 = 17.0 * ((v_working / 10.0) ** (2/3))
                
                # --- MATEMATYCZNY RYGORSTYCZNY MODEL PROFILU TEMPERATUR (Prawa Fizyki) ---
                c_p_carrier = 4.184 if "woda" in medium_term.lower() else (2.1 if "olej" in medium_term.lower() else 4.2)
                w_mass_flow = (v_flow_l_min / 60.0) * 1.0  # kg/s (założenie gęstości wody)
                w_heat_cap_kw_k = w_mass_flow * c_p_carrier  # Pojemność cieplna strumienia

                # NTU układu wężownicy
                if w_heat_cap_kw_k > 0:
                    ntu = (k_actual * scaled_area_m2) / w_heat_cap_kw_k
                    # Współczynnik sprawności dynamicznej wężownicy (Dynamic Exhaust Factor)
                    # Zapobiega błędom matematycznym i odzwierciedla spadek temp nośnika na wylocie
                    coil_efficiency = (1.0 - math.exp(-ntu)) / ntu if ntu > 0 else 1.0
                else:
                    coil_efficiency = 0.0

                # Wyznaczenie realnych, fizycznych sił napędowych na starcie i końcu procesu szarży
                dT_start = abs(t_in_carrier - T_in_prod) * coil_efficiency
                dT_final = abs(t_in_carrier - T_out_prod) * coil_efficiency

                # Obliczenie poprawnego LMTD
                if dT_start == dT_final:
                    lmtd_real = dT_start
                elif dT_start > 0 and dT_final > 0:
                    lmtd_real = (dT_start - dT_final) / math.log(dT_start / dT_final)
                else:
                    lmtd_real = 0.1

                # Bilans energii i czasu
                Q_total_kj = mass_batch_kg * c_p_product * abs(T_out_prod - T_in_prod)
                Q_total_kwh = Q_total_kj / 3600.0
                
                power_transfer_kw = k_actual * scaled_area_m2 * lmtd_real
                time_heat_h = (Q_total_kj / power_transfer_kw / 3600.0) if power_transfer_kw > 0 else 0.0

                st.metric("Wyliczone zapotrzebowanie na energię cieplną szarży", f"{int(Q_total_kwh):,} kWh", delta=f"Czas operacji: {time_heat_h:.2f} h")

            # ------------------------------------------------------------------
            # CONFIGURATOR 2: UKŁAD MECHANICZNEGO MIESZANIA (AGITATOR)
            # ------------------------------------------------------------------
            with tab_mieszadlo:
                st.markdown("##### Specyfikacja Hydrodynamiczna i Kinematyka Wirnika")
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    typ_wirnika = st.selectbox(f"Geometria wirnika ({tag}):", list(AGITATOR_TYPES.keys()), index=1, key=f"agit_type_{tag}")
                with col_m2:
                    obroty_rpm = st.number_input(f"Obroty mieszadła n [RPM] ({tag}):", min_value=10, max_value=500, value=90, step=10, key=f"rpm_{tag}")
                with col_m3:
                    motor_efficiency = st.slider(f"Sprawność przekładni i silnika [%] ({tag}):", min_value=50, max_value=98, value=85, step=1, key=f"eff_mot_{tag}")

                # Modelowanie średnicy wirnika (1/3 średnicy zbiornika wyznaczonej z gabarytu)
                D_vessel = 2.2 * ((v_working / 10.0) ** (1/3))
                d_impeller = D_vessel / 3.0
                n_rps = obroty_rpm / 60.0

                # Obliczenie Liczby Reynoldsa dla mieszania przy lepkości projektowej 500 cSt
                visc_dyn_pas = (500.0 / 1_000_000.0) * rho_product
                Re_mixing = (n_rps * (d_impeller ** 2) * rho_product) / max(visc_dyn_pas, 0.0001)
                
                cfg_mix = AGITATOR_TYPES[typ_wirnika]
                Ne_power = cfg_mix["laminar_C"] / Re_mixing if Re_mixing < 50 else cfg_mix["turbulent_Ne"]
                
                # Wyznaczenie mocy na wale i poboru mocy z sieci (z zapasem inżynieryjnym 25%)
                power_shaft_w = Ne_power * (n_rps ** 3) * (d_impeller ** 5) * rho_product
                power_electric_kw = (power_shaft_w / (motor_efficiency / 100.0) * 1.25) / 1000.0
                power_electric_kw = max(power_electric_kw, 1.5)  # Minimalny silnik strukturalny

                st.success(f"⚙️ **Rekomendowany napęd:** Silnik asynchroniczny o mocy min. **{power_electric_kw:.1f} kW** (Liczba Reynoldsa Re: {int(Re_mixing)})")

            # ------------------------------------------------------------------
            # CONFIGURATOR 3: UKŁAD HYDRAULICZNEGO ROZŁADUNKU (POMPA)
            # ------------------------------------------------------------------
            with tab_pompa:
                st.markdown("##### Wymiarowanie Linii Rurowej i Strat Ciśnienia (Darcy-Weisbach)")
                
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    q_user_m3_h = st.number_input(f"Wydajność pompy Q [m³/h] ({tag}):", min_value=1.0, value=float(round(v_working / 0.75, 1)), key=f"qp_{tag}")
                    pipe_l_m = st.number_input(f"Długość rurociągu tłocznego L [m] ({tag}):", min_value=1.0, value=15.0, key=f"pl_{tag}")
                with col_p2:
                    pipe_d_mm = st.number_input(f"Średnica wewnętrzna rury D [mm] ({tag}):", min_value=25, max_value=300, value=80, key=f"pd_{tag}")
                    roughness_mm = st.number_input(f"Chropowatość bezwzględna rury k_r [mm] ({tag}):", value=0.05, format="%.3f", key=f"pr_{tag}")
                with col_p3:
                    h_static_m = st.number_input(f"Wysokość geometryczna podnoszenia H_stat [m] ({tag}):", value=3.0, key=f"ph_{tag}")
                    pump_eff_pct = st.slider(f"Sprawność hydrauliczna pompy [%] ({tag}):", min_value=30, max_value=90, value=65, step=5, key=f"peff_{tag}")

                # Mechanika Płynów: Prędkość i straty tarcia rurociągu
                D_pipe_m = pipe_d_mm / 1000.0
                area_pipe_m2 = (math.pi * (D_pipe_m ** 2)) / 4.0
                v_velocity_m_s = (q_user_m3_h / 3600.0) / area_pipe_m2
                
                Re_pipe = (v_velocity_m_s * D_pipe_m * rho_product) / max(visc_dyn_pas, 0.0001)
                
                # Wyznaczenie współczynnika strat liniowych lambda
                if Re_pipe < 2100:
                    lambda_p = 64.0 / max(Re_pipe, 1.0)
                    przeplyw_status = "Laminarny (Duże opory tarcia wewnętrznego)"
                else:
                    lambda_p = 0.3164 / (Re_pipe ** 0.25)
                    przeplyw_status = "Turbulentny"
                
                # Równanie Darcy-Weisbacha
                loss_head_m = lambda_p * (pipe_l_m / D_pipe_m) * ((v_velocity_m_s ** 2) / (2.0 * 9.81))
                total_head_m = h_static_m + loss_head_m
                press_bar = (rho_product * 9.81 * total_head_m) / 100000.0
                
                # Dobór napędu pompy
                pump_power_el_kw = (q_user_m3_h * press_bar) / (36.0 * (pump_eff_pct / 100.0)) * 1.20
                pump_power_el_kw = max(pump_power_el_kw, 0.75)
                
                # Inteligentny dobór typu maszyny hydraulicznej ze względu na reologię
                p_type_rec = "Śrubowa (Wyporowa - zalecana dla FUCHS)" if visc_dyn_pas > 0.1 else "Odśrodkowa przemysłowa"

                st.warning(f"🔄 **Typ pompy:** {p_type_rec} | Przepływ: {przeplyw_status} | Wymagane ciśnienie instalacji: **{press_bar:.2f} bar**")

            # Zbieranie danych wyjściowych z konfiguratorów do głównej tabeli zbiorczej poniżej
            spec_rows.append({
                "Tag urządzenia 🔒": tag,
                "Pojemność robocza [m³]": round(v_working, 1),
                "Współczynnik k [kW/m²K]": round(k_actual, 3),
                "Moc Mieszadła [kW] ⚙️": round(power_electric_kw, 1),
                "Moc Pompy [kW] 🔄": round(pump_power_el_kw, 1),
                "Energia szarży [kWh] ⚡": int(Q_total_kwh),
                "Średnia delta LMTD [°C]": round(lmtd_real, 1),
                "Czas operacji [h] ⏱️": round(time_heat_h, 2)
            })

        # ------------------------------------------------------------------
        # GRID 3: ZBIORCZA KARTA WYNIKOWA I DYNAMICZNY BILANS MASZYNOWY
        # ------------------------------------------------------------------
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📊 3. Główna Karta Specyfikacji Technicznej Floty")
        st.caption("Poniższe zestawienie agreguje na żywo wyniki ze wszystkich powyższych konfiguratorów jednostkowych.")

        df_spec = pd.DataFrame(spec_rows)

        def style_lmtd_cells(row):
            styles = [''] * len(row)
            val = row["Średnia delta LMTD [°C]"]
            if isinstance(val, (int, float)):
                idx = row.index.get_loc("Średnia delta LMTD [°C]")
                if val < 15.0:
                    styles[idx] = 'background-color: #fff2cc; color: #b78103; font-weight: bold;'  # Za mały przepływ / niska siła
                elif val > 55.0:
                    styles[idx] = 'background-color: #fce8e6; color: #a51d24; font-weight: bold;'  # Ryzyko przypalenia oleju
                else:
                    styles[idx] = 'background-color: #e6f4ea; color: #137333; font-weight: bold;'  # Zakres optymalny
            return styles

        styled_df_spec = df_spec.style.apply(style_lmtd_cells, axis=1)

        st.dataframe(
            styled_df_spec,
            hide_index=True,
            width="stretch",
            column_config={
                "Pojemność robocza [m³]": st.column_config.NumberColumn(format="%.1f m³"),
                "Współczynnik k [kW/m²K]": st.column_config.NumberColumn(format="%.3f kW/m²K"),
                "Moc Mieszadła [kW] ⚙️": st.column_config.NumberColumn(format="%.1f kW"),
                "Moc Pompy [kW] 🔄": st.column_config.NumberColumn(format="%.1f kW"),
                "Energia szarży [kWh] ⚡": st.column_config.NumberColumn(format="%d kWh"),
                "Średnia delta LMTD [°C]": st.column_config.NumberColumn(format="%.1f °C"),
                "Czas operacji [h] ⏱️": st.column_config.NumberColumn(format="%.2f h")
            }
        )
# ==========================================
# ZAKŁADKA 3: LOGISTYKA, CZAS ROZLEWU I GOSPODARKA PALETOWA
# ==========================================
with tab3:
    st.header("📦 Analiza Logistyczna, Czas Rozlewu i Gospodarka Paletowa")

    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.info("💡 Aby przeprowadzić analizę logistyczną, najpierw zatwierdź konfigurację floty w **Zakładce 1**.")
    else:
        # Pobranie danych o produkcji z floty mieszalników
        mixers_fleet = st.session_state.confirmed_mixers
        opakowania_podzial = st.session_state.get("opakowania_podzial", {})
        
        # Wyznaczenie sumarycznego tonażu miesięcznego per rodzina
        tonaz_miesieczny_per_rodzina = {}
        for m in mixers_fleet:
            kat = m["product_family"]
            # szarże/miesiąc * masa_szarży
            masa_miesieczna = m["batches_count"] * m["mass_per_batch"]
            tonaz_miesieczny_per_rodzina[kat] = tonaz_miesieczny_per_rodzina.get(kat, 0) + masa_miesieczna

        # --- PARAMETRYZACJA GOSPODARKI MAGAZYNOWEJ ---
        st.markdown("### 🏢 1. Parametryzacja Magazynu Wyrobów Gotowych")
        c_log1, c_log2 = st.columns(2)
        with c_log1:
            czas_skladowania_dni = st.number_input(
                "Średni czas składowania palety w magazynie (Rotacja) [dni]:", 
                min_value=1, 
                max_value=90, 
                value=14, 
                step=1,
                help="Przez ile dni gotowa paleta średnio przebywa w magazynie przed wysyłką do klienta/dystrybutora."
            )
        with c_log2:
            # Liczba dni roboczych/wysyłkowych w miesiącu na podstawie bazy z panelu bocznego (250 dni / 12 miesięcy)
            dni_robocze_miesiac = 250.0 / 12.0
            st.metric("Wyliczone dni wysyłkowe / miesiąc", f"{dni_robocze_miesiac:.2f} dnia")

        st.markdown("---")

        # ==========================================
        # SEKCJA 1: SYMULACJA MIESZANA (REALNY SPLIT PRODUKCJI + PALETY)
        # ==========================================
        st.markdown("### 🔀 2. Symulacja Mieszana (Realny Split i Zapotrzebowanie na Miejsca Paletowe)")
        st.caption("Wyliczenia logistyczne odzwierciedlające zadeklarowany podział strumienia produkcyjnego oraz wymaganej pojemności magazynu.")

        real_split_rows = []
        total_real_pallets_month = 0
        total_real_pallet_slots_needed = 0

        for kat, total_mass_month in tonaz_miesieczny_per_rodzina.items():
            wybrane_dla_linii = st.session_state.get(f"packs_{kat}", [])
            
            # Wymagania magazynowe / przechowywania na bazie właściwości rodziny
            if "Water-miscible" in kat or "ECOCOOL" in kat:
                storage_req = "❄️ Frost Sensitive (Min +5°C), Wymaga strefy grzanej"
            elif "Engine Oils" in kat:
                storage_req = "🔥 Klasa pożarowa III, Standard"
            else:
                storage_req = "🟢 Standard, Brak specjalnych obostrzeń"

            for p in wybrane_dla_linii:
                key_id = f"pct_{kat}_{p}"
                udzial_pct = opakowania_podzial.get(key_id, 0.0)
                
                if udzial_pct > 0:
                    masa_opakowania_month = total_mass_month * (udzial_pct / 100.0)
                    
                    pack_capacity_l = PACK_CONFIGS[p]["size_l"]
                    pack_capacity_kg = pack_capacity_l * FUCHS_PORTFOLIO[kat]["density"]
                    liczba_sztuk_month = math.ceil(masa_opakowania_month / pack_capacity_kg) if pack_capacity_kg > 0 else 0
                    
                    wydajnosc_szt_h = PACK_CONFIGS[p]["rate_szt_h"]
                    czas_rozlewu_h = liczba_sztuk_month / wydajnosc_szt_h if wydajnosc_szt_h > 0 else 0.0
                    
                    # --- MODELOWANIE STRUMIENIA PALETOWEGO ---
                    szt_na_palecie = PACK_CONFIGS[p]["per_pallet"]
                    liczba_palet_month = math.ceil(liczba_sztuk_month / szt_na_palecie) if szt_na_palecie > 0 else 0
                    total_real_pallets_month += liczba_palet_month
                    
                    # Równanie bilansu statycznego: miejsca_paletowe = (palety_miesiecznie / dni_robocze) * czas_skladowania
                    miejsca_paletowe_w_magazynie = math.ceil((liczba_palet_month / dni_robocze_miesiac) * czas_skladowania_dni)
                    total_real_pallet_slots_needed += miejsca_paletowe_w_magazynie
                    
                    real_split_rows.append({
                        "Linia produktowa 🔒": kat,
                        "Typ Opakowania 📦": p,
                        "Udział [%]": f"{udzial_pct:.1f}%",
                        "Liczba opakowań [/mies]": int(liczba_sztuk_month),
                        "Palety [EPAL/mies] 🧱": int(liczba_palet_month),
                        "Wymagane Miejsca Paletowe [szt] 📐": int(miejsca_paletowe_w_magazynie),
                        "Czas składowania palety [dni] ⏱️": czas_skladowania_dni,
                        "Czas pracy linii rozlewu [h] ⏱️": round(czas_rozlewu_h, 1),
                        "Wymagania Przechowywania ⚠️": storage_req
                    })

        if real_split_rows:
            df_real_split = pd.DataFrame(real_split_rows)
            st.dataframe(
                df_real_split,
                hide_index=True,
                width="stretch",
                column_config={
                    "Liczba opakowań [/mies]": st.column_config.NumberColumn(format="%d szt."),
                    "Palety [EPAL/mies] 🧱": st.column_config.NumberColumn(format="%d EPAL"),
                    "Wymagane Miejsca Paletowe [szt] 📐": st.column_config.NumberColumn(format="%d miejsc"),
                    "Czas składowania palety [dni] ⏱️": st.column_config.NumberColumn(format="%d dni"),
                    "Czas pracy linii rozlewu [h] ⏱️": st.column_config.NumberColumn(format="%.1f h")
                }
            )
        else:
            st.warning("⚠️ Brak zdefiniowanych udziałów procentowych w panelu bocznym lub nie wybrano opakowań.")


        # ==========================================
        # SEKCJA 2: SYMULACJA STRUKTURY 100% (SCENARIUSZE SKRAJNE)
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📊 3. Symulacja Scenariuszy 100% (Maksymalna pojemność i skrajne obciążenia)")
        st.caption("Symulacja pokazująca wymogi logistyczne, gdyby **cały miesięczny tonaż danej rodziny** został skierowany wyłącznie do jednego typu opakowania.")

        simulation_100_rows = []

        for kat, total_mass_month in tonaz_miesieczny_per_rodzina.items():
            for p_type in PACK_CONFIGS.keys():
                pack_capacity_l = PACK_CONFIGS[p_type]["size_l"]
                pack_capacity_kg = pack_capacity_l * FUCHS_PORTFOLIO[kat]["density"]
                
                liczba_sztuk_100 = math.ceil(total_mass_month / pack_capacity_kg) if pack_capacity_kg > 0 else 0
                
                wydajnosc_szt_h = PACK_CONFIGS[p_type]["rate_szt_h"]
                czas_rozlewu_100_h = liczba_sztuk_100 / wydajnosc_szt_h if wydajnosc_szt_h > 0 else 0.0
                
                # Obliczenia gabarytów paletowych i przestrzennych dla wariantu 100%
                szt_na_palecie = PACK_CONFIGS[p_type]["per_pallet"]
                liczba_palet_100 = math.ceil(liczba_sztuk_100 / szt_na_palecie) if szt_na_palecie > 0 else 0
                miejsca_paletowe_100 = math.ceil((liczba_palet_100 / dni_robocze_miesiac) * czas_skladowania_dni)
                
                simulation_100_rows.append({
                    "Linia produktowa 🔒": kat,
                    "Wariant opakowania (100%) 📦": p_type,
                    "Wymagana liczba sztuk przy 100%": int(liczba_sztuk_100),
                    "Skrajny obrót palet [EPAL/mies]": int(liczba_palet_100),
                    "Skrajne Miejsca Paletowe [szt] 📐": int(miejsca_paletowe_100),
                    "Skrajny czas rozlewu [h] ⏱️": round(czas_rozlewu_100_h, 1)
                })

        df_sim_100 = pd.DataFrame(simulation_100_rows)
        
        wybrana_linia_filtr = st.selectbox("Filtruj scenariusze 100% dla linii:", ["Wszystkie"] + list(tonaz_miesieczny_per_rodzina.keys()))
        
        if wybrana_linia_filtr != "Wszystkie":
            df_sim_100_filtered = df_sim_100[df_sim_100["Linia produktowa 🔒"] == wybrana_linia_filtr]
        else:
            df_sim_100_filtered = df_sim_100

        st.dataframe(
            df_sim_100_filtered,
            hide_index=True,
            width="stretch",
            column_config={
                "Wymagana liczba sztuk przy 100%": st.column_config.NumberColumn(format="%d szt."),
                "Skrajny obrót palet [EPAL/mies]": st.column_config.NumberColumn(format="%d EPAL/mies"),
                "Skrajne Miejsca Paletowe [szt] 📐": st.column_config.NumberColumn(format="%d miejsc"),
                "Skrajny czas rozlewu [h] ⏱️": st.column_config.NumberColumn(format="%.1f h")
            }
        )

        # ==========================================
        # GLOBALNA TABLICA KPI - PODSUMOWANIE POTOKU
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📊 Zbiorcze wskaźniki KPI gospodarki magazynowej (Wariant Realny):")
        
        sum_log1, sum_log2, sum_log3 = st.columns(3)
        with sum_log1:
            st.metric(label="🧱 Całkowity obrót paletowy fabryki", value=f"{total_real_pallets_month:,} EPAL/miesiąc")
        with sum_log2:
            st.metric(label="📐 WYMAGANA LICZBA MIEJSC PALETOWYCH (Pojemność statyczna)", value=f"{total_real_pallet_slots_needed} szt.", delta="Miejsca w regałach")
        with sum_log3:
            st.metric(label="⏱️ Średni czas składowania palety", value=f"{czas_skladowania_dni} dni", delta="Rotacja wyrobów")

        # ==========================================
        # PODSUMOWANIE KROKU LOGISTYCZNEGO
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("""
        **💡 Wnioski z analizy intralogistycznej i magazynowej:**
        * **Pojemność statyczna (Miejsca paletowe):** Wyznacza minimalny gabaryt magazynu wysokiego składowania (MWS) niezbędny do bezpiecznego buforowania produkcji przed wysyłką bez ryzyka zatkania linii konfekcyjnych.
        * **Zależność czasu składowania:** Skrócenie czasu przebywania palety (np. poprzez sprawniejszą awizację transportów) drastycznie zmniejsza wymaganą liczbę miejsc paletowych, optymalizując koszty inwestycyjne infrastruktury FUCHS.
        """)
# ==========================================
# ZAKŁADKA 4: FINANSE - BILANSE MOCY ELEKTRYCZNEJ
# ==========================================
with tab4:
    st.header("💰 Optymalizacja Kosztów Energii i Bilans Finansowy")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych. Uruchom konfigurację w Zakładce 1.")
    else:
        st.markdown("### ⚡ 1. Taryfy i Parametry Ekonomiczne")
        waluta = st.selectbox("Wybierz walutę operacyjną:", ["PLN", "EUR", "USD"])
        default_cost = 2.119 if waluta == "PLN" else 0.535
        default_energy_rate = 750.0 if waluta == "PLN" else 160.0 
        
        c_fin1, c_fin2 = st.columns(2)
        with c_fin1: manuf_cost_per_kg = st.number_input(f"Bazowy Manufacturing Cost [za kg] w {waluta}:", min_value=0.01, value=default_cost, format="%.3f")
        with c_fin2: cena_mwh = st.number_input(f"Cena energii elektrycznej i cieplnej [{waluta}/MWh]:", min_value=1.0, value=default_energy_rate, format="%.2f")
        
        financial_summary = []
        total_monthly_saving_thermal = 0.0
        total_base_manuf_cost = 0.0
        total_mixing_energy_kwh = 0.0
        total_pumping_energy_kwh = 0.0
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            m_monthly_kg = mixer["annual_volume"] / 12
            batches_per_month = mixer["batches_count"]
            
            # Rekonstrukcja dynamiczna mocy i energii pobieranej z Zakładki 2
            d_agitor = round(round(2.2 * ((mixer["capacity_m3"] / 10.0) ** (1/3)), 2) / 3, 2)
            P_max_w = 2.5 * (1.5 ** 3) * (d_agitor ** 5) * (prod_info["density"] * 1000.0)
            motor_power_kw = max((P_max_w / 0.85 * 1.20) / 1000.0, 0.75)
            mixing_energy_month_kwh = motor_power_kw * prod_info["cycle_h"] * batches_per_month
            
            default_q_pump = float(max(round((mixer["capacity_m3"] / 0.75) * 1.25, 1), 5.0))
            pump_power_kw = max((default_q_pump * 2.5) / (36.0 * 0.60) * 1.15, 0.37)
            pumping_energy_month_kwh = pump_power_kw * (mixer["capacity_m3"] / default_q_pump) * batches_per_month
            
            total_mixing_energy_kwh += mixing_energy_month_kwh
            total_pumping_energy_kwh += pumping_energy_month_kwh
            cost_el_node = ((mixing_energy_month_kwh + pumping_energy_month_kwh) / 1000.0) * cena_mwh
            
            t_max_mix = st.session_state.heat_temps.get(mixer["tag"], 60.0)
            t_rozlew = st.session_state.filling_temps.get(mixer["tag"], 30.0)
            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg
            total_base_manuf_cost += base_manuf_cost_monthly
            
            oszczednosc_cieplna_mies = 0.0
            energia_cieplna_mwh_mies = 0.0
            if t_rozlew < t_max_mix:
                energia_cieplna_mwh_mies = (m_monthly_kg * prod_info["cp"] * (t_max_mix - t_rozlew)) / 3_600_000.0
                oszczednosc_cieplna_mies = energia_cieplna_mwh_mies * cena_mwh
                total_monthly_saving_thermal += oszczednosc_cieplna_mies
                
            financial_summary.append({
                "Reaktor": mixer["tag"], "Miesięczny tonaż [kg]": int(m_monthly_kg),
                "Energia Mieszania [kWh/m]": round(mixing_energy_month_kwh, 1), "Energia Pompowania [kWh/m]": round(pumping_energy_month_kwh, 1),
                "Koszt energii el.": f"{cost_el_node:.2f} {waluta}", "Oszczędność termiczna": f"- {oszczednosc_cieplna_mies:.2f} {waluta}"
            })
            
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("⚡ Globalne koszty zużycia prądu fabryki:")
        cost_total_el = ((total_mixing_energy_kwh + total_pumping_energy_kwh) / 1000.0) * cena_mwh
        
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1: st.metric("⚙️ Zużycie: Mieszanie", f"{total_mixing_energy_kwh:,.1f} kWh/m")
        with s_col2: st.metric("🔄 Zużycie: Przepompowanie", f"{total_pumping_energy_kwh:,.1f} kWh/m")
        with s_col3: st.metric("🔌 Łączny koszt energii el.", f"{cost_total_el:,.2f} {waluta}/mies")
        
        st.markdown("---")
        final_manufacturing_cost = total_base_manuf_cost + cost_total_el - total_monthly_saving_thermal
        st.metric(label="🚀 ZOPTYMALIZOWANY REALNY KOSZT WYTWORZENIA (Miesięcznie)", value=f"{final_manufacturing_cost:,.2f} {waluta}")

# ==========================================
# ZAKŁADKA 5: RAW MATERIAL (SUROWCE I TANK FARM)
# ==========================================
with tab5:
    st.header("🛢️ Logistyka Surowcowa i Wymiarowanie Parku Zbiorników")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych technicznych. Uruchom konfigurację w Zakładce 1.")
    else:
        st.markdown("### ⚙️ 1. Parametry Strategii Zaopatrzenia")
        c_raw1, c_raw2 = st.columns(2)
        with c_raw1: base_oil_ratio = st.slider("Udział oleju bazowego w recepturze [%]:", min_value=50, max_value=95, value=80, step=5) / 100.0
        with c_raw2: days_of_stock = st.number_input("Wymagany zapas bezpieczeństwa surowca [dni]:", min_value=5, max_value=60, value=14, step=1)
            
        st.markdown("---")
        st.markdown("### 📊 2. Bilans Zapotrzebowania na Oleje Bazowe")
        
        raw_material_summary = []
        total_annual_base_oil_kg = 0.0
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            v_annual_product_tony = mixer["annual_volume"] / 1000.0
            base_oil_annual_tony = v_annual_product_tony * base_oil_ratio
            base_oil_monthly_tony = (v_annual_product_tony / 12.0) * base_oil_ratio
            base_oil_monthly_m3 = (base_oil_monthly_tony * 1000.0) / (0.88 * 1000.0)
            total_annual_base_oil_kg += (base_oil_annual_tony * 1000.0)
            
            raw_material_summary.append({
                "ID Reaktora 🔒": mixer["tag"], "Rodzina Produktu 🔒": kat, "Produkcja [t/rok] 🔒": round(v_annual_product_tony, 1),
                "Baza [t/rok] 🔒": round(base_oil_annual_tony, 1), "Baza [t/mies] 🔒": round(base_oil_monthly_tony, 1), "Objętość Bazy [m³/mies] 🔒": round(base_oil_monthly_m3, 1)
            })
            
        st.dataframe(pd.DataFrame(raw_material_summary), hide_index=True, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🏢 3. Wymiarowanie Infrastruktury Magazynowej (Tank Farm)")
        
        total_annual_base_oil_tony = total_annual_base_oil_kg / 1000.0
        daily_base_oil_consumption_tony = total_annual_base_oil_tony / 250.0
        required_stock_m3 = (daily_base_oil_consumption_tony * days_of_stock) / 0.88
        
        c_tank1, c_tank2 = st.columns(2)
        with c_tank1: selected_tank_capacity_m3 = st.selectbox("Wybierz typową pojemność pojedynczego silosu [m³]:", [30, 50, 60, 80, 100, 150, 200], index=3)
        with c_tank2:
            needed_tanks_count = math.ceil(required_stock_m3 / (selected_tank_capacity_m3 * 0.85)) if required_stock_m3 > 0 else 0
            st.metric(label="🧱 Wymagana liczba silosów surowca", value=f"{needed_tanks_count} szt.", delta=f"Zapas na {days_of_stock} dni")
            
        st.markdown("<br>", unsafe_allow_html=True)
        raw_kpi1, raw_kpi2, raw_kpi3 = st.columns(3)
        with raw_kpi1: st.metric(label="📈 Zapotrzebowanie całkowite na bazę", value=f"{total_annual_base_oil_tony:,.1f} t/rok")
        with raw_kpi2: st.metric(label="🔀 Średnie zużycie dobowe", value=f"{daily_base_oil_consumption_tony:.1f} t/dzień")
        with raw_kpi3: st.metric(label="📐 Minimalna pojemność parku zbiorników", value=f"{required_stock_m3:,.1f} m³")
        
        st.warning(f"🚚 **Logistyka:** Wymaga to dostarczenia średnio **{((total_annual_base_oil_tony / 12.0) / 24.0):.1f} cystern (24t) na miesiąc**.")
