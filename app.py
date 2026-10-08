import streamlit as st
import pandas as pd
from datetime import datetime

# Thiết lập giao diện trang web
st.set_page_config(page_title="SmartCheck Logistics AI", layout="wide")

st.title("🚚 SmartCheck Logistics AI - Hệ thống Tiền Kiểm thông tin (Bước 2)")
st.subheader("Ứng dụng hỗ trợ Phòng Điều Vận rà soát thông tin lô hàng trước khi lập kế hoạch vận tải")

# Khu vực tải file Excel dữ liệu lên hệ thống
uploaded_file = st.file_uploader("Kéo và thả file Excel danh sách lô hàng vào đây để hệ thống tiền kiểm dữ liệu", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Đọc dữ liệu từ file Excel
        df = pd.read_excel(uploaded_file)
        
        # Tạo danh sách để chứa kết quả kiểm tra
        ket_qua = []
        
        # Vòng lặp quét qua từng dòng dữ liệu của lô hàng
        for index, row in df.iterrows():
            trang_thai = "🟢 ĐÃ DUYỆT"
            chi_tiet_loi = "Thông tin hợp lệ, đủ điều kiện chuyển sang Bước 3 (Lập kế hoạch điều xe)."
            
            # 1. KIỂM TRA ĐỐI CHIẾU CHỨNG TỪ (MÃ CONTAINER)
            if str(row['container_to_khai']).strip() != str(row['container_booking']).strip():
                trang_thai = "🔴 KHÓA LỆNH"
                chi_tiet_loi = f"LỆCH CONTAINER: Mã trên Tờ khai ({row['container_to_khai']}) không khớp với Booking Note ({row['container_booking']})"
            
            # 2. KIỂM TRA GIỚI HẠN TẢI TRỌNG QUY ĐỊNH (PHÁT HIỆN HÀNG QUÁ TẢI)
            # Giả định giới hạn tải trọng tiêu chuẩn tối đa cho phép là 25 tấn
            elif float(row['trong_luong_hang']) > 25.0:
                trang_thai = "🔴 KHÓA LỆNH"
                chi_tiet_loi = f"RỦI RO TẢI TRỌNG: Trọng lượng hàng {row['trong_luong_hang']} tấn vượt giới hạn tải trọng tiêu chuẩn quy định (25 tấn)"
            
            # 3. KIỂM TRA THỜI GIAN THỰC HIỆN (CẢNH BÁO RỦI RO TRỄ CHUYẾN/RỚT TÀU)
            else:
                try:
                    current_time = datetime.now()
                    closing_time = pd.to_datetime(row['closing_time_tau'])
                    # Tính khoảng thời gian chênh lệch từ thời điểm kiểm tra hiện tại đến lúc đóng hòm
                    thoi_gian_con_lai = (closing_time - current_time).total_seconds() / 3600
                    
                    # Nếu thời gian còn lại đến lúc tàu chạy ít hơn 12 tiếng (Rất gấp cho khâu lập kế hoạch và chạy xe bãi)
                    if thoi_gian_con_lai < 12.0:
                        trang_thai = "🟡 CẢNH BÁO"
                        chi_tiet_loi = f"RỦI RO THỜI GIAN: Thời gian từ lúc tiền kiểm đến lúc cắt máng còn dưới 12 giờ ({thoi_gian_con_lai:.1f} giờ). Cần ưu tiên lập kế hoạch gấp!"
                except:
                    pass
            
            # Lưu kết quả phân tích dòng này vào mảng
            ket_qua.append({
                "STT": index + 1,
                "Mã Cont (Tờ Khai)": row['container_to_khai'],
                "Trọng Lượng (Tấn)": row['trong_luong_hang'],
                "Trạng Thái AI": trang_thai,
                "Chi Tiết Phân Tích Rủi Ro (Bước 2)": chi_tiet_loi
            })
            
        # Chuyển mảng kết quả thành bảng dữ liệu
        df_ket_qua = pd.DataFrame(ket_qua)
        
        st.success(f"🎉 Hệ thống đã hoàn tất tiền kiểm dữ liệu cho {len(df)} lô hàng!")
        st.subheader("📊 Bảng phân tích dữ liệu đầu vào cho khâu Điều vận:")
        
        # Hàm tô màu hiển thị trực quan cho bảng kết quả trên web
        def format_status(val):
            if "🔴" in str(val): return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
            if "🟡" in str(val): return 'background-color: #fff2cc; color: #cc9900; font-weight: bold;'
            return 'background-color: #d9ead3; color: #274e13;'
            
        df_styled = df_ket_qua.style.map(format_status, subset=['Trạng Thái AI'])
        st.dataframe(df_styled, use_container_width=True)
        
    except Exception as error:
        st.error(f"Có lỗi cấu trúc dữ liệu xảy ra khi xử lý file: {error}")
        st.info("Mẹo: Hãy chắc chắn file Excel của bạn có đủ 5 cột tiêu đề: container_to_khai, container_booking, expiry_date, trong_luong_hang, closing_time_tau")
