import streamlit as st
from google import genai
from google.genai import types
import time
import tempfile
import os

# ==========================================
# CẤU HÌNH TRANG & FONT CHỮ (ROBOTO)
# ==========================================
st.set_page_config(page_title="Tarot & Oracle Mentor", page_icon="🔮", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"], .stApp, p, h1, h2, h3, h4, h5, h6, span, div, input, textarea, select, button {
        font-family: 'Roboto', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# KHỞI TẠO SESSION STATE
# ==========================================
if 'decks' not in st.session_state:
    st.session_state.decks = {} # Lưu {"Tên bộ bài": gemini_file_object}
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'client' not in st.session_state:
    st.session_state.client = None # Khởi tạo Client theo chuẩn SDK mới

# ==========================================
# GIAO DIỆN SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🔮 Cấu hình hệ thống")
    
    api_key_input = st.text_input("Nhập Gemini API Key của bạn:", type="password", value=st.session_state.api_key)
    if api_key_input:
        st.session_state.api_key = api_key_input
        try:
            # Khởi tạo Client theo thư viện google-genai mới
            st.session_state.client = genai.Client(api_key=st.session_state.api_key)
        except Exception as e:
            st.error(f"Lỗi khởi tạo kết nối: {str(e)}")
            
    st.divider()
    
    with st.expander("📖 Hướng dẫn sử dụng", expanded=True):
        st.markdown("""
        **Bước 1:** Nhập Gemini API Key để kích hoạt. \n
        **Bước 2:** Vào Tab **Quản lý Bộ bài**, tải lên Guidebook (PDF/TXT). \n
        **Bước 3:** Chuyển sang Tab **Không gian Trải bài**, chọn bộ bài và nhập bài đã rút. \n
        **Bước 4:** Bấm **Phân tích cùng Mentor** để nhận thông điệp.
        """)

# ==========================================
# GIAO DIỆN CHÍNH (MAIN AREA)
# ==========================================
st.title("Tarot & Oracle Mentor 🌟")
st.markdown("Hỗ trợ tự học đọc bài chuyên sâu dựa trên Guidebook của riêng bạn.")

tab1, tab2 = st.tabs(["📚 Quản lý Bộ bài & Tài liệu", "✨ Không gian Trải bài"])

# ------------------------------------------
# TAB 1: QUẢN LÝ BỘ BÀI VÀ TÀI LIỆU
# ------------------------------------------
with tab1:
    st.header("Tải lên Guidebook của bộ bài")
    
    with st.form("upload_deck_form"):
        deck_name = st.text_input("Tên bộ bài (Ví dụ: The Wild Unknown Tarot):")
        uploaded_file = st.file_uploader("Chọn file Guidebook (PDF, TXT):", type=['pdf', 'txt'])
        
        submit_upload = st.form_submit_button("Tải lên & Xử lý")
        
        if submit_upload:
            if not st.session_state.client:
                st.error("⚠️ Vui lòng nhập Gemini API Key hợp lệ ở thanh bên trái trước.")
            elif not deck_name or not uploaded_file:
                st.warning("⚠️ Vui lòng nhập tên bộ bài và chọn file đính kèm.")
            else:
                try:
                    with st.spinner(f"Đang tải lên và xử lý '{deck_name}'..."):
                        # Lưu file tạm thời
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name
                        
                        client = st.session_state.client
                        
                        # Upload file qua SDK mới (google-genai)
                        gemini_file = client.files.upload(
                            file=tmp_file_path, 
                            config={'display_name': deck_name}
                        )
                        
                        # Vòng lặp chờ file xử lý xong (ACTIVE)
                        while gemini_file.state.name == "PROCESSING":
                            time.sleep(2)
                            gemini_file = client.files.get(name=gemini_file.name)
                            
                        if gemini_file.state.name == "FAILED":
                            st.error("❌ Lỗi khi xử lý file trên hệ thống. Vui lòng thử lại.")
                        elif gemini_file.state.name == "ACTIVE":
                            st.session_state.decks[deck_name] = gemini_file
                            st.success(f"✅ Đã tải lên và xử lý thành công: **{deck_name}**")
                        
                        os.remove(tmp_file_path)
                        
                except Exception as e:
                    st.error(f"❌ Có lỗi xảy ra trong quá trình upload: {str(e)}")

    if st.session_state.decks:
        st.subheader("📋 Các bộ bài đã sẵn sàng:")
        for name in st.session_state.decks.keys():
            st.markdown(f"- 🃏 **{name}**")

# ------------------------------------------
# TAB 2: KHÔNG GIAN TRẢI BÀI
# ------------------------------------------
with tab2:
    st.header("Bắt đầu buổi đọc bài của bạn")
    
    if not st.session_state.decks:
        st.info("💡 Bạn chưa có bộ bài nào. Hãy tải lên Guidebook nhé.")
    else:
        selected_deck = st.selectbox("🔮 Chọn bộ bài đang sử dụng:", options=list(st.session_state.decks.keys()))
        
        question = st.text_input("❓ Câu hỏi / Vấn đề của bạn:")
        
        cards_drawn = st.text_area(
            "🃏 Các lá bài đã rút & Vị trí:", 
            placeholder="Ví dụ:\n1. Quá khứ: The Fool\n2. Hiện tại: The Magician\n3. Tương lai: The High Priestess",
            height=120
        )
        
        user_feelings = st.text_area(
            "✍️ Cảm nhận / Luận giải sơ bộ của bạn (Không bắt buộc):", 
            placeholder="Ghi lại cảm giác đầu tiên của bạn...",
            height=100
        )
        
        if st.button("✨ Phân tích cùng Mentor", type="primary"):
            if not st.session_state.client:
                st.error("⚠️ Client chưa được khởi tạo. Vui lòng nhập API Key.")
            elif not question or not cards_drawn:
                st.warning("⚠️ Vui lòng nhập câu hỏi và các lá bài đã rút.")
            else:
                try:
                    with st.spinner("Mentor đang đọc Guidebook và phân tích bài..."):
                        client = st.session_state.client
                        deck_file = st.session_state.decks[selected_deck]
                        
                        prompt = f"""
                        Bạn là một Mentor dạy đọc bài. File đính kèm là guidebook của bộ bài {selected_deck}.
                        Câu hỏi của người học: {question}.
                        Các lá bài rút được: {cards_drawn}.
                        Cảm nhận người học: {user_feelings if user_feelings else "Không có cảm nhận ban đầu."}.
                        Yêu cầu:
                        - TUYỆT ĐỐI CHỈ trích xuất ý nghĩa các lá bài từ tài liệu đính kèm.
                        - Tổng hợp ý nghĩa từng lá bài.
                        - Liên kết năng lượng các lá bài để trả lời câu hỏi.
                        - Đánh giá phần cảm nhận của người học và đặt 1 câu hỏi mở để họ chiêm nghiệm.
                        """
                        
                        # Gọi API theo chuẩn SDK mới của thư viện google-genai, dùng mô hình 3.8-flash
                        response = client.models.generate_content(
                            model='gemini-3.8-flash',
                            contents=[deck_file, prompt]
                        )
                        
                        st.subheader("💌 Lời khuyên từ Mentor:")
                        st.write(response.text)
                        
                except Exception as e:
                    st.error(f"❌ Có lỗi xảy ra trong quá trình phân tích: {str(e)}")
