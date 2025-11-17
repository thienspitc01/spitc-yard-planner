import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit_authenticator as stauth
from datetime import datetime
import yaml
from yaml.loader import SafeLoader

# ====================== CẤU HÌNH BẢO MẬT (bắt buộc có file config.yaml trong repo) ======================
# Nếu bạn chưa có file config.yaml, tạo ngay trong repo với nội dung ở cuối tin nhắn này
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

# ====================== LOGIN ĐÚNG PHIÊN BẢN MỚI NHẤT (không còn lỗi) ======================
authenticator.login(location='sidebar')

if st.session_state["authentication_status"]:
    st.sidebar.success(f'Chào {st.session_state["name"]} 👏')
    authenticator.logout('Logout', 'sidebar')
elif st.session_state["authentication_status"] is False:
    st.sidebar.error('Sai username/password')
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning('Vui lòng đăng nhập ở sidebar')
    st.stop()

# ====================== CÀI ĐẶT CỐ ĐỊNH ======================
st.set_page_config(page_title="SP-ITC Yard Planner", layout="wide")
st.title("🚢 SP-ITC Export Yard Planner – Online cho Team")

YARD_CAPACITY = {
    'A0': 650, 'H0': 650, 'I0': 650,
    'A1': 676, 'B1': 676, 'C1': 676, 'D1': 676,
    'A2': 884, 'B2': 884, 'C2': 884, 'D2': 884,
    'I1': 504, 'I2': 336, 'E2': 192,  # Reefer
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
    if size.startswith('4'): return 2
    return 2  # mặc định 40'

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
        uploaded_lich = st.file_uploader("Ảnh/PDF lịch tàu tuần", type=["png","jpg","pdf","jpeg"])

    if uploaded_ton:
        df_ton = pd.read_excel(uploaded_ton, engine='openpyxl')
        df_ton['Block'] = df_ton['Vị trí trên bãi'].apply(extract_block)
        df_ton['TEU'] = df_ton['Kích cỡ'].apply(tinh_teu)
        df_ton['IsReefer'] = df_ton.apply(is_reefer, axis=1)
        df_ton['SizeGroup'] = df_ton['Kích cỡ'].apply(lambda x: '20' if str(x).startswith('2') else '40+')

        occ_data = []
        for yard, cap in YARD_CAPACITY.items():
            ydf = df_ton[df_ton['Block'] == yard]
            teu = ydf['TEU'].sum()
            pct = round(teu / cap * 100, 1) if cap > 0 else 0
            occ_data.append({
                'Yard': yard,
                'Capacity': cap,
                'TEU': teu,
                '%': pct,
                'Màu': mau_occupancy(pct),
                '20': len(ydf[ydf['SizeGroup']=='20']),
                '40+': len(ydf[ydf['SizeGroup']=='40+']),
            })
        df_occ = pd.DataFrame(occ_data)

        st.session_state.df_ton = df_ton
        st.session_state.df_occ = df_occ
        st.success(f"✓ Đã cập nhật {len(df_ton):,} cont – {df_ton['TEU'].sum():,} TEU ({datetime.now().strftime('%H:%M %d/%m/%Y')})")

    if uploaded_lich:
        st.session_state.lich_image = uploaded_lich
        st.success("✓ Đã cập nhật lịch tàu mới")

with tab2:
    if 'df_occ' in st.session_state:
        df_occ = st.session_state.df_occ.sort_values('%', ascending=False)
        st.dataframe(df_occ.style.format({"%": "{:.1f}%"} ), use_container_width=True)

        fig = make_subplots(rows=1, cols=2, subplot_titles=("Occupancy (%)", "Phân bổ size"))
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['%'], text=df_occ['Màu'] + df_occ['%'].astype(str)+"%", textposition='outside'), row=1, col=1)
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['20'], name="20'"), row=1, col=2)
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['40+'], name="40+'"), row=1, col=2)
        st.plotly_chart(fig, use_container_width=True)

        top10 = st.session_state.df_ton.groupby('Tên tàu')['TEU'].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top10)

with tab3:
    st.header("Đề xuất hạ mới / Sà lan (tự động tách tàu chồng lịch)")
    col1, col2 = st.columns(2)
    with col1:
        loai = st.radio("Loại lô", ["Tàu trực tiếp", "Sà lan (theo COT)"])
        so_cont = st.number_input("Số container", 1, 1000, 100)
        reefer = st.number_input("Số reefer 40RH", 0, so_cont, 0)
        ty_le_20 = st.slider("Tỷ lệ 20' (%)", 0, 100, 30)
    with col2:
        if loai == "Tàu trực tiếp":
            berth = st.selectbox("Berth dự kiến", ["Berth 1A", "Berth 1B", "Berth 2"])
        else:
            st.date_input("COT sà lan", datetime.today() + timedelta(days=2))
            berth = None

    if st.button("🔥 Tính đề xuất ngay"):
        cont20 = int(so_cont * ty_le_20 / 100)
        cont40 = so_cont - cont20
        df_occ = st.session_state.df_occ.set_index('Yard')

        # Ưu tiên yard theo berth + còn dư
        if berth == "Berth 1A":
            priority = ['A0','H0','I0','B1','A1','A2','B2']
        elif berth == "Berth 1B":
            priority = ['B1','A1','A2','B2','C1']
        else:
            priority = ['D1','C1','D2','C2','A2','B2']

        # Nếu lịch dày → tự động thêm bãi tạm
        if so_cont > 200:
            priority += ['E1','F1','G1','H1']

        de_xuat = []
        remain20, remain40, remain_reefer = cont20, cont40, reefer

        # Reefer trước
        for y in ['I1','I2','E2']:
            if remain_reefer <= 0: break
            left = YARD_CAPACITY[y] - df_occ.loc[y,'TEU']
            take = min(remain_reefer, left // 2)
            if take > 0:
                de_xuat.append(f"✅ {take} reefer → {y} ({df_occ.loc[y,'%']:.1f}%)")
                remain_reefer -= take

        # Khô thường
        for y in priority:
            if y in ['I1','I2','E2']: continue
            if remain20 + remain40 == 0: break
            left = YARD_CAPACITY[y] - df_occ.loc[y,'TEU']
            take = min(remain20 + remain40, int(left / 1.7))
            take20 = min(remain20, int(take * ty_le_20 / 100))
            take40 = take - take20
            if take > 0:
                new_pct = df_occ.loc[y,'%'] + take*1.7 / YARD_CAPACITY[y] * 100
                de_xuat.append(f"✅ {take20}×20' + {take40}×40' → {y} {mau_occupancy(new_pct)}")
                remain20 -= take20
                remain40 -= take40

        for line in de_xuat:
            st.write(line)
        if remain20 + remain40 + remain_reefer > 0:
            st.error(f"⚠️ Thiếu chỗ cho {remain20+remain40+remain_reefer} cont → cần di chuyển nội bộ")

with tab4:
    st.header("Lịch tàu tuần hiện tại")
    if 'lich_image' in st.session_state:
        st.image(st.session_state.lich_image, use_column_width=True)
    else:
        st.info("Chưa có lịch – upload ảnh/PDF ở tab đầu tiên")

with tab5:
    st.header("Ghi chú team (realtime)")
    note = st.text_area("Viết ghi chú mới", height=150)
    if st.button("Gửi"):
        if 'notes' not in st.session_state:
            st.session_state.notes = []
        st.session_state.notes.append(f"[{datetime.now().strftime('%H:%M %d/%m')}] {st.session_state['name']}: {note}")
        st.rerun()
    if 'notes' in st.session_state:
        for n in reversed(st.session_state.notes[-30:]):
            st.write(n)

st.sidebar.info("App online 24/7 – Team SP-ITC 🚢")
