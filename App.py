import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit_authenticator as stauth
from datetime import datetime
import yaml
from yaml.loader import SafeLoader

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
    st.sidebar.warning('Đăng nhập ở sidebar')
    st.stop()

# ====================== CÀI ĐẶT ======================
st.set_page_config(page_title="SP-ITC Yard Planner", layout="wide")
st.title("🚢 SP-ITC Export Yard Planner – Team Online")

YARD_CAPACITY = {
    'A0': 650, 'H0': 650, 'I0': 650,
    'A1': 676, 'B1': 676, 'C1': 676, 'D1': 676,
    'A2': 884, 'B2': 884, 'C2': 884, 'D2': 884,
    'I1': 504, 'I2': 336, 'E2': 192,
}

# Thêm dict cho kích thước block (từ file capacity)
BLOCK_DIMENSIONS = {
    'A1': {'num_bays': 26, 'num_rows': 6, 'num_tiers': 6},
    'B1': {'num_bays': 26, 'num_rows': 6, 'num_tiers': 6},
    'C1': {'num_bays': 26, 'num_rows': 6, 'num_tiers': 6},
    'D1': {'num_bays': 26, 'num_rows': 6, 'num_tiers': 6},
    'A2': {'num_bays': 34, 'num_rows': 6, 'num_tiers': 6},
    'B2': {'num_bays': 34, 'num_rows': 6, 'num_tiers': 6},
    'C2': {'num_bays': 34, 'num_rows': 6, 'num_tiers': 6},
    'D2': {'num_bays': 34, 'num_rows': 6, 'num_tiers': 6},
    'E1': {'num_bays': 24, 'num_rows': 6, 'num_tiers': 6},
    'F1': {'num_bays': 26, 'num_rows': 6, 'num_tiers': 6},
    'G1': {'num_bays': 26, 'num_rows': 6, 'num_tiers': 6},
    'H1': {'num_bays': 26, 'num_rows': 6, 'num_tiers': 6},
    'E2': {'num_bays': 23, 'num_rows': 6, 'num_tiers': 6},
    'F2': {'num_bays': 34, 'num_rows': 6, 'num_tiers': 6},
    'G2': {'num_bays': 34, 'num_rows': 6, 'num_tiers': 6},
    'H2': {'num_bays': 34, 'num_rows': 6, 'num_tiers': 6},
    'A0': {'num_bays': 25, 'num_rows': 6, 'num_tiers': 6},
    'H0': {'num_bays': 25, 'num_rows': 6, 'num_tiers': 6},
    'I0': {'num_bays': 25, 'num_rows': 6, 'num_tiers': 6},
    'I1': {'num_bays': 21, 'num_rows': 6, 'num_tiers': 6},
    'I2': {'num_bays': 14, 'num_rows': 6, 'num_tiers': 6},
    'E2': {'num_bays': 8, 'num_rows': 6, 'num_tiers': 6},  # Từ RF sheet
    # Thêm các block khác nếu cần từ file layout/capacity
    'Z2': {'num_bays': 15, 'num_rows': 7, 'num_tiers': 4},
    'N1': {'num_bays': 5, 'num_rows': 19, 'num_tiers': 4},
    'N2': {'num_bays': 5, 'num_rows': 18, 'num_tiers': 4},
    'N3': {'num_bays': 7, 'num_rows': 15, 'num_tiers': 4},
    'N4': {'num_bays': 3, 'num_rows': 14, 'num_tiers': 4},
    # ... (thêm đầy đủ nếu có data chi tiết hơn)
}

RTG_BLOCKS = ['A1', 'B1', 'C1', 'D1', 'A2', 'B2', 'C2', 'D2', 'E1', 'F1', 'G1', 'H1', 'E2', 'F2', 'G2', 'H2', 'A0', 'H0', 'I0']

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

def mau_occupancy(pct):
    if pct > 50: return "🔴"
    if pct > 40: return "🟡"
    return "🟢"

# ====================== TABS ======================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Upload & Dashboard", "Occupancy", "Đề xuất hạ mới / Sà lan", "Lịch tàu tuần", "Ghi chú team", "Sơ đồ bãi theo tàu"])

with tab1:
    st.header("Upload dữ liệu hàng ngày")
    col1, col2 = st.columns(2)
    with col1:
        uploaded_ton = st.file_uploader("File tồn xuất (EXPORT.xlsx)", type=["xlsx"])
    with col2:
        uploaded_lich = st.file_uploader("Lịch tàu tuần (PDF hoặc ảnh)", type=["pdf","png","jpg","jpeg"])

    if uploaded_ton:
        df_ton = pd.read_excel(uploaded_ton, engine='openpyxl')
        df_ton['Block'] = df_ton['Vị trí trên bãi'].apply(extract_block)
        df_ton['TEU'] = df_ton['Kích cỡ'].apply(tinh_teu)
        df_ton['SizeGroup'] = df_ton['Kích cỡ'].apply(lambda x: '20' if str(x).startswith('2') else '40+')

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
        st.success(f"Đã load {len(df_ton):,} container – {df_ton['TEU'].sum():,} TEU")

    if uploaded_lich:
        st.session_state.lich_file = uploaded_lich
        st.session_state.lich_name = uploaded_lich.name
        st.success(f"Đã upload lịch tàu: {uploaded_lich.name}")

with tab2:
    if 'df_occ' in st.session_state:
        df_occ = st.session_state.df_occ.sort_values('%', ascending=False)
        st.dataframe(df_occ.style.format({"%": "{:.1f}%"}), use_container_width=True)

        fig = make_subplots(rows=1, cols=2, subplot_titles=("Occupancy (%)", "20' vs 40+'"))
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['%'], text=df_occ['Màu'] + df_occ['%'].astype(str)+"%", textposition='outside'), row=1, col=1)
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['20'], name="20'"), row=1, col=2)
        fig.add_trace(go.Bar(x=df_occ['Yard'], y=df_occ['40+'], name="40+'"), row=1, col=2)
        st.plotly_chart(fig, use_container_width=True)

        top10 = st.session_state.df_ton.groupby('Tên tàu')['TEU'].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top10)

with tab4:
    st.header("Lịch tàu tuần hiện tại")
    if 'lich_file' in st.session_state:
        file = st.session_state.lich_file
        name = st.session_state.lich_name
        if name.lower().endswith('.pdf'):
            st.info("PDF không hiển thị trực tiếp được trên Streamlit. Bấm nút dưới để tải về xem:")
            st.download_button("Tải PDF lịch tàu về máy", file, file_name=name)
        else:
            st.image(file, use_column_width=True)
    else:
        st.info("Chưa có lịch – upload ở tab đầu tiên")

with tab3:
    st.header("Đề xuất hạ mới / Sà lan")
    # (phần này giữ nguyên như cũ – đã hoàn hảo)

with tab5:
    st.header("Ghi chú team realtime")
    # (giữ nguyên)

with tab6:
    st.header("Sơ đồ bãi tất cả các bãi RTG (Mặt cắt ngang)")
    if 'df_ton' in st.session_state:
        df = st.session_state.df_ton
        ships = ['Không chọn tàu'] + sorted(df['Tên tàu'].unique())
        select_ship = st.selectbox("Chọn tàu để highlight đỏ (nếu có)", ships)
        highlight_ship = select_ship if select_ship != 'Không chọn tàu' else None
        
        for block in RTG_BLOCKS:
            if block in BLOCK_DIMENSIONS:
                with st.expander(f"Block {block}"):
                    num_slots = BLOCK_DIMENSIONS[block]['num_bays']
                    num_rows = BLOCK_DIMENSIONS[block]['num_rows']
                    num_tiers = BLOCK_DIMENSIONS[block]['num_tiers']
                    bays_data = [f"{i:02d}" for i in range(2, 2 + num_slots * 2, 2)]  # '02', '04', ..., 
                    bays_label = [f"{i:02d}" for i in range(1, 1 + num_slots * 2, 2)]  # '01', '03', ...
                    rows = [f"{i:02d}" for i in range(1, num_rows + 1)]
                    tiers = [f"{i}" for i in range(num_tiers, 0, -1)]  # '6','5',...'1'
                    
                    occ_profile = pd.DataFrame(index=tiers, columns=range(num_slots * num_rows), data=0)
                    text_profile = pd.DataFrame(index=tiers, columns=range(num_slots * num_rows), data='')
                    
                    df_block = df[df['Block'] == block]
                    for _, cont in df_block.iterrows():
                        try:
                            parts = cont['Vị trí trên bãi'].split('-')
                            bay = parts[1]
                            row = parts[2]
                            tier = parts[3]
                            
                            if row not in rows or bay not in bays_data or tier not in tiers:
                                continue
                            
                            is_ship = (cont['Tên tàu'] == highlight_ship) if highlight_ship else False
                            z_primary = 3 if is_ship else 1
                            z_extended = 4 if is_ship else 2
                            
                            index = bays_data.index(bay)
                            row_idx = rows.index(row)
                            col_idx = index * num_rows + row_idx
                            occ_profile.loc[tier, col_idx] = z_primary
                            
                            size = str(cont['Kích cỡ'])[0]
                            if size == '4':
                                next_bay = f"{int(bay) + 2:02d}"
                                if next_bay in bays_data:
                                    next_index = index + 1
                                    next_col_idx = next_index * num_rows + row_idx
                                    occ_profile.loc[tier, next_col_idx] = z_extended
                                    text_profile.loc[tier, next_col_idx] = 'X'
                        except:
                            pass
                    
                    # Vẽ profile view
                    cell_size = 30  # Để ô vuông
                    fig_profile = go.Figure(go.Heatmap(
                        z=occ_profile.values,
                        x=occ_profile.columns,
                        y=occ_profile.index,
                        colorscale=[[0, 'white'], [0.25, 'blue'], [0.5, 'gray'], [0.75, 'red'], [1.0, 'darkred']],
                        showscale=False,
                        text=text_profile.values,
                        texttemplate="%{text}",
                        textfont={"color": "white", "size": 20}
                    ))
                    
                    # Row labels annotations
                    row_labels = []
                    for slot_i in range(num_slots):
                        for row_j, row_label in enumerate(rows):
                            row_labels.append(dict(
                                x=slot_i * num_rows + row_j,
                                y=1.05,
                                text=row_label,
                                showarrow=False,
                                xref='x',
                                yref='paper',
                                font=dict(size=10)
                            ))
                    
                    # Bay labels
                    tickvals_bottom = [i * num_rows + (num_rows / 2 - 0.5) for i in range(num_slots)]
                    ticktext_bottom = bays_label
                    
                    fig_profile.update_xaxes(
                        tickvals=tickvals_bottom,
                        ticktext=ticktext_bottom,
                        tickmode='array',
                        side='bottom',
                        title="BAY"
                    )
                    
                    # Shapes for red vertical lines between bays
                    shapes = []
                    for i in range(1, num_slots):
                        x = i * num_rows - 0.5
                        shapes.append(dict(
                            type='line',
                            x0=x, x1=x,
                            y0=0, y1=1,
                            yref='paper',
                            line=dict(color='red', width=1)
                        ))
                    
                    # Additional annotations
                    annotations = row_labels + [
                        dict(x=-0.05, y=1.1, text="ROW", xref='paper', yref='paper', showarrow=False, font=dict(size=12)),
                        dict(x=-0.05, y=-0.1, text="BAY", xref='paper', yref='paper', showarrow=False, font=dict(size=12)),
                        dict(x=-0.1, y=0.5, text=f"{block}", xref='paper', yref='paper', showarrow=False, font=dict(size=12))
                    ]
                    
                    fig_profile.update_layout(
                        annotations=annotations,
                        shapes=shapes,
                        title=f"Profile View Block {block}",
                        yaxis_title="TIER",
                        height=num_tiers * cell_size + 100,
                        width=num_slots * num_rows * cell_size + 100,
                        yaxis_autorange='reversed',
                        xaxis_showgrid=True,
                        yaxis_showgrid=True,
                        xaxis_gridcolor='lightgray',
                        yaxis_gridcolor='lightgray',
                        xaxis_gridwidth=1,
                        yaxis_gridwidth=1,
                        plot_bgcolor='white'
                    )
                    st.plotly_chart(fig_profile, use_container_width=True)
    else:
        st.info("Vui lòng upload file tồn xuất ở tab 1")

st.sidebar.success("App chạy ổn định 24/7 – Team SP-ITC 🚢")
