import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
from prompts import ROAST_PROMPT, REWRITE_PROMPT, COVER_LETTER_PROMPT
import hashlib
import tempfile

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY not found in .env file")
    st.stop()

genai.configure(api_key=api_key)
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK")

# Page config
st.set_page_config(
    page_title="Resume Roaster 🔥",
    page_icon="🔥",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .roast-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid #e94560;
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
    }
    .unlock-box {
        background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
        border: 2px solid #00d9ff;
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        filter: blur(5px);
        user-select: none;
    }
    .cta-button {
        background: linear-gradient(90deg, #e94560, #ff6b6b);
        color: white;
        padding: 15px 40px;
        border-radius: 30px;
        font-size: 18px;
        font-weight: bold;
        text-decoration: none;
        display: inline-block;
        margin: 20px 0;
    }
    .cta-button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 20px rgba(233, 69, 96, 0.4);
    }
</style>
""", unsafe_allow_html=True)


def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF."""
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        return None


import time

def get_gemini_response(content, system_instruction=None):
    """Helper to call Gemini API. content can be text or a list [file_ref, prompt]."""
    # Use a standard stable model with better free tier limits
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
    
    # Retry logic for 429 errors
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(content)
            return response.text
        except Exception as e:
            if "429" in str(e):
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                else:
                    st.error(f"⏳ Use Limit Exceeded. Please wait a minute and try again. (Quota exhausted)")
                    return None
            else:
                st.error(f"Error calling Gemini: {str(e)}")
                return None

def generate_roast(input_data, is_scanned=False):
    """Generate brutal resume roast using Gemini."""
    system_instruction = "You are a brutally honest resume critic with dark humor. Do not hold back."
    
    if is_scanned:
        # input_data is the file object from genai
        prompt = ROAST_PROMPT.replace("{resume_text}", "The resume is attached as a file.")
        return get_gemini_response([input_data, prompt], system_instruction=system_instruction)
    else:
        # input_data is text
        prompt = ROAST_PROMPT.format(resume_text=input_data)
        return get_gemini_response(prompt, system_instruction=system_instruction)


def generate_rewrite(input_data, is_scanned=False):
    """Generate optimized resume rewrite."""
    system_instruction = "You are an elite resume writer and career coach."
    
    if is_scanned:
        prompt = REWRITE_PROMPT.replace("{resume_text}", "The resume is attached as a file.")
        return get_gemini_response([input_data, prompt], system_instruction=system_instruction)
    else:
        prompt = REWRITE_PROMPT.format(resume_text=input_data)
        return get_gemini_response(prompt, system_instruction=system_instruction)


def generate_cover_letter(input_data, is_scanned=False):
    """Generate cover letter template."""
    system_instruction = "You are an elite career coach and cover letter expert."
    
    if is_scanned:
        prompt = COVER_LETTER_PROMPT.replace("{resume_text}", "The resume is attached as a file.")
        return get_gemini_response([input_data, prompt], system_instruction=system_instruction)
    else:
        prompt = COVER_LETTER_PROMPT.format(resume_text=input_data)
        return get_gemini_response(prompt, system_instruction=system_instruction)


def create_session_id(content):
    """Create unique session ID from resume content."""
    return hashlib.md5(str(content).encode()).hexdigest()[:12]


# Initialize session state
if "roast" not in st.session_state:
    st.session_state.roast = None
if "resume_content" not in st.session_state:
    st.session_state.resume_content = None
if "is_scanned" not in st.session_state:
    st.session_state.is_scanned = False
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "gemini_file" not in st.session_state:
    st.session_state.gemini_file = None

# Check for payment callback
query_params = st.query_params
paid = query_params.get("paid", "false") == "true"

# Header
st.title("🔥 Resume Roaster")
st.subheader("Get brutally honest feedback on your resume")
st.markdown("*Upload your resume. Get roasted. Get hired.*")

st.divider()

# File upload
uploaded_file = st.file_uploader(
    "Drop your resume here (PDF only)",
    type=["pdf"],
    help="Maximum file size: 5MB"
)

if uploaded_file is not None:
    # Logic to handle file change or first load
    # We use a session state check to avoid re-processing on button clicks unless file changed
    
    # Save to temp file strictly for potential upload
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    # Try text extraction first (faster/cheaper)
    extracted_text = extract_text_from_pdf(uploaded_file)
    
    # Store in session state
    if extracted_text and len(extracted_text) > 50: # Threshold for valid text
        st.session_state.resume_content = extracted_text
        st.session_state.is_scanned = False
        st.session_state.session_id = create_session_id(extracted_text)
        preview_text = extracted_text[:1000] + "..."
    else:
        # Fallback to Vision
        st.session_state.is_scanned = True
        st.session_state.session_id = create_session_id(uploaded_file.name) # Use filename for ID if scanned
        
        # Upload to Gemini if not already uploaded
        if not st.session_state.gemini_file or st.session_state.gemini_file.display_name != uploaded_file.name:
            with st.spinner("Scanned PDF detected! Uploading to Gemini Vision..."):
                try:
                    upload = genai.upload_file(tmp_file_path, mime_type="application/pdf")
                    st.session_state.gemini_file = upload
                    st.session_state.resume_content = upload
                except Exception as e:
                    st.error(f"Failed to upload file to Gemini: {e}")
        
        preview_text = "⚠️ Text extraction failed. Using Gemini Vision to read scanned PDF."

    # Cleanup temp file
    try:
        os.remove(tmp_file_path)
    except:
        pass
        
    # UI
    if st.session_state.resume_content:
        with st.expander("📄 Resume Status"):
            st.text(preview_text)
        
        # Generate roast button
        if st.button("🔥 ROAST MY RESUME", type="primary", use_container_width=True):
            with st.spinner("Preparing your emotional damage..."):
                roast = generate_roast(st.session_state.resume_content, st.session_state.is_scanned)
                if roast:
                    st.session_state.roast = roast

# Display roast if available
if st.session_state.roast:
    st.markdown("### 💀 The Verdict Is In...")
    st.markdown(f"""
    <div class="roast-box">
        {st.session_state.roast}
    </div>
    """, unsafe_allow_html=True)
    
    # Share buttons
    col1, col2 = st.columns(2)
    with col1:
        st.button("📸 Screenshot & Share", disabled=True)
    with col2:
        st.button("🔄 Roast Again", on_click=lambda: st.session_state.update(roast=None))
    
    st.divider()
    
    # The Paywall Section
    st.markdown("### 🚀 Ready to Actually Get Hired?")
    
    # Check if paid
    if paid and st.session_state.resume_content:
        st.success("✅ Payment received! Generating your premium content...")
        
        with st.spinner("Creating your optimized resume..."):
            rewrite = generate_rewrite(st.session_state.resume_content, st.session_state.is_scanned)
        
        with st.spinner("Crafting your cover letter..."):
            cover_letter = generate_cover_letter(st.session_state.resume_content, st.session_state.is_scanned)
        
        if rewrite:
            st.markdown("### ✨ Your Optimized Resume")
            st.markdown(rewrite)
            st.download_button(
                "📥 Download Resume",
                rewrite,
                file_name="optimized_resume.txt",
                mime="text/plain"
            )
        
        if cover_letter:
            st.markdown("### 📝 Your Cover Letter Template")
            st.markdown(cover_letter)
            st.download_button(
                "📥 Download Cover Letter",
                cover_letter,
                file_name="cover_letter.txt",
                mime="text/plain"
            )
        
        st.balloons()
        
    else:
        # Show blurred preview
        st.markdown("""
        <div class="unlock-box">
            <h4>🎯 Your ATS-Optimized Resume</h4>
            <p>Professional summary that grabs attention...</p>
            <p>• Quantified achievements with real metrics...</p>
            <p>• Action verbs that demonstrate leadership...</p>
            <p>• Keywords optimized for applicant tracking...</p>
            <br>
            <h4>📝 Custom Cover Letter Template</h4>
            <p>Personalized opening hook...</p>
            <p>Achievement highlights...</p>
            <p>Confident closing...</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### Unlock your transformation for just $19")
        
        # Create payment link with session ID
        if STRIPE_PAYMENT_LINK:
            payment_url = f"{STRIPE_PAYMENT_LINK}?client_reference_id={st.session_state.session_id}"
            
            st.markdown(f"""
            <a href="{payment_url}" target="_blank" class="cta-button">
                💳 Unlock Rewrite + Cover Letter - $19
            </a>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            ✅ Instant delivery  
            ✅ ATS-optimized format  
            ✅ Custom cover letter template  
            ✅ 100% satisfaction guarantee
            """)
        else:
             st.warning("Stripe Payment Link not configured in .env")

# Footer
st.divider()
st.markdown("""
<center>
    <small>Built with 🔥 and sleep deprivation</small>
</center>
""", unsafe_allow_html=True)
