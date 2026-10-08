mport streamlit as st
import pandas as pd
from datetime import datetime

# Thiết lập giao diện trang web
st.set_page_config(page_title="SmartCheck Logistics AI", layout="wide")

st.title("🚚 SmartCheck Logistics AI - Hệ thống Điều Vận & Tiền Kiểm Thông Minh")
st.subheader("Hỗ trợ Phòng Điều Vận rà soát Chứng từ, Tải trọng, Thời gian và An toàn Tài xế")

# Khu vực tải file Excel dữ liệu lên hệ thống
uploaded_file = st.file_uploader("Kéo và thả file Excel điều xe vào đây để hệ thống tiền kiểm tự động", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Đọc dữ liệu từ file Excel
        df = pd.read_excel(uploaded_file)
        
        # Tạo danh sách để chứa kết quả kiểm tra
        ket_qua = []
        
        # Vòng lặp quét qua từng dòng dữ liệu của lô hàng
        for index, row in df.iterrows():
            trang_thai = "🟢 ĐÃ DUYỆT"
            chi_tiet_loi = "Mọi thông tin hợp lệ, đủ điều kiện điều xe."
            
            # 1. KIỂM TRA ĐỐI CHIẾU CHỨNG TỪ (MÃ CONTAINER)
            if str(row['container_to_khai']).strip() != str(row['container_booking']).strip():
                trang_thai = "🔴 KHÓA LỆNH"
                chi_tiet_loi = f"LỆCH CONTAINER: Hải quan ({row['container_to_khai']}) vs Hãng tàu ({row['container_booking']})"
            
            # 2. KIỂM TRA GIỚI HẠN TẢI TRỌNG (TRÁNH PHẠT QUÁ TẢI)
            elif float(row['trong_luong_hang']) > float(row['tai_trong_cho_phep']):
                trang_thai = "🔴 KHÓA LỆNH"
                chi_tiet_loi = f"QUÁ TẢI TRỌNG: Hàng nặng {row['trong_luong_hang']} tấn vượt tải xe cho phép {row['tai_trong_cho_phep']} tấn"
            
            # 3. KIỂM TRA TRẠNG THÁI AN TOÀN TÀI XẾ (GIỜ LÁI XE)
            elif float(row['so_gio_da_lai']) >= 8.0:
                trang_thai = "🟡 CẢNH BÁO"
                chi_tiet_loi = f"AN TOÀN TÀI XẾ: Tài xế {row['ten_tai_xe']} đã lái {row['so_gio_da_lai']} tiếng, cần đổi tài xế dự phòng"
            
            # 4. KIỂM TRA THỜI GIAN VẬN CHUYỂN (TRÁNH RỚT TÀU)
            else:
                try:
                    tg_xuat_phat = pd.to_datetime(row['thoi_gian_xuat_phat'])
                    closing_time = pd.to_datetime(row['closing_time_tau'])
                    # Tính khoảng thời gian chênh lệch từ lúc chạy đến lúc đóng hòm
                    thoi_gian_con_lai = (closing_time - tg_xuat_phat).total_seconds() / 3600
                    
                    # Nếu thời gian còn lại ít hơn 4 tiếng
                    if thoi_gian_con_lai < 4.0:
                        trang_thai = "🟡 CẢNH BÁO"
                        chi_tiet_loi = f"RỦI RO TRỄ CHUYẾN: Thời gian từ lúc xuất phát đến lúc cắt máng chỉ còn {thoi_gian_con_lai:.1f} giờ"
                except:
                    pass
            
            # Lưu kết quả phân tích dòng này vào mảng
            ket_qua.append({
                "STT": index + 1,
                "Tài Xế": row.get('ten_tai_xe', 'N/A'),
                "Mã Container (Tờ Khai)": row['container_to_khai'],
                "Trạng Thái AI": trang_thai,
                "Chi Tiết Phân Tích Rủi Ro": chi_tiet_loi
            })
            
        # Chuyển mảng kết quả thành bảng dữ liệu
        df_ket_qua = pd.DataFrame(ket_qua)
        
        st.success(f"🎉 Hệ thống đã quét hoàn tất danh sách gồm {len(df)} lô hàng!")
        st.subheader("📊 Kết quả phân tích rủi ro vận hành đa tầng:")
        
        # Hàm tô màu hiển thị trực quan cho bảng kết quả trên web
        def format_status(val):
            if "🔴" in str(val): return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
            if "🟡" in str(val): return 'background-color: #fff2cc; color: #cc9900; font-weight: bold;'
            return 'background-color: #d9ead3; color: #274e13;'
            
        df_styled = df_ket_qua.style.map(format_status, subset=['Trạng Thái AI'])
        st.dataframe(df_styled, use_container_width=True)
        
    except Exception as error:
        st.error(f"Có lỗi cấu trúc dữ liệu xảy ra khi xử lý file: {error}")
        st.info("Mẹo: Hãy chắc chắn file Excel của bạn có đủ các cột: container_to_khai, container_booking, trong_luong_hang, tai_trong_cho_phep, ten_tai_xe, so_gio_da_lai, thoi_gian_xuat_phat, closing_time_tau"
