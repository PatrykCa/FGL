import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Dynamiczne Wymiarowanie Linii na Bazie Optymalizacji Stopnia Utylizacji Węzła")
st.markdown("---")

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Hydraulic Oils (RENOLIN)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "visc_kin": 46.0, "flash_point": "220°C", "frost_sensitivity": "Nie"
    },
    "Gear & Turbine Oils (RENOLIN)": {
        "material": "Stal zwykła", "density": 0.89, "cycle_h": 5, "cp": 1.9, 
        "visc_kin": 220.0, "flash_point": "240°C", "frost_sensitivity": "Nie"
    },
    "Slideway & Machine Oils (RENAX)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "210°C", "visc_kin": 68.0, "frost_sensitivity": "Nie"
    },
    "Engine Oils (TITAN)": {
        "material": "Stal zwykła", "density": 0.87, "cycle_h": 5, "cp": 2.1, 
        "visc_kin": 95.0, "flash_point": "230°C", "frost_sensitivity": "Nie"
    },
    "Gear & Transmission Oils (TITAN)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 5, "cp": 2.0, 
        "visc_kin": 140.0, "flash_point": "210°C", "frost_sensitivity": "Nie"
    },
    "Water-miscible (ECOCOOL)": {
        "material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8, 
        "visc_kin": 60.0, "flash_point": "Brak", "frost_sensitivity": "TAK"
    },
    "Non-water-miscible (ECOCUT)": {
        "material": "Stal zwykła", "density": 0.87, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "190°C", "visc_kin": 22.0, "frost_sensitivity": "Nie"
    },
    "Cleaners (RENOCLEAN)": {
        "material": "Stal nierdzewna", "density": 1.01, "cycle_h": 4, "cp": 3.9, 
        "visc_kin": 5.0, "flash_point": "Brak", "frost_sensitivity": "TAK"
    }
}

PACK_CONFIGS = {
    "1l (Detal)": {"size_l": 1.0, "per_pallet": 480},
    "4l (Karton)": {"size_l": 4.0, "per_pallet": 120},
    "5l (Karton)": {"size_l": 5.0, "per_pallet": 96},
    "10l (Kanister)": {"size_l": 10.0, "per_pallet": 40},
    "20l (Kanister)": {"size_l": 20.0, "per_pallet": 24},
    "60l (Beczka)": {"size_l": 60.0, "per_pallet": 9},
    "200l (Beczka)": {"size_l": 200.0, "per_pallet": 4},
    "1000l (IBC)": {"size_l": 1000.0, "per_pallet": 1}
}

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h/miesiąc (nominalny czas pracy na 2 zmiany)

# --- PANEL BOCZNY (TYLKO WYBÓR I REFRESH) ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne linie produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Hydraulic Oils (RENOLIN)", "Engine Oils (TITAN)", "Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Dystrybucja Opakowań")
input_packs = {}
for kat in wybrane_kategorie:
    packs = st.sidebar.multiselect(
        f"Opakowania dla {kat}:",
        list(PACK_CONFIGS.keys()),
        default=["200l (Beczka)", "1000l (IBC)"],
        key=f"packs_{kat}"
    )
    input_packs[kat] = packs

if "master_df" not in st.session_state:
    st.session_state.master_df = pd.DataFrame()

# --- PODZIAŁ NA TRZY ZAKŁADKI ---
tab1, tab2, tab3 = st.tabs([
    "📊 1. Główne Zestawienie i Symulacja Utylizacji", 
    "📐 2. Karta Techniczna Maszyn i Hydrodynamika", 
    "📦 3. Magazyn Wyrobów Gotowych i Palety"
])

# ==========================================
# ZAKŁADKA 1: JEDNA, JEDYNA TABELA ZBIORCZA
# ==========================================
with tab1:
    st.header("Zestawienie parametrów procesowych i optymalizacji obłożenia")
    
    if wybrane_kategorie:
        # Inicjalizacja lub resetowanie danych po kliknięciu przycisku w sidebarze
        if st.sidebar.button("🔄 Generuj / Resetuj tabele z bazy handlowej") or st.session_state.master_df.empty or len(st.session_state.master_df) != len(wybrane_kategorie):
            raw_rows = []
            for kat in wybrane_kategorie:
                # Domyślne wartości startowe rekomendowane przez system
                m_annual = 1200000
                m_monthly = m_annual / 12
                util_init = 75.0
                
                dens = FUCHS_PORTFOLIO[kat]["density"]
                cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
                
                allocated_hours = AVAILABLE_HOURS_MONTH * (util_init / 100.0)
                needed_batches = math.ceil(allocated_hours / cyc) if allocated_hours > 0 else 1
                batch_size_kg = math.ceil(m_monthly / needed_batches) if needed_batches > 0 else 0
                calculated_vol_m3 = batch_size_kg / (dens * 1000.0) if batch_size_kg > 0 else 0.0
                
                raw_rows.append({
                    "1. Nazwa rodziny": kat,
                    "2. Roczna produkcja [kg]": int(m_annual),
                    "3. Utilization %": float(util_init),
                    "4. Liczba szarż na miesiąc [całkowita]": int(needed_batches),
                    "5. Pojemność mieszalnika [m³]": f"{calculated_vol_m3:.1f} m³",
                    "6. Wielkość pojedynczej szarży [kg]": int(batch_size_kg)
                })
            st.session_state.master_df = pd.DataFrame(raw_rows)
            
        st.markdown("💡 *Kolumny **2. Roczna produkcja [kg]** oraz **3. Utilization %** są edytowalne bezpośrednio w komórkach tabeli. Zmiana wartości automatycznie przeliczy parametry szarży i miksera.*")
        
        # INTERAKTYWNA FUNKCJA REAGUJĄCA NA EDYCJĘ TABELI
        def handle_live_recalculation():
            changes = st.session_state["live_editor"]["edited_rows"]
            current_df = st.session_state.master_df
            
            for row_idx, changed_cols in changes.items():
                kat = current_df.loc[row_idx, "1. Nazwa rodziny"]
                dens = FUCHS_PORTFOLIO[kat]["density"]
                cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
                
                # Pobranie wartości (obecnych lub nowo wpisanych)
                m_annual = changed_cols.get("2. Roczna produkcja [kg]", current_df.loc[row_idx, "2. Roczna produkcja [kg]"])
                util_val = changed_cols.get("3. Utilization %", current_df.loc[row_idx, "3. Utilization %"])
                
                m_monthly = m_annual / 12
                util_fraction = util_val / 100.0
                allocated_hours = AVAILABLE_HOURS_MONTH * util_fraction
                
                needed_batches = math.ceil(allocated_hours / cyc) if allocated_hours > 0 else 1
                batch_size_kg = math.ceil(m_monthly / needed_batches) if needed_batches > 0 else 0
                calculated_vol_m3 = batch_size_kg / (dens * 1000.0) if batch_size_kg > 0 else 0.0
                
                # Aktualizacja struktur danych w wierszu tabeli
                current_df.loc[row_idx, "2. Roczna produkcja [kg]"] = int(m_annual)
                current_df.loc[row_idx, "3. Utilization %"] = float(util_val)
                current_df.loc[row_idx, "4. Liczba szarż na miesiąc [całkowita]"] = int(needed_batches)
                current_df.loc[row_idx, "5. Pojemność mieszalnika [m³]"] = f"{calculated_vol_m3:.1f} m³"
                current_df.loc[row_idx, "6. Wielkość pojedynczej szarży [kg]"] = int(batch_size_kg)
                
            st.session_state.master_df = current_df

        # JEDYNA, WYŚWIETLANA TABELA PROCESOWA
        edited_output = st.data_editor(
            st.session_state.master_df,
            key="live_editor",
            hide_index=True,
            use_container_width=True,
            on_change=handle_live_recalculation,
            disabled=
