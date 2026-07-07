import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Kreator Linii FUCHS Portfolio", layout="wide")

st.title("🏭 Kompleksowy Kreator Produkcyjny FUCHS Oil")
st.subheader("Zarządzanie Wolumenami i Gabarytami Aparatury (Forma Tabeli Zbiorczej)")
st.markdown("---")

# --- 1. BAZA DANYCH RODZIN PRODUKTOWYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Industrial: Hydraulic Oils (RENOLIN)": {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "cp": 2.0, "flash": "220°C", "visc": "46 mm²/s", "frost": "Nie", "pdf": "PID_Olejowy.pdf"},
    "Industrial: Gear & Turbine Oils (RENOLIN)": {"material": "Stal węglowa (Carbon Steel)", "density": 0.89, "cycle_h": 5, "cp": 1.9, "flash": "240°C", "visc": "220 mm²/s", "frost": "Nie", "pdf": "PID_Olejowy.pdf"},
    "Industrial: Slideway & Machine Oils (RENAX)": {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "cp": 2.0, "flash": "210°C", "visc": "68 mm²/s", "frost": "Nie", "pdf": "PID_Olejowy.pdf"},
    "Automotive: Engine Oils (TITAN)": {"material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 5, "cp": 2.1, "flash": "230°C", "visc": "11.5 mm²/s", "frost": "Nie", "pdf": "PID_Olejowy.pdf"},
    "Automotive: Gear & Transmission Oils (TITAN)": {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 5, "cp": 2.0, "flash": "210°C", "visc": "14.0 mm²/s", "frost": "Nie", "pdf": "PID_Olejowy.pdf"},
    "Metal Processing: Water-miscible (ECOCOOL)": {"material": "Stal nierdzewna (SS316L)", "density": 0.99, "cycle_h": 6, "cp": 3.8, "flash": "Brak", "visc": "60 mm²/s", "frost": "TAK", "pdf": "PID_Wodny.pdf"},
    "Metal Processing: Non-water-miscible (ECOCUT)": {"material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 4, "cp": 2.0, "flash": "190°C", "visc": "22 mm²/s", "frost": "Nie", "pdf": "PID_Olejowy.pdf"},
    "Metal Processing: Cleaners (RENOCLEAN)": {"material": "Stal nierdzewna (SS304/316L)", "density": 1.01, "cycle_h": 4, "cp": 3.9, "flash": "Brak", "visc": "5 mm²/s", "frost": "TAK", "pdf": "PID_Wodny.pdf"}
}

PACK_SIZES = {
    "1l (Detal)": 1.0, "4l (Karton)": 4.0, "5l (Karton)": 5.0, 
    "10l (Kanister)": 10.0, "20l (Kanister)": 20.0, 
    "60l (Beczka)": 60.0, "200l (Beczka)": 200.0, "1000l (IBC)": 1000.0
}

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h/miesiąc

# --- PANEL BOCZNY ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin FUCHS")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Dane wejściowe")
input_data = {}
for kat in wybrane_kategorie:
    st.sidebar.markdown(f"### 🧪 {kat}")
    vol = st.sidebar.number_input(f"Roczna produkcja [kg]:", min_value=0, value=1200000, step=100000, key=f"vol_{kat}")
    packs = st.sidebar.multiselect(
        "Opakowania końcowe (FL):",
        list(PACK_SIZES.keys()) + ["Bulk (Cysterna luz)"],
        default=["200l (Beczka)", "1000l (IBC)"],
        key=f"packs_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "opakowania": packs}

# Inicjalizacja tabeli w pamięci Session State przy starcie aplikacji lub resecie
if "df_table" not in st.session_state or st.sidebar.button("🔄 Odśwież tabelę z nowymi surowcami"):
    rows = []
    for kat in wybrane_kategorie:
        if input_data[kat]["wolumen"] > 0:
            m_prod = input_data[kat]["wolumen"] / 12
            d = FUCHS_PORTFOLIO[kat]["density"]
            c = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            # 75% Utylizacji bazowej (System)
            sys_s = round((AVAILABLE_HOURS_MONTH * 0.75) / c, 1)
            sys_v = (m_prod / sys_s) / (d * 1000)
            sys_v = max(0.5, math.ceil(sys_v * 2) / 2)
            
            rows.append({
                "Produkt": kat.split(":")[-1].strip(),
                "Klucz_ID": kat,
                "1. Miesięczna produkcja [kg]": int(m_prod),
                "2. Rekomendowana Pojemność MT [m³]": float(sys_v),
                "3. Szarże / miesiąc (Rekomendacja)": float(sys_s),
                "4. Obłożenie % (Rekomendacja)": 75.0,
                "5. Pojemność użytkownika [m³]": float(sys_v),
                "6. Szarże / miesiąc użytkownika": float(sys_s),
                "7. Obłożenie % użytkownika": 75.0,
                "Wariant do projektu": "Rekomendowany"
            })
    st.session_state.df_table = pd.DataFrame(rows)

if "confirmed_setup" not in st.session_state:
    st.session_state.confirmed_setup = {}

tab1, tab2 = st.tabs(["📊 1. Logistyka Szarż i Zbiorniki", "📐 2. Specyfikacja Ciągu Technologicznego (P&ID)"])

with tab1:
    st.header("Zestawienie Wolumenów i Parametrów Szarż")
    st.caption("Wszystkie wybrane linie zebrane w jedną tabelę. Zmień dowolną wartość w kolumnach użytkownika (5, 6, 7), aby automatycznie przeliczyć wiersz.")
    
    if not st.session_state.df_table.empty:
        
        # CENTRALNY SILNIK PRZELICZANIA DWUKIERUNKOWEGO DLA DATA_EDITOR
        def recalculate_table_rows():
            changes = st.session_state["main_editor"]["edited_rows"]
            current_df = st.session_state.df_table
            
            for row_idx, changed_cols in changes.items():
                kat_id = current_df.loc[row_idx, "Klucz_ID"]
                m_prod = current_df.loc[row_idx, "1. Miesięczna produkcja [kg]"]
                d = FUCHS_PORTFOLIO[kat_id]["density"]
                c = FUCHS_PORTFOLIO[kat_id]["cycle_h"]
                
                v_curr = current_df.loc[row_idx, "5. Pojemność użytkownika [m³]"]
                s_curr = current_df.loc[row_idx, "6. Szarże / miesiąc użytkownika"]
                u_curr = current_df.loc[row_idx, "7. Obłożenie % użytkownika"]
                
                # Sprawdzamy która komórka została kliknięta/zmieniona
                if "5. Pojemność użytkownika [m³]" in changed_cols:
                    v_curr = changed_cols["5. Pojemność użytkownika [m³]"]
                    if v_curr > 0:
                        s_curr = round(m_prod / (v_curr * d * 1000), 1)
                        u_curr = round((s_curr * c / AVAILABLE_HOURS_MONTH) * 100, 1)
                elif "6. Szarże / miesiąc użytkownika" in changed_cols:
                    s_curr = changed_cols["6. Szarże / miesiąc użytkownika"]
                    if s_curr > 0:
                        v_curr = round(max(0.5, math.ceil((m_prod / (s_curr * d * 1000)) * 2) / 2), 1)
                        u_curr = round((s_curr * c / AVAILABLE_HOURS_MONTH) * 100, 1)
                elif "7. Obłożenie % użytkownika" in changed_cols:
                    u_curr = changed_cols["7. Obłożenie % użytkownika"]
                    s_curr = round(((u_curr / 100) * AVAILABLE_HOURS_MONTH) / c, 1)
                    if s_curr > 0:
                        v_curr = round(max(0.5, math.ceil((m_prod / (s_curr * d * 1000)) * 2) / 2), 1)
                
                # Zapisujemy komplet wyników z powrotem do wiersza tabeli
                current_df.loc[row_idx, "5. Pojemność użytkownika [m³]"] = float(v_curr)
                current_df.loc[row_idx, "6. Szarże / miesiąc użytkownika"] = float(s_curr)
                current_df.loc[row_idx, "7. Obłożenie % użytkownika"] = float(u_curr)
                
                if "Wariant do projektu" in changed_cols:
                    current_df.loc[row_idx, "Wariant do projektu"] = changed_cols["Wariant do projektu"]
                    
            st.session_state.df_table = current_df

        # WYŚWIETLENIE ZBIORCZEJ TABELI
        edited_output = st.data_editor(
            st.session_state.df_table,
            key="main_editor",
            on_change=recalculate_table_rows,
            disabled=["Produkt", "Klucz_ID", "1. Miesięczna produkcja [kg]", "2. Rekomendowana Pojemność MT [m³]", "3. Szarże / miesiąc (Rekomendacja)", "4. Obłożenie % (Rekomendacja)"],
            column_config={
                "Klucz_ID": None,  # ukryta kolumna techniczna
                "1. Miesięczna produkcja [kg]": st.column_config.NumberColumn(format="%d kg"),
                "Wariant do projektu": st.column_config.SelectboxColumn("Wybrana Opcja", options=["Rekomendowany", "Użytkownika"])
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Przycisk wysyłający całą tabelę naraz
        st.markdown("---")
        if st.button("🔒 ZATWIERDŹ I WYŚLIJ CAŁĄ TABELĘ DO DRUGIEJ ZAKŁADKI"):
            temp_confirmed = {}
            for idx, r in edited_output.iterrows():
                k_key = r["Klucz_ID"]
                if r["Wariant do projektu"] == "Rekomendowany":
                    temp_confirmed[k_key] = {
                        "capacity": r["2. Rekomendowana Pojemność MT [m³]"], "batches": r["3. Szarże / miesiąc (Rekomendacja)"], "utilization": r["4. Obłożenie % (Rekomendacja)"], "opakowania": input_data[k_key]["opakowania"]
                    }
                else:
                    temp_confirmed[k_key] = {
                        "capacity": r["5. Pojemność użytkownika [m³]"], "batches": r["6. Szarże / miesiąc użytkownika"], "utilization": r["7. Obłożenie % użytkownika"], "opakowania": input_data[k_key]["opakowania"]
                    }
            st.session_state.confirmed_setup = temp_confirmed
            st.success("✔️ Pomyślnie zamrożono i wygenerowano listę maszyn w Zakładce 2!")

        # --- SEKCJA OPAKOWAŃ POD TABELĄ ---
        st.markdown("### 📦 Zapotrzebowanie na opakowania (Miesięcznie dla aktywnych linii)")
        for idx, r in edited_output.iterrows():
            k_key = r["Klucz_ID"]
            chosen_packs = input_data[k_key]["opakowania"]
            if chosen_packs:
                st.markdown(f"**Dla produktu: {r['Produkt']}**")
                num_types = len(chosen_packs)
                mass_per_type_l = (r["1. Miesięczna produkcja [kg]"] / FUCHS_PORTFOLIO[k_key]["density"]) / num_types
                
                cols = st.columns(num_types)
                for p_idx, p_name in enumerate(chosen_packs):
                    with cols[p_idx]:
                        if p_name in PACK_SIZES:
                            size_l = PACK_SIZES[p_name]
                            total_szt = math.ceil(mass_per_type_l / size_l)
                            st.metric(label=p_name, value=f"{total_szt:,} szt.")
                        else:
                            total_trucks = round((r["1. Miesięczna produkcja [kg]"] / num_types) / 24000, 1)
                            st.metric(label="Luz (Bulk)", value=f"{total_trucks} cystern")
    else:
        st.info("Wybierz rodziny produktowe w panelu bocznym.")

with tab2:
    st.header("📐 Inżynieryjna Specyfikacja Ciągu Technologicznego")
    
    if not st.session_state.confirmed_setup:
        st.info("ℹ️ Zatwierdź tabelę zbiorczą w Zakładce 1 za pomocą przycisku '🔒 Zatwierdź i wyślij całą tabelę'.")
    else:
        rows = []
        idx = 101
        for kat, dane in st.session_state.confirmed_setup.items():
            rules = FUCHS_PORTFOLIO[kat]
            v_final = dane["capacity"]
            
            rows.append({
                "Tag Mieszalnika": f"MT-{idx}",
                "Rodzina Produktowa": kat.split(":")[-1].strip(),
                "Pojemność [m³]": f"{v_final:.1f} m³",
                "Szarże / miesiąc": dane["batches"],
                "Obłożenie (%)": f"{dane['utilization']:.1f}%",
                "Materiał (Stal)": rules["material"],
                "Flash Point": rules["flash"],
                "Viscosity": rules["visc"],
                "Frost Sensitivity": rules["frost"],
                "Masa Szarży [kg]": v_final * rules["density"] * 1000,
                "cp": rules["cp"]
            })
            idx += 1
            
        df_ins = pd.DataFrame(rows)
        
        st.markdown("#### 🌡️ Parametry Procesowe i Bilans Cieplny")
        final_table_data = []
        for index, row in df_ins.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 3, 3])
                with c1:
                    st.markdown(f"**{row['Tag Mieszalnika']}**<br><small>{row['Rodzina Produktowa']}</small>", unsafe_allowed_html=True)
                with c2:
                    dt_heat = st.number_input(f"ΔT grzania [°C] ({row['Tag Mieszalnika']}):", value=40, step=5, key=f"dth_{row['Tag Mieszalnika']}")
                    total_heat_gj = (row["Masa Szarży [kg]"] * row["cp"] * dt_heat * row["Szarże / miesiąc"]) / (1_000_000 * 0.85)
                with c3:
                    dt_cool = st.number_input(f"ΔT chłodzenia [°C] ({row['Tag Mieszalnika']}):", value=30, step=5, key=f"dtc_{row['Tag Mieszalnika']}")
                    total_cool_gj = (row["Masa Szarży [kg]"] * row["cp"] * dt_cool * row["Szarże / miesiąc"]) / (1_000_000 * 0.85)
                
                final_table_data.append({
                    "Tag": row["Tag Mieszalnika"],
                    "Produkt": row["Rodzina Produktowa"],
                    "Pojemność": row["Pojemność [m³]"],
                    "Stal": row["Materiał (Stal)"],
                    "Ciepło grzania [GJ/m]": f"{total_heat_gj:.2f} GJ",
                    "Ciepło chłodzenia [GJ/m]": f"{total_cool_gj:.2f} GJ",
                    "Flash Point": row["Flash Point"],
                    "Lepkość": row["Viscosity"],
                    "Wrażliwość na mróz": row["Frost Sensitivity"]
                })
        
        st.markdown("---")
        st.markdown("### 📋 Zbiorcza Tabela Technologiczna")
        st.table(pd.DataFrame(final_table_data))
