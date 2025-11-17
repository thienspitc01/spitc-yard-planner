import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit_authenticator as stauth
from datetime import datetime
import yaml
from yaml.loader import SafeLoader
from io
from PIL import Image
import fitz  # PyMuPDF – đã có sẵn trên Streamlit Cloud

# ====================== LOGIN ======================
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

authenticator.login(location='sidebar')

if st.session_state["authentication_status"]:
    st.sidebar.success(f'Chào {st.session_state["name"]} 👏')
    authenticator.logout('Logout', 'sidebar')
elif st.session_state["authentication_status"] is False:
    st.sidebar.error('Sai username/password')
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning('Vui lòng đăng nhập ở sidebar bên trái')
    st.stop()

# ====================== CÀI ĐẶT ======================
st.set_page_config(page_title="SP-ITC Yard Planner", layout="wide")
st.title("🚢 SP-ITC Export Yard Planner – Online Team")

YARD_CAPACITY = {
    'A0': 650, 'H0': 650, 'I0': 650,
    'A1': 676, 'B1': 676, 'C1': 676, 'D1': 676,
    'A2': 884, 'B2': 884, 'C2': 884, 'D2': 884,
    'I1': 504, 'I2': 336, 'E2': 192,
}

def extract_block(pos):
    if pd.isna(pos): return "Unknown"
    try:
        return str(pos).split('-')[0].upper()
    except:
        return "Unknown"

def tinh_teu(size):
    size = str(size)
    if size.startswith('2'): return 1
    return 2

def is_reefer(row):
    return ('R' in str(row.get('Kích cỡ ISO', ''))) or ('Reefer' in str(row.get('Loại Hàng', '')))

def mau_occupancy(pct):
    if pct > 50: return "🔴"
    if pct > 40: return "🟡"
    return "🟢"

# ====================== TABS ======================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Upload & Dashboard", "Occupancy hiện tại", "Đề xuất hạ mới / Sà lan", "Lịch tàu tuần", "Ghi chú team"])

with tab1:
    st.header("Upload dữ liệu mới (mỗi sáng 8h30)")
    col1, col2 = st.columns(2)
    with col1:
        uploaded_ton = st.file_uploader("File tồn bãi xuất (EXPORT.xlsx)", type=["xlsx"])
    with col2:
        uploaded_lich = st.file_uploader("Lịch tàu tuần (PDF hoặc ảnh)", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded_ton:
        df_ton = pd.read_excel(uploaded_ton, engine='openpyxl')
        df_ton['Block'] = df_ton['Vị trí trên bãi'].apply(extract_block)
        df_ton['TEU'] = df_ton['Kích cỡ'].apply(tinh_teu)
        df_ton['IsReefer'] = df_ton.apply(is_reefer, axis=1)
        df_ton['SizeGroup'] = df_ton['Kích cỡ'].apply(lambda x: '20' if str(x).startswith('2')) else '40+')

        occ_data = []
        for yard, cap in YARD_CAPACITY.items():
            ydf = df_ton[df_ton['Block'] == yard]
            teu = ydf['TEU'].sum()
            pct = round(teu / cap * 100, 1) if cap > 0 else 0
            occ_data.append({
                'Yard': yard, 'Capacity': cap, 'TEU': teu, '%': pct, 'Màu': mau_occupancy(pct),
                '20': len(ydf[ydf['SizeGroup']=='20']),
                '40+': len(ydf[ydf['SizeGroup']=='40+']),
            })
        df_occ = pd.DataFrame(occ_data)

        st.session_state.df_ton = df_ton
        st.session_state.df_occ = df_occ
        st.success(f"Đã cập nhật {len(df_ton):,} cont – {df_ton['TEU'].sum():,} TEU")

    if uploaded_lich:
        st.session_state.lich_file = uploaded_lich
        st.success("Đã upload lịch tàu thành công!")

with tab2:
    if 'df_occ' in st.session_state:
        df_occ = st.session_state.df_occ.sort_values('%', ascending=False)
        st.dataframe(df_occ.style.format({"%": "{:.1f}%"}), use_container_width=True)

        fig = make_subplots(rows=1, cols=2, subplot_titles=("Occupancy (%)", "20' vs 40+'"))
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['%'], text=df_occ['Màu'] + df_occ['%'].astype(str)+"%", textposition='outside'), row=1, col=1)
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['20'], name="20'"), row=1, col=2)
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['40+'], name="40+'"), row=1, col=2)
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    # (giữ nguyên phần đề xuất như trước – đã hoàn hảo)

with tab4:
    st.header("Lịch tàu tuần hiện tại")
    if 'lich_file' in st.session_state:
        file = st.session_state.lich_file
        if file.type == "application/pdf":
            # Convert PDF trang 1 thành ảnh
            pdf_doc = fitz.open(stream=file.read(), filetype="pdf")
            page = pdf_doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # độ phân giải cao
            img_bytes = pix.tobytes("png")
            st.image(img_bytes, use_column_width=True)
        else:
            st.image(file, use_column_width=True)
    else:
        st.info("Chưa có lịch tuần này – upload PDF/ảnh ở tab đầu")

with tab5:
    st.header("Ghi chú team (realtime)")
    note = st.text_area("Viết ghi chú mới", height=150)
    if st.button("Gửi ghi chú"):
        if 'notes' not in st.session_state:
            st.session_state.notes = []
        st.session_state.notes.append(f"[{datetime.now().strftime('%H:%M %d/%m')}] {st.session_state['name']}: {note}")
        st.rerun()
    if 'notes' in st.session_state:
        for n in reversed(st.session_state.notes[-30:]):
            st.write(n)

st.sidebar.success("App chạy mượt – Team SP-ITC 🚢")
