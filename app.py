import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --------------------------------------------------
# CONFIG CẤU HÌNH GIAO DIỆN WEB
# --------------------------------------------------
st.set_page_config(
    page_title="SmartCheck Logistics AI",
    page_icon="🚚",
    layout="wide"
)

class SmartCheckLogisticsApp:
    def ai_extract_ocr(self, document_type, file_content):
        return file_content

    def cross_check_and_audit(self, custom_declaration, booking_note, do_document):
        errors = []
        
        custom_data = self.ai_extract_ocr("Tờ khai Hải quan", custom_declaration)
        booking_data = self.ai_extract_ocr("Booking Note", booking_note)
        do_data = self.ai_extract_ocr("Lệnh giao hàng D/O", do_document)
        
        container_custom = str(custom_data.get("container_no", "")).strip().upper()
        container_booking = str(booking_data.get("container_no", "")).strip().upper()
        
        # 1. Kiểm tra mã Container
        if container_custom != container_booking:
            errors.append(f"LỆCH CONTAINER: Tờ khai ({container_custom}) vs Booking ({container_booking})")

        # 2. Kiểm tra hạn D/O
        try:
            do_expiry_date = datetime.strptime(str(do_data.get("expiry_date", "")).strip(), "%Y-%m-%d")
            current_date = datetime.now()
            if current_date > do_expiry_date:
                errors.append(f"HẾT HẠN D/O: Hết hạn từ ngày {do_data.get('expiry_date')}")
        except ValueError:
            errors.append("LỖI ĐỊNH DẠNG: Ngày trên D/O không hợp lệ (Cần YYYY-MM-DD)")

        if len(errors) > 0:
            return "🔴 KHÓA LỆNH", " | ".join(errors)
        else:
            return "🟢 ĐÃ DUYỆT", f"Khớp 100% (Container: {container_custom})"

app = SmartCheckLogisticsApp()

# --------------------------------------------------
# GIAO DIỆN HIỂN THỊ TRÊN TRÌNH DUYỆT WEB
# --------------------------------------------------
st.title("🚚 SmartCheck Logistics AI - Hệ thống Tiền Kiểm Chứng Từ")
st.markdown("""
Ứng dụng hỗ trợ phòng *Operations/Logistics* đối chiếu chéo thông tin Tờ Khai, Booking Note, và D/O tự động từ File Excel đầu vào nhằm ngăn chặn rủi ro phát sinh chi phí phạt tại Cảng.
""")

st.divider()

st.sidebar.header("📁 Hướng dẫn File Excel mẫu")
st.sidebar.markdown("""
File Excel của bạn cần có chính xác 3 cột sau ở hàng đầu tiên:
1. container_to_khai
2. container_booking
3. expiry_date (Định dạng: YYYY-MM-DD)
""")

uploaded_file = st.file_uploader("Kéo và thả file Excel danh sách lô hàng vào đây để kiểm tra", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, dtype=str)
        required_columns = ['container_to_khai', 'container_booking', 'expiry_date']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ File Excel thiếu các cột bắt buộc sau: {', '.join(missing_cols)}")
        else:
            st.success(f"📥 Đã tải lên thành công danh sách gồm *{len(df)}* lô hàng!")
            
            if st.button("🚀 BẮT ĐẦU QUÉT ĐỐI CHIẾU AI", type="primary"):
                df['Trạng thái AI'] = ""
                df['Chi tiết lỗi rủi ro'] = ""
                
                with st.spinner("Hệ thống AI đang tiến hành quét dữ liệu và đối chiếu..."):
                    for index, row in df.iterrows():
                        doc_to_khai = {"container_no": row['container_to_khai']}
                        doc_booking  = {"container_no": row['container_booking']}
                        doc_do       = {"expiry_date": row['expiry_date']}
                        
                        trang_thai, chi_tiet = app.cross_check_and_audit(doc_to_khai, doc_booking, doc_do)
                        
                        df.at[index, 'Trạng thái AI'] = trang_thai
                        df.at[index, 'Chi tiết lỗi rủi ro'] = chi_tiet
                
                st.balloons()
                st.subheader("📊 Kết quả phân tích rủi ro hệ thống:")
                st.dataframe(df, use_container_width=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Ket_Qua_Quet_AI')
                processed_data = output.getvalue()
                
                st.markdown("---")
                st.download_button(
                    label="💾 TẢI FILE BÁO CÁO KẾT QUẢ (EXCEL)",
                    data=processed_data,
                    file_name="ket_qua_doi_chieu_logistics_ai.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
    except Exception as e:
        st.error(f"Có lỗi xảy ra khi xử lý file: {e}")
else:
    st.info("💡 Vui lòng tải file Excel lên để hệ thống bắt đầu kiểm tra tự động.")