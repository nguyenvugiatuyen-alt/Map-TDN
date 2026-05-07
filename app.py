import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
import base64
from geopy.geocoders import Nominatim
import streamlit as st
from supabase import create_client, Client

# Điền thông tin thật lấy từ mục Settings > API trên Supabase
url: str = "https://pcxinjdikvascvwfurjl.supabase.co"
key: str = "sb_publishable_5mZvJ9_Y6QQBBI6ihGhLDw_INxHRnnS"
supabase: Client = create_client(url, key)

# --- CÁC HÀM XỬ LÝ DỮ LIỆU ---
def load_data():
    try:
        # 1. Lấy dữ liệu địa điểm
        locs_res = supabase.table("locations").select("*").execute()
        # 2. Lấy dữ liệu nhật ký (Nhớ tên bảng trên Supabase phải là 'diaries')
        diary_res = supabase.table("diaries").select("*").execute()
        
        return locs_res.data, diary_res.data
    except Exception as e:
        st.error(f"Lỗi load dữ liệu từ Supabase: {e}")
        return [], []

def save_location(new_loc):
    try:
        supabase.table("locations").insert(new_loc).execute()
        st.success("Đã lưu thành công!")
        # Xóa dữ liệu cũ trong session để nó tải lại từ Supabase
        if 'off_locations' in st.session_state:
            del st.session_state.off_locations 
        st.rerun() # Ép trình duyệt load lại
    except Exception as e:
        st.error(f"Lỗi: {e}")

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Bản Đồ CTTN - TDN", layout="wide")

# --- 2. CSS ÉP LIGHT MODE & STYLE ---
st.markdown("""
    <style>
    .stApp { background-color: white !important; color: black !important; }
    input { color: black !important; background-color: #f0f2f6 !important; }
    textarea { color: black !important; background-color: #f0f2f6 !important; }
    .stMarkdown p, label, .stText { color: black !important; }
    [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #e0e0e0; }
    button[data-baseweb="tab"] p { font-size: 22px !important; font-weight: bold !important; color: black !important; }
    .diary-card { border-radius: 15px; padding: 15px; margin-bottom: 15px; background-color: #FFFFFF; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #F0F0F0; color: black; }
    
    /* Màu đỏ cho nút xoá */
    div.stButton > button:first-child[style*="background-color: red"] {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. HÀM XỬ LÝ DỮ LIỆU ---

from PIL import Image
import io

def get_img_64(file):
    if file:
        # Mở ảnh bằng thư viện Pillow
        img = Image.open(file)
        # Chuyển về hệ màu RGB (tránh lỗi khi lưu ảnh PNG/WebP)
        img = img.convert("RGB")
        
        # Nén ảnh: Giảm kích thước xuống tối đa 800px chiều rộng
        img.thumbnail((800, 800)) 
        
        # Lưu vào bộ nhớ đệm với chất lượng 60%
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=60, optimize=True)
        
        # Trả về chuỗi Base64 đã nén
        return base64.b64encode(buffered.getvalue()).decode()
    return None

# Nạp dữ liệu
locs, diaries = load_data()
if 'off_locations' not in st.session_state: 
    st.session_state.off_locations = locs
if 'off_diaries' not in st.session_state: 
    st.session_state.off_diaries = diaries
if 'map_center' not in st.session_state: st.session_state.map_center = [10.7794, 106.7010]
if 'view_mode' not in st.session_state: st.session_state.view_mode = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'user_name' not in st.session_state: st.session_state.user_name = None

# --- 4. SIDEBAR ---
st.sidebar.markdown(f"""
    <div style="display: flex; justify-content: space-around; align-items: center; margin-bottom: 20px;">
        <img src="https://oj.vnoi.info/martor/fec9db73-5f4f-4b81-ad73-d901da48bd6c.png" width="70">
        <img src="https://upload.wikimedia.org/wikipedia/vi/0/09/Huy_Hi%E1%BB%87u_%C4%90o%C3%A0n.png" width="70">
    </div>
    """, unsafe_allow_html=True)

st.sidebar.subheader("🔑 Đăng nhập")
u_id = st.sidebar.text_input("Họ tên / Admin ID")
u_pw = st.sidebar.text_input("Mật khẩu (Admin)", type="password")

if st.sidebar.button("Xác nhận", use_container_width=True):
    if u_id == "admin_tdn" and u_pw == "tdn2026":
        st.session_state.is_admin = True
        st.session_state.user_name = "Ban Chỉ huy"
        st.sidebar.success("Chào Admin!")
    elif u_id:
        st.session_state.is_admin = False
        st.session_state.user_name = u_id
        st.sidebar.success(f"Chào {u_id}!")

# --- 5. GIAO DIỆN CHÍNH ---
st.title("BẢN ĐỒ CTTN - TRẦN ĐẠI NGHĨA")

# --- TRUY CẬP NHANH ---
st.write("📍 **Truy cập nhanh:**")
cols = st.columns(5)
for i, l in enumerate(st.session_state.off_locations):
    with cols[i % 5]:
        # Sửa l['Tên'] thành l['name']
        loc_name = l.get('name', 'Không tên') 
        if st.button(loc_name, key=f"quick_{i}", use_container_width=True):
            # Sửa l['Vĩ độ'] thành l['lat'], l['Kinh độ'] thành l['lon']
            st.session_state.map_center = [l['lat'], l['lon']]
            st.rerun()

st.divider()

t1, t2 = st.tabs(["📍 Bản đồ", "📸 Nhật ký"])

with t1:
    m = folium.Map(location=st.session_state.map_center, zoom_start=18)
    # Duyệt qua dữ liệu từ Supabase
    for l in st.session_state.off_locations:
        image_html = ""
        # Chú ý: l['main_img'] chứ không phải l.get('main_img') nếu Tuyển đã đặt tên cột như vậy
        if l.get('main_img'):
            image_html = f'''
                <div style="margin: 10px 0; text-align: center;">
                    <img src="data:image/png;base64,{l['main_img']}" 
                         style="width: 100%; max-width: 180px; height: auto; border-radius: 5px;">
                </div>
            '''
        
        # Tên cột trong Supabase là 'name' và 'description', không phải 'Tên' hay 'Mo_ta'
        popup_content = f"""
            <div style="font-family: Arial; width: 200px;">
                <h4 style="margin: 0; color: #1f77b4;">{l.get('name', 'Không tên')}</h4>
                {image_html}
                <p style="margin: 5px 0 0 0; font-size: 13px; color: #333;">{l.get('description', 'Điểm quân quân')}</p>
            </div>
        """
        
        folium.Marker(
            [l['lat'], l['lon']], # Dùng lat, lon viết thường
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=l.get('name'),
            icon=folium.Icon(color='blue', icon='university', prefix='fa')
        ).add_to(m)

    map_data = st_folium(m, width="100%", height=500, key="map_final")

    # CLICK GHIM
    # --- ĐOẠN NÀY SỬA LẠI CHO KHỚP SUPABASE (KHOẢNG DÒNG 171) ---
    if map_data['last_object_clicked']:
        lat_c = map_data['last_object_clicked']['lat']
        # Sửa 'Vĩ độ' thành 'lat'
        sel = next((l for l in st.session_state.off_locations if abs(l.get('lat', 0) - lat_c) < 0.0001), None)
        
        if sel:
            # Sửa sel['Tên'] thành sel['name'] (Dòng 174 bị lỗi của Tuyển nè)
            loc_name = sel.get('name', 'Địa điểm')
            st.info(f"📍 Đang chọn: {loc_name}")
            
            # HIỆN ẢNH ĐẠI DIỆN NẾU CÓ (Sửa 'main_img' cho chắc chắn)
            if sel.get('main_img'):
                st.image(f"data:image/png;base64,{sel['main_img']}", 
                        caption=f"Ảnh thực tế tại {loc_name}", 
                        use_container_width=True)
            
            c1, c2 = st.columns(2)
            if c1.button("➕ Đăng bài", use_container_width=True): st.session_state.view_mode = "post"
            if c2.button("📸 Xem ảnh", use_container_width=True): st.session_state.view_mode = "view"
            
            if st.session_state.view_mode == "post" and st.session_state.user_name:
                with st.form("f_post"):
                    t = st.text_input("Tiêu đề")
                    f = st.file_uploader("Ảnh", type=['jpg','png','jpeg'])
                    c = st.text_area("Cảm nghĩ")
                    if st.form_submit_button("Gửi bài"):
                        # Khi lưu Nhật ký, cũng dùng sel['name'] thay cho sel['Tên']
                        new_d = {
                            "loc_name": loc_name, 
                            "title": t, 
                            "content": c, 
                            "img_data": get_img_64(f), 
                            "date": datetime.now().strftime("%d/%m/%Y"), 
                            "author": st.session_state.user_name, 
                            "approved": False
                        }
                        # Lưu diary lên Supabase
                        try:
                            supabase.table("diaries").insert(new_d).execute()
                            st.success("Đã gửi bài chờ duyệt lên Supabase!")
                        except Exception as e:
                            st.error(f"Lỗi lưu nhật ký: {e}")

            elif st.session_state.view_mode == "view":
                # Sửa d['loc_name'] == sel['name']
                pics = [d for d in st.session_state.off_diaries if str(d.get('loc_name')) == str(loc_name) and d.get('approved')]
                if not pics:
                    st.write("Chưa có ảnh nào được duyệt tại đây.")
                for p in pics[::-1]:
                    if p.get('img_data'):
                        st.image(f"data:image/png;base64,{p['img_data']}", use_container_width=True)
                        st.caption(f"**{p.get('title')}** - {p.get('author')}")

    # --- CHỨC NĂNG ADMIN (CẬP NHẬT: XOÁ ĐỊA ĐIỂM) ---
    if st.session_state.is_admin:
        st.divider()
        st.header("🛠️ QUẢN TRỊ VIÊN")
        
        tab_ad1, tab_ad2 = st.tabs(["📍 Quản lý Địa điểm", "✅ Duyệt Nhật ký"])
        
        with tab_ad1:
            # --- PHẦN 1: THÊM BẰNG CÁCH CLICK ---
            if map_data.get('last_clicked'):
                n_lat, n_lng = map_data['last_clicked']['lat'], map_data['last_clicked']['lng']
                st.write(f"Tọa độ vừa chọn: `{n_lat}, {n_lng}`")
                with st.form("add_loc"):
                    n_name = st.text_input("Tên địa điểm mới (từ Click)")
                    n_desc = st.text_input("Mô tả (ví dụ: Điểm quân quân)", key="desc_click")
                    n_img = st.file_uploader("Ảnh đại diện", type=['jpg','png','jpeg'], key="img_click")
                    # --- TÌM ĐOẠN NÀY VÀ THAY THẾ ---
                    if st.form_submit_button("Lưu địa điểm này"):
                        if n_name:
                            # ĐOẠN MỚI DÁN VÀO ĐÂY:
                            new_loc_data = {
                                "name": n_name, 
                                "lat": n_lat, 
                                "lon": n_lng, 
                                "main_img": get_img_64(n_img), 
                                "description": n_desc
                            }
                            save_location(new_loc_data) # Gọi hàm lưu lên Supabase
                            
                            st.success(f"Đã lưu {n_name} lên Supabase!")
                            st.rerun()
            # --- PHẦN 2: THÊM THỦ CÔNG (LUÔN HIỆN) ---
            st.divider() 
            with st.form("form_manual_admin"):
                st.write("📍 **Thêm thủ công (tự nhập số):**")
                m_name = st.text_input("Tên địa điểm")
                m_desc = st.text_input("Mô tả (ví dụ: Điểm quân quân)", key="desc_man")
                m_img = st.file_uploader("Ảnh đại diện", type=['jpg','png','jpeg'], key="img_man")
                
                col_m1, col_m2 = st.columns(2)
                m_lat = col_m1.number_input("Vĩ độ", format="%.6f", value=10.779400)
                m_lng = col_m2.number_input("Kinh độ", format="%.6f", value=106.701000)
                
                # --- TÌM ĐOẠN NÀY VÀ THAY THẾ ---
                if st.form_submit_button("Lưu thủ công"):
                    if m_name:
                        # ĐOẠN MỚI DÁN VÀO ĐÂY:
                        new_loc_man = {
                            "name": m_name, 
                            "lat": m_lat, 
                            "lon": m_lng, 
                            "main_img": get_img_64(m_img), 
                            "description": m_desc
                        }
                        save_location(new_loc_man) # Gọi hàm lưu lên Supabase
                        
                        st.success(f"Đã lưu thủ công: {m_name}")
                        st.rerun()
            # --- PHẦN 3: DANH SÁCH QUẢN LÝ ĐỊA ĐIỂM (CHỈ GIỮ LẠI 1 ĐOẠN NÀY) ---
            # --- ĐOẠN ĐÃ SỬA THEO SUPABASE ---
            st.write("---")
            st.subheader("🗑️ Danh sách địa điểm hiện có")
            
            if not st.session_state.off_locations:
                st.info("Chưa có địa điểm nào được lưu.")
            
            for i, l in enumerate(st.session_state.off_locations):
                col_n, col_d = st.columns([4, 1])
                
                # Sửa l['Tên'] -> l.get('name')
                # Sửa l['Vĩ độ'] -> l.get('lat')
                # Sửa l['Kinh độ'] -> l.get('lon')
                name_display = l.get('name', 'Không tên')
                lat_display = l.get('lat', 0)
                lon_display = l.get('lon', 0)

                col_n.write(f"**{i+1}. {name_display}**")
                col_n.caption(f"📍 Tọa độ: {lat_display}, {lon_display}")
                
                # Nút xoá
                if col_d.button("Xoá", key=f"btn_del_{i}"):
                    # Gọi lệnh xóa trên Supabase dựa vào cột 'name' hoặc 'id'
                    try:
                        supabase.table("locations").delete().eq("name", name_display).execute()
                        st.success(f"Đã xoá {name_display} khỏi Supabase!")
                        # Xóa cache để tải lại dữ liệu mới
                        del st.session_state.off_locations
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi xóa: {e}")
        with tab_ad2:
            st.subheader("📋 Quản lý bài đăng Nhật ký")
            
            # Phân loại bài đăng
            pending = [d for d in st.session_state.off_diaries if not d['approved']]
            approved = [d for d in st.session_state.off_diaries if d['approved']]
            
            # --- PHẦN 1: DUYỆT BÀI ĐANG CHỜ ---
            st.markdown("#### ⏳ Bài đăng chờ duyệt")
            if not pending:
                st.info("Không có bài nào đang chờ duyệt.")
            for i, p in enumerate(pending):
                with st.expander(f"Duyệt: {p['title']} - {p['author']}"):
                    st.write(f"**Nội dung:** {p['content']}")
                    if p['img_data']:
                        st.image(f"data:image/png;base64,{p['img_data']}", width=300)
                    
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Đồng ý Duyệt", key=f"appr_btn_{p['id']}"):
                        for d in st.session_state.off_diaries:
                            if d['id'] == p['id']:
                                d['approved'] = True
                        save_data(st.session_state.off_diaries, "Diary")
                        st.success("Đã duyệt bài!")
                        st.rerun()
                    
                    # Nút xoá bài chờ duyệt (từ chối bài)
                    if c2.button("❌ Xoá / Từ chối", key=f"del_pend_{p['id']}"):
                        st.session_state.off_diaries = [d for d in st.session_state.off_diaries if d['id'] != p['id']]
                        save_data(st.session_state.off_diaries, "Diary")
                        st.warning("Đã xoá bài chờ duyệt.")
                        st.rerun()

            st.divider()

            # --- PHẦN 2: QUẢN LÝ BÀI ĐÃ ĐĂNG ---
            st.markdown("#### ✅ Bài đăng đã hiển thị")
            if not approved:
                st.info("Chưa có bài nào được duyệt.")
            for i, p in enumerate(approved):
                col_info, col_del = st.columns([4, 1])
                col_info.write(f"**{p['title']}** - {p['author']} ({p['date']})")
                
                # Nút xoá bài đã duyệt
                if col_del.button("Xoá bài", key=f"del_appr_{p['id']}", help="Gỡ bài đăng này khỏi nhật ký"):
                    st.session_state.off_diaries = [d for d in st.session_state.off_diaries if d['id'] != p['id']]
                    save_data(st.session_state.off_diaries, "Diary")
                    st.error(f"Đã xoá bài: {p['title']}")
                    st.rerun()

with t2:
    st.header("📸 Dòng thời gian chung")
    for p in [d for d in st.session_state.off_diaries if d['approved']][::-1]:
        st.markdown(f'<div class="diary-card"><h4>{p["title"]}</h4><p>{p["content"]}</p><small>📍 {p["loc_name"]} | {p["author"]} | {p["date"]}</small></div>', unsafe_allow_html=True)
        if p['img_data']: st.image(f"data:image/png;base64,{p['img_data']}", use_container_width=True)
