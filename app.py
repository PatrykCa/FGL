# ==========================================================================
# PATCH: Wskaźnik Obciążenia Ogniowego (Gęstość Obciążenia Ogniowego, Q [MJ/m²])
# ==========================================================================
# Ten plik NIE jest samodzielną aplikacją — to gotowe bloki kodu do wklejenia
# w trzech miejscach istniejącego app.py. Każdy blok ma komentarz mówiący
# DOKŁADNIE gdzie go wstawić (szukaj podanego fragmentu istniejącego kodu).
#
# Logika: Q = ΣQi / A, gdzie Qi = masa materiału palnego [kg] x jego ciepło
# spalania [MJ/kg], A = powierzchnia magazynowa wyrobów gotowych [m²]
# (ta sama, którą apka już liczy w Zakładce 3 -> "Podsumowanie Powierzchni
# Magazynowej"). Masa palna liczona jest automatycznie z zapasu magazynowego
# (ile sztuk danego opakowania danej linii aktualnie leży w magazynie, wg
# rotacji "Czas składowania palety"), rozbita na masę PRODUKTU (ciecz) i
# masę OPAKOWANIA (tara) — każda ze swoim własnym ciepłem spalania.
# ==========================================================================


# --------------------------------------------------------------------------
# BLOK 1 — nowe stałe/domyślne wartości.
# WSTAW: zaraz pod definicją GROUP_PHYSICAL_DEFAULTS (przed GENERIC_PORTFOLIO).
# --------------------------------------------------------------------------

# Domyślne ciepło spalania PRODUKTU (samej cieczy) per grupa produktowa [MJ/kg].
# Wartości orientacyjne: oleje mineralne/syntetyczne ok. 42-44 MJ/kg (typowe dla
# węglowodorów), smary podobnie (baza olejowa), produkty wodne/emulsje znacznie
# niżej (woda nie jest palna, obniża średnią kaloryczność mieszaniny).
# W pełni edytowalne w aplikacji (Zakładka 4 -> nowa sekcja), to tylko starter.
FIRE_LOAD_PRODUCT_CALORIFIC_MJKG = {
    "Cleaners": 5.0,
    "Engine Oils": 42.0,
    "Glycols": 20.0,
    "Greases": 40.0,
    "Hydraulic Oils": 42.0,
    "Watermiscibles": 10.0,
    "Waxes": 42.0,
}

# Progi orientacyjne kategorii gęstości obciążenia ogniowego stref PM — powszechnie
# stosowane w polskiej praktyce projektowej jako pierwsze przybliżenie (nie zastępuje
# właściwej klasyfikacji wg PN-B-02852 / ekspertyzy rzeczoznawcy ppoż.).
FIRE_LOAD_Q_BRACKETS = [
    (500.0, "Mała (Q ≤ 500 MJ/m²)", "🟢"),
    (1000.0, "Średnia (500-1000 MJ/m²)", "🟡"),
    (2000.0, "Duża (1000-2000 MJ/m²)", "🟠"),
    (float("inf"), "Bardzo duża (> 2000 MJ/m²)", "🔴"),
]


def classify_fire_load(q_density_mjm2):
    """Zwraca (etykieta, emoji) dla podanej gęstości obciążenia ogniowego [MJ/m²]."""
    for prog, label, emoji in FIRE_LOAD_Q_BRACKETS:
        if q_density_mjm2 <= prog:
            return label, emoji
    return FIRE_LOAD_Q_BRACKETS[-1][1], FIRE_LOAD_Q_BRACKETS[-1][2]


def default_packaging_fire_props(pack_name, size_l):
    """
    Zgaduje domyślny materiał / masę własną (tarę) / ciepło spalania OPAKOWANIA
    na podstawie nazwy i pojemności — użytkownik i tak może to nadpisać w apce.
    Wartości orientacyjne: HDPE ok. 46 MJ/kg, tektura ok. 17 MJ/kg, stal 0 MJ/kg
    (niepalna, ale nadal wliczana jako masa - z zerowym ciepłem spalania po
    prostu nie dokłada energii do bilansu).
    """
    n = pack_name.lower()
    if "1000" in n or "ibc" in n:
        return {"material": "IBC: HDPE + rama stalowa", "tara_kg": 55.0, "calorific": 30.0}
    if "200" in n or ("beczka" in n and size_l >= 100):
        return {"material": "Beczka stalowa", "tara_kg": 22.0, "calorific": 0.0}
    if "60" in n:
        return {"material": "Beczka HDPE", "tara_kg": 3.0, "calorific": 46.0}
    if "20" in n:
        return {"material": "Kanister HDPE", "tara_kg": 0.9, "calorific": 46.0}
    if "10" in n:
        return {"material": "Kanister HDPE", "tara_kg": 0.5, "calorific": 46.0}
    if "karton" in n or "4" in n or "5" in n:
        return {"material": "Tektura + wkład HDPE", "tara_kg": 0.25, "calorific": 20.0}
    if "1l" in n or n.strip().startswith("1 "):
        return {"material": "Butelka HDPE", "tara_kg": 0.05, "calorific": 46.0}
    return {"material": "Nieokreślony", "tara_kg": 0.5, "calorific": 20.0}


# --------------------------------------------------------------------------
# BLOK 2 — zapamiętanie pojemności/gęstości przy budowaniu real_split_rows,
# żeby dało się z nich policzyć masę zapasu bez powtarzania kodu.
# WSTAW: w Zakładce 3 (tab3), wewnątrz pętli "for m in mixers_fleet:",
# ZNAJDŹ blok kończący się na:
#
#     real_split_rows.append({
#         "Reaktor 🔒": m["tag"], "Linia 🔒": kat, "Opakowanie 📦": p, "Udział": f"{udzial_pct:.1f}%",
#         "Źródło %": split_source,
#         "Opakowań [/mies]": int(liczba_sztuk_month), "Palet [/mies] 🧱": int(liczba_palet_month),
#         "Miejsca magazynowe [szt] 📐": int(miejsca_paletowe), "Czas rozlewu strumienia [h] ⏱️": round(czas_rozlewu_h, 1),
#         "Wąskie gardło": "Pompa" if q_pump_m3h < sekcja_nalewania_m3_h else "Sekcja nalewania"
#     })
#
# I DODAJ do tego słownika dwa ukryte klucze (nie zmieniaj reszty):
# --------------------------------------------------------------------------
#
#     "_pack_capacity_kg": pack_capacity_kg,
#     "_rho_linii": rho_linii,


# --------------------------------------------------------------------------
# BLOK 2b — ukryj te dwa klucze przy wyświetlaniu istniejącej tabeli.
# ZNAJDŹ (kilka linii niżej, dalej w tab3):
#
#     st.dataframe(pd.DataFrame(real_split_rows), hide_index=True, use_container_width=True)
#
# ZAMIEŃ NA:
# --------------------------------------------------------------------------
#
#     _df_logistics_display = pd.DataFrame(real_split_rows)
#     _cols_to_show = [c for c in _df_logistics_display.columns if not c.startswith("_")]
#     st.dataframe(_df_logistics_display[_cols_to_show], hide_index=True, use_container_width=True)


# --------------------------------------------------------------------------
# BLOK 3 — sama sekcja Obciążenia Ogniowego.
# WSTAW: w Zakładce 3 (tab3), zaraz PO istniejącym bloku:
#
#     m_wh1, m_wh2, m_wh3 = st.columns(3)
#     with m_wh1: st.metric("📦 Łączna liczba miejsc paletowych", f"{total_miejsca_magazynowe:,} szt.")
#     with m_wh2: st.metric("📐 Wymagana powierzchnia magazynowa", f"{total_powierzchnia_m2:,.0f} m²")
#     with m_wh3: st.metric("📏 Powierzchnia / miejsce paletowe", f"{powierzchnia_na_miejsce:.2f} m²")
#
#     st.caption("💡 Powyższa suma to zapotrzebowanie na miejsca paletowe **wyrobów gotowych** ...")
#
# (czyli zaraz przed "else:" / "st.info(... brak skonfigurowanego podziału ...)")
# --------------------------------------------------------------------------

FIRE_LOAD_SECTION = r'''
            st.markdown("---")
            st.markdown("##### 🔥 Wskaźnik Obciążenia Ogniowego (Gęstość Obciążenia Ogniowego Q)")
            st.caption("Q = ΣQi / A, gdzie Qi = masa materiału palnego w zapasie magazynowym [kg] x jego ciepło spalania "
                       "[MJ/kg], a A = powierzchnia magazynowa wyliczona powyżej. Masa produktu i opakowań w zapasie "
                       "liczona jest automatycznie z bieżącej rotacji ('Czas składowania palety'). To orientacyjne "
                       "obliczenie inżynierskie do wstępnej oceny - ostateczna klasyfikacja strefy pożarowej wg "
                       "PN-B-02852 wymaga weryfikacji przez rzeczoznawcę ds. zabezpieczeń przeciwpożarowych.")

            fire_load_product = st.session_state.setdefault("fire_load_product_calorific", {})
            for kat_fl in wybrane_kategorie:
                fire_load_product.setdefault(kat_fl, FIRE_LOAD_PRODUCT_CALORIFIC_MJKG.get(kat_fl, 30.0))
            with st.expander("⚙️ Ciepło spalania produktu (per linia) i opakowań (per typ) — edytowalne", expanded=False):
                st.markdown("**Ciepło spalania produktu wg linii produktowej**")
                df_fp = pd.DataFrame([
                    {"Linia": k, "Ciepło spalania produktu [MJ/kg]": v}
                    for k, v in fire_load_product.items() if k in wybrane_kategorie
                ])
                edited_fp = st.data_editor(df_fp, hide_index=True, use_container_width=True,
                                            disabled=["Linia"], key="fire_load_product_editor")
                for _, r in edited_fp.iterrows():
                    fire_load_product[r["Linia"]] = float(r["Ciepło spalania produktu [MJ/kg]"])

                st.markdown("**Materiał, masa własna (tara) i ciepło spalania opakowań**")
                fire_load_pack = st.session_state.setdefault("fire_load_pack_props", {})
                for p_fl, cfg_fl in st.session_state.pack_configs.items():
                    if p_fl not in fire_load_pack:
                        fire_load_pack[p_fl] = default_packaging_fire_props(p_fl, cfg_fl.get("size_l", 0))
                df_fpack = pd.DataFrame([
                    {"Opakowanie": p_fl, "Materiał": fire_load_pack[p_fl]["material"],
                     "Masa własna (tara) [kg]": fire_load_pack[p_fl]["tara_kg"],
                     "Ciepło spalania opakowania [MJ/kg]": fire_load_pack[p_fl]["calorific"]}
                    for p_fl in st.session_state.pack_configs.keys()
                ])
                edited_fpack = st.data_editor(df_fpack, hide_index=True, use_container_width=True,
                                               disabled=["Opakowanie"], key="fire_load_pack_editor")
                for _, r in edited_fpack.iterrows():
                    fire_load_pack[r["Opakowanie"]] = {
                        "material": r["Materiał"],
                        "tara_kg": float(r["Masa własna (tara) [kg]"]),
                        "calorific": float(r["Ciepło spalania opakowania [MJ/kg]"]),
                    }

            fire_rows = []
            total_q_mj = 0.0
            for r_fl in real_split_rows:
                kat_fl = r_fl["Linia 🔒"]
                pack_fl = r_fl["Opakowanie 📦"]
                units_month = r_fl["Opakowań [/mies]"]
                units_in_stock = (units_month / dni_robocze_miesiac) * czas_skladowania_dni if dni_robocze_miesiac > 0 else 0.0
                pack_capacity_kg_fl = r_fl.get("_pack_capacity_kg", 0.0)
                product_mass_kg = units_in_stock * pack_capacity_kg_fl
                pack_props = fire_load_pack.get(pack_fl, {"tara_kg": 0.0, "calorific": 0.0})
                packaging_mass_kg = units_in_stock * pack_props["tara_kg"]
                h_product = fire_load_product.get(kat_fl, 30.0)
                h_pack = pack_props["calorific"]
                q_row_mj = (product_mass_kg * h_product) + (packaging_mass_kg * h_pack)
                total_q_mj += q_row_mj
                fire_rows.append({
                    "Linia": kat_fl, "Opakowanie": pack_fl, "Zapas [szt]": int(units_in_stock),
                    "Masa produktu w zapasie [kg]": round(product_mass_kg, 1),
                    "Masa opakowań w zapasie [kg]": round(packaging_mass_kg, 1),
                    "Energia [MJ]": round(q_row_mj, 1),
                })

            st.markdown("**➕ Dodatkowe materiały palne w magazynie (opcjonalnie: palety, folia, regały palne...)**")
            if "fire_load_extra_items" not in st.session_state:
                st.session_state.fire_load_extra_items = pd.DataFrame([
                    {"Materiał": "Palety drewniane (przykład)", "Masa [kg]": 2000.0, "Ciepło spalania [MJ/kg]": 17.0},
                ])
            edited_extra = st.data_editor(
                st.session_state.fire_load_extra_items, hide_index=True, use_container_width=True,
                num_rows="dynamic", key="fire_load_extra_editor"
            )
            st.session_state.fire_load_extra_items = edited_extra
            extra_q_mj = 0.0
            if not edited_extra.empty:
                masy = pd.to_numeric(edited_extra["Masa [kg]"], errors="coerce").fillna(0.0)
                ciepla = pd.to_numeric(edited_extra["Ciepło spalania [MJ/kg]"], errors="coerce").fillna(0.0)
                extra_q_mj = float((masy * ciepla).sum())

            total_q_mj_all = total_q_mj + extra_q_mj

            if fire_rows or extra_q_mj > 0:
                st.markdown("**Rozbicie energii pożarowej wg linii/opakowania (zapas wyrobów gotowych)**")
                if fire_rows:
                    st.dataframe(pd.DataFrame(fire_rows), hide_index=True, use_container_width=True)

                q_density = total_q_mj_all / total_powierzchnia_m2 if total_powierzchnia_m2 > 0 else 0.0
                klasa_txt, klasa_emoji = classify_fire_load(q_density)

                m_q1, m_q2, m_q3 = st.columns(3)
                with m_q1:
                    st.metric("🔥 Sumaryczna energia pożarowa", f"{total_q_mj_all:,.0f} MJ")
                with m_q2:
                    st.metric("📐 Powierzchnia magazynowa", f"{total_powierzchnia_m2:,.0f} m²")
                with m_q3:
                    st.metric("Q — Gęstość obciążenia ogniowego", f"{q_density:,.1f} MJ/m²")
                st.markdown(f"**Orientacyjna kategoria:** {klasa_emoji} {klasa_txt}")
                st.caption("Progi orientacyjne wg powszechnej praktyki wstępnej klasyfikacji stref pożarowych PM w Polsce "
                           "— traktuj jako szacunek pomocniczy, nie substytut właściwej ekspertyzy ppoż. wg PN-B-02852.")
            else:
                st.info("Brak danych do wyliczenia obciążenia ogniowego — skonfiguruj podział opakowań powyżej lub "
                        "dodaj pozycję ręcznie w tabeli 'Dodatkowe materiały palne'.")
'''

print("Ten plik to wyłącznie dokumentacja patcha — patrz komentarze BLOK 1/2/2b/3 powyżej "
      "oraz zmienna FIRE_LOAD_SECTION zawierająca gotowy kod Streamlit do wklejenia.")
