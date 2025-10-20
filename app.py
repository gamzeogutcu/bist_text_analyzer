import streamlit as st
import pandas as pd
import plotly.express as px
from pipeline import analyze_texts

# ---------- Sayfa yapılandırma ----------
st.set_page_config(
    page_title="📈 BIST Text Analyzer",
    page_icon="💹",
    layout="wide"
)

# ---------- Arka plan ve stil ----------
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #fbc2eb, #a6c1ee);
    color: #222222;
    font-family: 'Segoe UI', sans-serif;
}
.stButton>button {
    background-color: #ff6347;
    color: white;
    font-weight: bold;
    border-radius: 10px;
    border: none;
    padding: 0.5em 1em;
    font-size: 16px;
}
.stTextArea>div>textarea {
    background-color: #fff8dc;
    border-radius: 10px;
    padding: 1em;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 BIST Hisse Analiz Aracı")
st.markdown("Metinlerden hisse, miktar, işlem ve duygu çıkarımı yapar.")

# ---------- Metin Girişi ----------
texts_input = st.text_area(
    "Analiz etmek istediğiniz cümleleri alt alta yazın:",
    value=(
        "AVISA 5 hisse aldım, çok iyi gidiyor\n"
        "THYAO 10 adet satıldı, düşüş yaşandı\n"
        "GARAN portföyümde var, kazançlı\n"
        "SASA almayı düşünüyorum, ama negatif bir durum yok\n"
        "THYAO'da 2 adet aldım, %5 yükseliş oldu"
    ),
    height=200
)

# ---------- Analiz ----------
if st.button("🔍 Analiz Et"):
    texts = [line.strip() for line in texts_input.split("\n") if line.strip()]
    if not texts:
        st.warning("Lütfen en az bir cümle girin!")
    else:
        df = analyze_texts(texts)
        if df.empty:
            st.info("Hiç hisse tespit edilemedi.")
        else:
            # ---------- Renkli Tablo ----------
            st.subheader("📄 Analiz Sonuçları")
            def color_sentiment(val):
                if val == 'positive':
                    return 'background-color: #b6fcd5; color: #006400'
                elif val == 'negative':
                    return 'background-color: #fcb6b6; color: #8b0000'
                else:
                    return 'background-color: #fff3b6; color: #8b6500'
            st.dataframe(df.style.applymap(color_sentiment, subset=['sentiment']))

            # ---------- Grafikler ----------
            st.subheader("📈 Duygu Dağılımı")
            sentiment_counts = df['sentiment'].value_counts().reset_index()
            sentiment_counts.columns = ['sentiment', 'count']
            fig1 = px.bar(sentiment_counts, x='sentiment', y='count',
                          color='sentiment', color_discrete_map={
                              'positive':'green', 'neutral':'gold', 'negative':'red'})
            st.plotly_chart(fig1, use_container_width=True)

            st.subheader("💼 İşlem Türü Dağılımı")
            action_counts = df['action'].fillna('none').value_counts().reset_index()
            action_counts.columns = ['action','count']
            fig2 = px.pie(action_counts, names='action', values='count',
                          color='action', color_discrete_map={
                              'buy':'green','sell':'red','none':'gray'})
            st.plotly_chart(fig2, use_container_width=True)

            st.subheader("🏦 En Çok Geçen Hisseler")
            asset_counts = df['asset'].value_counts().reset_index()
            asset_counts.columns = ['asset','count']
            fig3 = px.bar(asset_counts.head(10), x='asset', y='count', color='asset')
            st.plotly_chart(fig3, use_container_width=True)

            # ---------- CSV İndir ----------
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Analiz Sonuçlarını İndir", data=csv, file_name="bist_analysis.csv", mime='text/csv')
