import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import re
import pandas as pd

st.set_page_config(page_title="E-ZAK Karlovarský kraj", layout="wide")
st.title("🛡️ E-ZAK Karlovarský kraj")
st.markdown("**Aktivní zakázky všech zadavatelů v Karlovarském kraji**")

base_index = "https://ezak.kr-karlovarsky.cz/profile_index.html"

# Načtení všech zadavatelů z 5 stránek
@st.cache_data(ttl=3600)
def load_all_profiles():
    all_profiles = []
    for page in range(1, 6):
        url = f"{base_index}?page={page}"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            
            for a in soup.find_all("a", href=re.compile(r"profile_display_\d+")):
                name = a.text.strip()
                if name and len(name) > 3:
                    profile_url = urljoin(base_index, a["href"])
                    all_profiles.append({"Název zadavatele": name, "URL": profile_url})
        except:
            continue
    return pd.DataFrame(all_profiles)

# Zobrazení tabulky
st.subheader("📋 Seznam všech zadavatelů v Karlovarském kraji")
df_profiles = load_all_profiles()
st.dataframe(df_profiles, use_container_width=True, hide_index=True)

st.caption(f"Celkem nalezeno {len(df_profiles)} zadavatelů")

if st.button("🔄 Načíst aktivní zakázky ze všech zadavatelů", type="primary"):
    now = datetime.now()
    total_active = 0

    with st.spinner("Prohledávám všechny zadavatele v kraji..."):
        progress_bar = st.progress(0)

        for idx, row in df_profiles.iterrows():
            profile_name = row["Název zadavatele"]
            profile_url = row["URL"]
            
            progress_bar.progress((idx + 1) / len(df_profiles))

            try:
                # Filtr na aktivní zakázky
                url = profile_url
                if "?" not in url:
                    url += "?state=active&archive=ACTUAL"
                else:
                    url += "&state=active&archive=ACTUAL"

                response = requests.get(url, timeout=12)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                contract_links = soup.find_all("a", href=re.compile(r"contract_display_"))

                active = []
                for a in contract_links:
                    name = a.text.strip()
                    if not name or len(name) < 8: 
                        continue
                    link = urljoin(url, a["href"])

                    tr = a.find_parent("tr")
                    if not tr: 
                        continue
                    tds = tr.find_all("td")
                    if len(tds) < 5: 
                        continue

                    deadline_str = tds[-1].text.strip().replace("\xa0", " ")

                    if not deadline_str or deadline_str in ["-", ""]:
                        continue

                    try:
                        if ":" in deadline_str:
                            dl = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
                        else:
                            dl = datetime.strptime(deadline_str, "%d.%m.%Y")
                        if dl > now:
                            active.append(f"[{name}]({link}) — lhůta {deadline_str}")
                    except:
                        continue

                if active:
                    st.markdown(f"### {profile_name}")
                    for item in active:
                        st.markdown(f"- {item}", unsafe_allow_html=True)
                    total_active += len(active)

            except:
                continue

        progress_bar.progress(1.0)

    if total_active == 0:
        st.info("Momentálně nejsou žádné aktivní zakázky v Karlovarském kraji.")
    else:
        st.success(f"Celkem nalezeno {total_active} aktivních zakázek")

st.caption("E-ZAK Karlovarský kraj • Prohledává všech 5 stránek zadavatelů")
