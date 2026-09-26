# -*- coding: utf-8 -*-
"""
====================================================================
ỨNG DỤNG: TAROT & ORACLE MENTOR (STREAMLIT + GEMINI)
Mục đích: Cố vấn tự học đọc bài Tarot, Oracle, Tea Leaf
chuẩn xác theo tài liệu Guidebook gốc (PDF/TXT) bằng Gemini API.
====================================================================
"""

import streamlit as st
import tempfile
import time
import os

# Cấu hình trang giao diện Streamlit
st.set_page_config(
    page_title="Tarot & Oracle Mentor",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# 1. KHỞI TẠO SESSION STATE (LƯU TRỮ DỮ LIỆU BỘ BÀI VÀ TRẢI BÀI)
# -------------------------------------------------------------
if "decks" not in st.session_state:
    # Cấu trúc mỗi bộ bài: { "name": str, "file_ref": obj, "file_name": str, "type": str }
    st.session_state.decks = {}

if "history" not in st.session_state:
    st.session_state.history = []

# -------------------------------------------------------------
# 2. THANH BÊN (SIDEBAR) - CẤU HÌNH API KEY VÀ HƯỚNG DẪN
# -------------------------------------------------------------
with st.sidebar:
    st.title("🔮 Tarot & Oracle Mentor")
    st.caption("Trợ lý đồng hành tự học giải bài theo Guidebook")
    st.markdown("---")

    # Nhập Gemini API Key
    api_key = st.text_input(
        "🔑 Gemini API Key:",
        type="password",
        placeholder="Nhập mã AI Studio API Key của bạn...",
        help="Lấy API Key miễn phí tại: https://aistudio.google.com/apikey"
    )

    if not api_key:
        st.warning("⚠️ Vui lòng nhập API Key để bắt đầu sử dụng.")
    else:
        st.success("✅ Đã nhận API Key")

    st.markdown("---")

    # Hướng dẫn sử dụng app
    with st.expander("📖 Hướng dẫn sử dụng nhanh", expanded=False):
        st.markdown("""
        **Bước 1:** Nhập Gemini API Key ở ô trên.
        
        **Bước 2 (Tab 1):** Tải file Guidebook (PDF hoặc TXT) của bộ bài bạn đang dùng (Ví dụ: The Wild Unknown, Rider-Waite, Tea Leaf...).
        
        **Bước 3 (Tab 2):** 
        - Chọn bộ bài vừa nạp.
        - Nhập câu hỏi và các lá bài bạn rút ở đời thực.
        - Ghi cảm nhận trực giác sơ bộ của bạn (nếu có).
        - Bấm **'Phân tích cùng Mentor'** để AI tra cứu đúng sách và hướng dẫn bạn chiêm nghiệm.
        """)

    st.markdown("---")
    st.markdown("💡 *Mẹo: Bạn có thể lưu trữ nhiều bộ bài khác nhau trong một phiên làm việc.*")


# -------------------------------------------------------------
# 3. HÀM XỬ LÝ UPLOAD VÀ THEO DÕI TRẠNG THÁI FILE LÊN GEMINI
# -------------------------------------------------------------
def upload_guidebook_to_gemini(uploaded_file, deck_name, api_key_str):
    """
    Lưu file tạm, đẩy lên Gemini Files API và đợi cho đến khi ACTIVE
    """
    try:
        # Sử dụng SDK Google Gen AI
        try:
            from google import genai
            client = genai.Client(api_key=api_key_str)
            use_new_sdk = True
        except ImportError:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=api_key_str)
            use_new_sdk = False

        # Lưu file tải lên vào thư mục tạm của máy
        file_suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name

        status_placeholder = st.empty()
        status_placeholder.info(f"⏳ Đang tải file `{uploaded_file.name}` lên Gemini Files API...")

        # Đẩy file lên Gemini
        if use_new_sdk:
            gemini_file = client.files.upload(file=temp_path)
            # Chờ xử lý nếu là PDF lớn
            while gemini_file.state.name == "PROCESSING":
                time.sleep(2)
                gemini_file = client.files.get(name=gemini_file.name)
            
            if gemini_file.state.name != "ACTIVE":
                raise Exception(f"File xử lý thất bại: {gemini_file.state.name}")
        else:
            gemini_file = legacy_genai.upload_file(path=temp_path, display_name=deck_name)
            while gemini_file.state.name == "PROCESSING":
                time.sleep(2)
                gemini_file = legacy_genai.get_file(gemini_file.name)
            
            if gemini_file.state.name != "ACTIVE":
                raise Exception(f"File xử lý thất bại: {gemini_file.state.name}")

        # Xóa file tạm trên máy cục bộ
        try:
            os.remove(temp_path)
        except Exception:
            pass

        status_placeholder.success(f"✨ File `{uploaded_file.name}` đã sẵn sàng (ACTIVE)!")
        return gemini_file, use_new_sdk

    except Exception as e:
        st.error(f"❌ Lỗi tải tài liệu: {str(e)}")
        return None, None


# -------------------------------------------------------------
# 4. HÀM GỌI GEMINI ĐỂ PHÂN TÍCH (THEO ĐÚNG PROMPT YÊU CẦU)
# -------------------------------------------------------------
def analyze_reading_with_mentor(deck_info, question, cards, user_reflection, api_key_str):
    """
    Gọi Gemini với file Guidebook đính kèm và Prompt sư phạm chuẩn
    """
    # Xây dựng prompt chuẩn theo đúng đặc tả của bài toán
    prompt_text = f"""Bạn là một Mentor dạy đọc bài. File đính kèm là guidebook của bộ bài [{deck_info['name']}].
Câu hỏi của người học: [{question}].
Các lá bài rút được: [{cards}].
Cảm nhận người học: [{user_reflection if user_reflection else 'Người học chưa có cảm nhận sơ bộ, muốn lắng nghe phân tích từ sách trước'}].

Yêu cầu:
1. TUYỆT ĐỐI CHỈ trích xuất ý nghĩa các lá bài từ tài liệu đính kèm.
2. Tổng hợp ý nghĩa từng lá bài.
3. Liên kết năng lượng các lá bài để trả lời câu hỏi.
4. Đánh giá phần cảm nhận của người học và đặt 1 câu hỏi mở để họ chiêm nghiệm.

Hãy trình bày theo định dạng Markdown trang trọng, dễ tiếp thu và mang tính định hướng khai mở trực giác sâu sắc."""

    try:
        if deck_info.get("use_new_sdk"):
            from google import genai
            client = genai.Client(api_key=api_key_str)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[deck_info["file_ref"], prompt_text]
            )
            return response.text
        else:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=api_key_str)
            model = legacy_genai.GenerativeModel(model_name="gemini-1.5-flash")
            response = model.generate_content([deck_info["file_ref"], prompt_text])
            return response.text

    except Exception as e:
        raise Exception(f"Lỗi khi trao đổi với AI Mentor: {str(e)}")


# -------------------------------------------------------------
# 5. KHU VỰC CHÍNH (MAIN AREA - CHIA 2 TABS)
# -------------------------------------------------------------
tab1, tab2 = st.tabs(["📚 Quản lý Bộ bài & Tài liệu", "🔮 Không gian Trải bài (Reading Workspace)"])

# ----------------- TAB 1: QUẢN LÝ BỘ BÀI -----------------
with tab1:
    st.subheader("📁 Tải lên & Quản lý Guidebook Bộ bài")
    st.info("Hệ thống sẽ lưu file trên Gemini Files API để bạn có thể phân tích nhiều lần mà không cần upload lại.")

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        with st.form("upload_deck_form", clear_on_submit=False):
            deck_name = st.text_input("Tên bộ bài (*):", placeholder="Ví dụ: The Wild Unknown, Rider-Waite, Tea Leaf...")
            uploaded_file = st.file_uploader(
                "Tải lên file Guidebook (PDF hoặc TXT):",
                type=["pdf", "txt"],
                help="Chọn file sách hướng dẫn đi kèm bộ bài của bạn"
            )
            submit_upload = st.form_submit_button("📤 Nạp tài liệu lên hệ thống", use_container_width=True)

        if submit_upload:
            if not api_key:
                st.error("⚠️ Vui lòng nhập Gemini API Key ở cột Sidebar trước khi tải file.")
            elif not deck_name.strip():
                st.error("⚠️ Vui lòng nhập tên bộ bài.")
            elif uploaded_file is None:
                st.error("⚠️ Vui lòng chọn file PDF hoặc TXT.")
            else:
                with st.spinner("Đang xử lý và đăng ký tài liệu lên Gemini..."):
                    gemini_file, use_new_sdk = upload_guidebook_to_gemini(uploaded_file, deck_name.strip(), api_key)
                    if gemini_file:
                        st.session_state.decks[deck_name.strip()] = {
                            "name": deck_name.strip(),
                            "file_ref": gemini_file,
                            "file_name": uploaded_file.name,
                            "file_size": f"{uploaded_file.size / 1024:.1f} KB",
                            "use_new_sdk": use_new_sdk
                        }
                        st.success(f"🎉 Đã lưu bộ bài '{deck_name.strip()}' thành công! Hãy chuyển sang Tab 2 để trải bài.")

    with col2:
        st.markdown("### 🗃️ Danh sách bộ bài đã nạp")
        if not st.session_state.decks:
            st.caption("Chưa có bộ bài nào được tải lên. Hãy nạp file đầu tiên ở biểu mẫu bên trái.")
        else:
            for d_name, d_info in list(st.session_state.decks.items()):
                with st.container(border=True):
                    c_title, c_del = st.columns([4, 1])
                    with c_title:
                        st.markdown(f"**🃏 {d_name}**")
                        st.caption(f"File: `{d_info['file_name']}` ({d_info.get('file_size', 'N/A')}) | Trạng thái: ✅ Sẵn sàng")
                    with c_del:
                        if st.button("Xóa", key=f"del_{d_name}"):
                            del st.session_state.decks[d_name]
                            st.rerun()

# ----------------- TAB 2: KHÔNG GIAN TRẢI BÀI -----------------
with tab2:
    st.subheader("🕯️ Không gian Trải bài & Luận giải cùng Mentor")

    if not st.session_state.decks:
        st.warning("👉 Bạn chưa nạp bộ bài nào. Vui lòng sang **Tab 1: Quản lý Bộ bài & Tài liệu** để tải sách Guidebook trước.")
    else:
        deck_names_list = list(st.session_state.decks.keys())
        selected_deck_name = st.selectbox(
            "🃏 Chọn bộ bài đang sử dụng:",
            options=deck_names_list,
            index=0
        )

        col_q, col_c = st.columns([1, 1], gap="medium")

        with col_q:
            question_input = st.text_input(
                "❓ Câu hỏi / Vấn đề của bạn:",
                placeholder="Ví dụ: Định hướng công việc trong 3 tháng tới của tôi là gì?"
            )

        with col_c:
            st.caption("💡 Mẹo: Bạn có thể ghi rõ vị trí trải bài như Quá khứ, Hiện tại, Tương lai, Khuyên...")

        cards_input = st.text_area(
            "🎴 Các lá bài đã rút & Vị trí (*):",
            placeholder="Ví dụ:\n1. Quá khứ: The Fool\n2. Hiện tại: The Tower\n3. Tương lai: Ace of Pentacles",
            height=130
        )

        reflection_input = st.text_area(
            "💭 Cảm nhận / Luận giải sơ bộ của bạn (Không bắt buộc):",
            placeholder="Ghi lại những gì bạn cảm nhận ban đầu khi nhìn vào hình ảnh, màu sắc hoặc trực giác của bạn trước khi xem sách...",
            height=100
        )

        analyze_button = st.button("🔮 Phân tích cùng Mentor", type="primary", use_container_width=True)

        if analyze_button:
            if not api_key:
                st.error("⚠️ Vui lòng nhập Gemini API Key ở cột Sidebar!")
            elif not question_input.strip():
                st.error("⚠️ Vui lòng nhập câu hỏi hoặc vấn đề bạn đang băn khoăn.")
            elif not cards_input.strip():
                st.error("⚠️ Vui lòng nhập các lá bài bạn đã rút.")
            else:
                current_deck = st.session_state.decks[selected_deck_name]
                with st.spinner(f"Mentor đang tra cứu Guidebook của '{selected_deck_name}' và suy ngẫm cùng bạn..."):
                    try:
                        mentor_result = analyze_reading_with_mentor(
                            deck_info=current_deck,
                            question=question_input.strip(),
                            cards=cards_input.strip(),
                            user_reflection=reflection_input.strip(),
                            api_key_str=api_key
                        )

                        # Hiển thị kết quả luận giải
                        st.markdown("---")
                        st.subheader("📜 Luận giải từ Mentor")
                        st.markdown(mentor_result)

                        # Lưu vào lịch sử phiên làm việc
                        st.session_state.history.append({
                            "deck": selected_deck_name,
                            "question": question_input,
                            "cards": cards_input,
                            "reflection": reflection_input,
                            "result": mentor_result,
                            "timestamp": time.strftime("%H:%M - %d/%m/%Y")
                        })

                    except Exception as e:
                        st.error(f"❌ Có lỗi xảy ra trong quá trình phân tích: {str(e)}")

        # Hiển thị lịch sử các lần trải bài gần nhất
        if st.session_state.history:
            st.markdown("---")
            with st.expander("🕰️ Lịch sử các lần luận giải gần đây", expanded=False):
                for idx, item in enumerate(reversed(st.session_state.history)):
                    st.markdown(f"**Lần #{len(st.session_state.history) - idx}** ({item['timestamp']}) - Bộ bài: *{item['deck']}*")
                    st.markdown(f"- **Câu hỏi:** {item['question']}")
                    st.markdown(f"- **Lá bài:** {item['cards']}")
                    if st.button("Xem lại lời khuyên", key=f"hist_btn_{idx}"):
                        st.markdown(item["result"])
                    st.markdown("---")
