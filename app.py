import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
from prompts import ROAST_PROMPT, REWRITE_PROMPT, COVER_LETTER_PROMPT
import hashlib

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
        st.error(f"Error reading PDF: {str(e)}")
        return None


def get_gemini_response(prompt_text, system_instruction=None):
    """Helper to call Gemini API."""
    try:
        # Use a standard stable model
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        st.error(f"Error calling Gemini: {str(e)}")
        return None

def generate_roast(resume_text):
    """Generate brutal resume roast using Gemini."""
    system_instruction = "You are a brutally honest resume critic with dark humor."
    prompt = ROAST_PROMPT.format(resume_text=resume_text)
    return get_gemini_response(prompt, system_instruction=system_instruction)


def generate_rewrite(resume_text):
    """Generate optimized resume rewrite."""
    system_instruction = "You are an elite resume writer and career coach."
    prompt = REWRITE_PROMPT.format(resume_text=resume_text)
    return get_gemini_response(prompt, system_instruction=system_instruction)


def generate_cover_letter(resume_text):
    """Generate cover letter template."""
    system_instruction = "You are an elite career coach and cover letter expert."
    prompt = COVER_LETTER_PROMPT.format(resume_text=resume_text)
    return get_gemini_response(prompt, system_instruction=system_instruction)


def create_session_id(resume_text):
    """Create unique session ID from resume content."""
    return hashlib.md5(resume_text.encode()).hexdigest()[:12]


# Initialize session state
if "roast" not in st.session_state:
    st.session_state.roast = None
if "resume_text" not in st.session_state:
    st.session_state.resume_text = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None

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
    # Extract text
    with st.spinner("Reading your resume..."):
        resume_text = extract_text_from_pdf(uploaded_file)
    
    if resume_text:
        st.session_state.resume_text = resume_text
        st.session_state.session_id = create_session_id(resume_text)
        
        # Show extracted text preview
        with st.expander("📄 Preview extracted text"):
            st.text(resume_text[:1000] + "..." if len(resume_text) > 1000 else resume_text)
        
        # Generate roast button
        if st.button("🔥 ROAST MY RESUME", type="primary", use_container_width=True):
            with st.spinner("Preparing your emotional damage..."):
                roast = generate_roast(resume_text)
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
    if paid and st.session_state.resume_text:
        st.success("✅ Payment received! Generating your premium content...")
        
        with st.spinner("Creating your optimized resume..."):
            rewrite = generate_rewrite(st.session_state.resume_text)
        
        with st.spinner("Crafting your cover letter..."):
            cover_letter = generate_cover_letter(st.session_state.resume_text)
        
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
