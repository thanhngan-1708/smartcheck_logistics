
import io
import time
from datetime import datetime

import pandas as pd
import streamlit as st

# ==================================================
# 1. CẤU HÌNH GIAO DIỆN
# ==================================================

st.set_page_config(
    page_title="SmartCheck Logistics",
    page_icon="🚚",
    layout="wide"
)

st.title("🚚 SmartCheck Logistics")
st.subheader(
    "Hệ thống tiền kiểm dữ liệu vận tải hỗ trợ Phòng Điều vận"
)

st.caption(
    "Phiên bản kiểm tra theo quy tắc (Rule-based). "
    "Kết quả phụ thuộc vào dữ liệu đầu vào và cấu hình của người dùng."
)

REQUIRED_COLUMNS = [
    "container_to_khai",
    "container_booking",
    "expiry_date",
    "trong_luong_hang",
    "closing_time_tau"
]

# ==================================================
# 2. CẤU HÌNH NGƯỠNG KIỂM TRA
# ==================================================

st.sidebar.header("⚙️ Cấu hình hệ thống")

weight_unit = st.sidebar.selectbox(
    "Đơn vị trọng lượng trong Excel",
    ["kg", "tấn"],
    index=0
)

max_weight = st.sidebar.number_input(
    "Ngưỡng trọng lượng hàng (tấn)",
    min_value=0.1,
    value=25.0,
    step=0.5,
    help="25 tấn là ngưỡng giả định dùng cho kiểm thử."
)

warning_hours = st.sidebar.number_input(
    "Cảnh báo trước giờ đóng máng (giờ)",
    min_value=1.0,
    value=12.0,
    step=1.0
)

st.sidebar.info(
    "Cần xác nhận ngưỡng trọng lượng và đơn vị với nghiệp vụ "
    "thực tế trước khi sử dụng chính thức."
)

# ==================================================
# 3. HÀM KIỂM TRA DỮ LIỆU
# ==================================================

def is_missing(value):
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass

    return str(value).strip() == ""


def clean_text(value):
    return "" if is_missing(value) else str(value).strip()


def parse_weight(value):
    """Chuyển trọng lượng về số; trả về None nếu dữ liệu không hợp lệ."""
    if is_missing(value):
        return None

    try:
        if isinstance(value, str):
            value = value.strip().replace(" ", "")

            # Hỗ trợ số thập phân như 18,5
            if "," in value and "." not in value:
                value = value.replace(",", ".")

        result = float(value)

        if result < 0:
            return None

        return result

    except (TypeError, ValueError):
        return None


def parse_date(value):
    if is_missing(value):
        return None

    try:
        result = pd.to_datetime(value, errors="coerce")

        if pd.isna(result):
            return None

        return result.to_pydatetime()

    except (TypeError, ValueError, OverflowError):
        return None


def check_shipment(row, checked_at):
    errors = []
    warnings = []

    # Lấy dữ liệu
    container_decl = clean_text(row["container_to_khai"])
    container_booking = clean_text(row["container_booking"])
    expiry_raw = row["expiry_date"]
    weight_raw = row["trong_luong_hang"]
    closing_raw = row["closing_time_tau"]

    # 1. KIỂM TRA THIẾU THÔNG TIN
    required_values = {
        "container_to_khai": row["container_to_khai"],
        "container_booking": row["container_booking"],
        "expiry_date": expiry_raw,
        "trong_luong_hang": weight_raw,
        "closing_time_tau": closing_raw
    }

    missing_fields = [
        name for name, value in required_values.items()
        if is_missing(value)
    ]

    if missing_fields:
        errors.append(
            "Thiếu thông tin bắt buộc: "
            + ", ".join(missing_fields)
        )

    # 2. KIỂM TRA MÃ CONTAINER
    if (
        container_decl
        and container_booking
        and container_decl.upper() != container_booking.upper()
    ):
        errors.append(
            f"Sai mã container: tờ khai {container_decl} "
            f"không khớp Booking {container_booking}."
        )

    # 3. KIỂM TRA TRỌNG LƯỢNG
    weight = parse_weight(weight_raw)
    weight_tons = None

    if not is_missing(weight_raw):
        if weight is None:
            errors.append(
                "Trọng lượng không hợp lệ hoặc là số âm."
            )
        else:
            # Quy đổi về tấn trước khi so sánh
            weight_tons = (
                weight / 1000
                if weight_unit == "kg"
                else weight
            )

            if weight_tons > max_weight:
                errors.append(
                    f"Trọng lượng {weight_tons:.2f} tấn "
                    f"vượt ngưỡng cấu hình {max_weight:.2f} tấn."
                )

    # 4. KIỂM TRA NGÀY HẾT HẠN
    expiry = parse_date(expiry_raw)

    if not is_missing(expiry_raw):
        if expiry is None:
            errors.append(
                "Ngày expiry_date không hợp lệ."
            )
        elif expiry.date() < checked_at.date():
            errors.append(
                f"Ngày hết hạn {expiry.date()} đã qua."
            )

    # 5. KIỂM TRA THỜI GIAN ĐÓNG MÁNG
    closing = parse_date(closing_raw)
    hours_left = None

    if not is_missing(closing_raw):
        if closing is None:
            errors.append(
                "Thời gian closing_time_tau không hợp lệ."
            )
        else:
            hours_left = (
                closing - checked_at
            ).total_seconds() / 3600

            if hours_left <= 0:
                errors.append(
                    "Thời điểm đóng máng đã qua."
                )
            elif hours_left < warning_hours:
                warnings.append(
                    f"Chỉ còn {hours_left:.1f} giờ đến giờ đóng máng."
                )

    # 6. TỔNG HỢP KẾT QUẢ
    if errors:
        if missing_fields:
            category = "THIEU_THONG_TIN"
            status = "🔴 CẦN BỔ SUNG"
        elif any("Sai mã container" in e for e in errors):
            category = "SAI_MA_CONTAINER"
            status = "🔴 KHÓA LỆNH"
        elif any("Trọng lượng" in e for e in errors):
            category = "QUA_TAI"
            status = "🔴 KHÓA LỆNH"
        elif any("hết hạn" in e.lower() for e in errors):
            category = "HET_HAN_CHUNG_TU"
            status = "🔴 KHÓA LỆNH"
        else:
            category = "LOI_DU_LIEU"
            status = "🔴 LỖI DỮ LIỆU"

        details = " ".join(errors + warnings)

    elif warnings:
        category = "CANH_BAO_THOI_GIAN"
        status = "🟡 CẢNH BÁO"
        details = " ".join(warnings)

    else:
        category = "HOP_LE"
        status = "🟢 ĐÃ DUYỆT"
        details = "Dữ liệu đạt các quy tắc tiền kiểm đã thiết lập."

    return {
        "category": category,
        "status": status,
        "details": details,
        "weight_tons": weight_tons,
        "hours_left": hours_left
    }


# ==================================================
# 4. TẠO FILE EXCEL KIỂM THỬ
# ==================================================

def create_test_file():
    test_data = pd.DataFrame([
        {
            "container_to_khai": "ABCU1234567",
            "container_booking": "ABCU1234567",
            "expiry_date": "2026-10-20",
            "trong_luong_hang": 18000,
            "closing_time_tau": "2026-10-20 20:00",
            "ket_qua_thu_cong": "HOP_LE"
        },
        {
            "container_to_khai": "ABCU1234567",
            "container_booking": "XYZU7654321",
            "expiry_date": "2026-10-20",
            "trong_luong_hang": 18000,
            "closing_time_tau": "2026-10-20 20:00",
            "ket_qua_thu_cong": "SAI_MA_CONTAINER"
        },
        {
            "container_to_khai": "ABCU1234567",
            "container_booking": "ABCU1234567",
            "expiry_date": "2026-10-20",
            "trong_luong_hang": 35000,
            "closing_time_tau": "2026-10-20 20:00",
            "ket_qua_thu_cong": "QUA_TAI"
        },
        {
            "container_to_khai": "ABCU1234567",
            "container_booking": "ABCU1234567",
            "expiry_date": None,
            "trong_luong_hang": 18000,
            "closing_time_tau": "2026-10-20 20:00",
            "ket_qua_thu_cong": "THIEU_THONG_TIN"
        }
    ])

    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer, engine="openpyxl"
    ) as writer:
        test_data.to_excel(
            writer, index=False, sheet_name="Sheet1"
        )

    buffer.seek(0)
    return buffer.getvalue()


st.download_button(
    "⬇️ Tải Excel kiểm thử 4 tình huống",
    data=create_test_file(),
    file_name="SmartCheck_KiemThu.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ==================================================
# 5. TẢI VÀ KIỂM TRA FILE
# ==================================================

st.markdown("### 📂 Tải dữ liệu vận tải")

uploaded_file = st.file_uploader(
    "Chọn file Excel cần kiểm tra",
    type=["xlsx", "xls"]
)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [str(c).strip() for c in df.columns]

        missing_columns = [
            col for col in REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing_columns:
            st.error(
                "File thiếu cột: " + ", ".join(missing_columns)
            )

        elif df.empty:
            st.warning("File không có dữ liệu.")

        else:
            checked_at = datetime.now()
            start = time.perf_counter()

            results = []

            for index, row in df.iterrows():
                result = check_shipment(row, checked_at)

                results.append({
                    "STT": index + 1,
                    "Mã container": clean_text(
                        row["container_to_khai"]
                    ),
                    "Trọng lượng đầu vào": clean_text(
                        row["trong_luong_hang"]
                    ),
                    "Trọng lượng (tấn)": (
                        round(result["weight_tons"], 2)
                        if result["weight_tons"] is not None
                        else None
                    ),
                    "Trạng thái": result["status"],
                    "Nhãn hệ thống": result["category"],
                    "Chi tiết kiểm tra": result["details"],
                    "Kết quả thủ công": (
                        clean_text(row["ket_qua_thu_cong"])
                        if "ket_qua_thu_cong" in df.columns
                        else ""
                    )
                })

            elapsed_seconds = time.perf_counter() - start
            result_df = pd.DataFrame(results)

            # BẢNG TỔNG QUAN
            st.success(
                f"Đã kiểm tra {len(result_df)} dòng dữ liệu."
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng số lô hàng", len(result_df))
            c2.metric("Thời gian xử lý", f"{elapsed_seconds:.3f} giây")
            c3.metric(
                "Ngưỡng trọng lượng",
                f"{max_weight:.1f} tấn"
            )

            st.markdown("### 📊 Kết quả kiểm tra")

            st.dataframe(
                result_df,
                use_container_width=True,
                hide_index=True
            )

            # XUẤT EXCEL
            output = io.BytesIO()

            with pd.ExcelWriter(
                output, engine="openpyxl"
            ) as writer:
                result_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Ket_qua"
                )

            output.seek(0)

            st.download_button(
                "⬇️ Tải kết quả kiểm tra",
                data=output.getvalue(),
                file_name="SmartCheck_KetQua.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # ĐỐI CHIẾU KIỂM TRA THỦ CÔNG
            st.markdown("### 🧪 Đối chiếu kết quả thủ công")

            if "ket_qua_thu_cong" in df.columns:
                comparison_rows = []

                for i, row in df.iterrows():
                    manual = clean_text(
                        row["ket_qua_thu_cong"]
                    ).upper()

                    if manual:
                        system_result = results[i]["category"]

                        comparison_rows.append({
                            "STT": i + 1,
                            "Kết quả thủ công": manual,
                            "Kết quả hệ thống": system_result,
                            "Khớp": manual == system_result
                        })

                if comparison_rows:
                    comparison_df = pd.DataFrame(
                        comparison_rows
                    )

                    st.dataframe(
                        comparison_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    total = len(comparison_df)
                    mismatches = int(
                        (~comparison_df["Khớp"]).sum()
                    )
                    mismatch_rate = mismatches / total * 100

                    a, b, c = st.columns(3)
                    a.metric("Số dòng đối chiếu", total)
                    b.metric("Số dòng sai lệch", mismatches)
                    c.metric(
                        "Tỷ lệ sai lệch",
                        f"{mismatch_rate:.2f}%"
                    )

                    st.caption(
                        "Tỷ lệ sai lệch = số dòng hệ thống khác kết quả "
                        "thủ công / tổng số dòng đã đối chiếu × 100%."
                    )
                else:
                    st.warning(
                        "Cột ket_qua_thu_cong chưa có nhãn để đối chiếu."
                    )
            else:
                st.info(
                    "Muốn đối chiếu, hãy thêm cột ket_qua_thu_cong "
                    "vào Excel và nhập nhãn kiểm tra thủ công cho từng dòng."
                )

            # ĐO MỨC GIẢM THỜI GIAN
            st.markdown("### ⏱️ Đánh giá thời gian xử lý")

            manual_minutes = st.number_input(
                "Nhập thời gian kiểm tra thủ công cùng bộ dữ liệu (phút)",
                min_value=0.0,
                value=0.0,
                step=0.5
            )

            if manual_minutes > 0:
                system_minutes = elapsed_seconds / 60
                reduction = (
                    (manual_minutes - system_minutes)
                    / manual_minutes
                ) * 100

                st.metric(
                    "Mức giảm thời gian",
                    f"{reduction:.2f}%"
                )

                st.caption(
                    "Mức giảm = (thời gian thủ công − thời gian hệ thống) "
                    "/ thời gian thủ công × 100%."
                )
            else:
                st.caption(
                    "Chưa có số đo thời gian thủ công nên chưa tính được "
                    "mức giảm thời gian. Hãy đo trên cùng bộ dữ liệu."
                )

            st.warning(
                "Lưu ý: ngưỡng tải trọng là tham số kiểm thử, không mặc nhiên "
                "là giới hạn pháp lý cho mọi loại xe hoặc container. "
                "Cần xác nhận ngưỡng và đơn vị trước khi triển khai thực tế."
            )

    except Exception as error:
        st.error(f"Không thể xử lý file Excel: {error}")
        st.info(
            "Kiểm tra định dạng file và tên 5 cột bắt buộc."
        )
