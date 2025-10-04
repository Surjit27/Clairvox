import streamlit as st
import pandas as pd
import os
import time
from backend.retriever import fetch_wikipedia_summary
from backend.synth import extract_claims_from_text
from backend.verifier import analyze_claim
from backend.utils import LOGO_SVG

# Safe imports for file parsing
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    import docx
except ImportError:
    docx = None

# --- Page Configuration ---
st.set_page_config(
    page_title="Clairvox",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- UI Setup ---
st.markdown(
    """
    <style>
    .block-container {max-width: 1100px; padding-top: 2.5rem;}
    .hero {display:flex; align-items:center; gap:14px; margin-bottom: 0.5rem; justify-content:center;}
    .hero h1 {margin: 0; font-size: 2rem; text-align:center;}
    .hero-sub {opacity: 0.8; margin-bottom: 1.0rem; text-align:center;}
    .search-help {margin: 0.5rem auto 1.0rem; padding: 10px 14px; border-radius: 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); text-align:center;}

    /* Main Input Box Container */
    .input-container {
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        background-color: rgba(30, 32, 43, 0.5); /* Slightly different background */
        margin-bottom: 1.5rem;
    }

    /* Section Headers (e.g., "1. State Your Core Question") */
    .section-header {
        font-weight: 600;
        color: #CDD6F4; /* A lighter, less prominent color */
        margin-bottom: 0.8rem;
        font-size: 1.1rem;
    }

    /* Styling for the file uploader to make it a 'drop zone' */
    .stFileUploader {
        border: 2px dashed rgba(255, 255, 255, 0.15);
        background-color: rgba(255, 255, 255, 0.04);
        padding: 25px 20px;
        border-radius: 12px;
        text-align: center;
    }
    .stFileUploader label {
        font-weight: 600 !important;
    }

    /* The 'OR' divider */
    .or-divider {
        text-align: center;
        margin-top: 45px; /* Aligns vertically with inputs */
        font-weight: 600;
        color: rgba(255, 255, 255, 0.4);
    }
    
    .stTextInput>div>div>input {height: 46px; border-radius: 12px;}
    .claim-card {border:1px solid rgba(255,255,255,0.1); border-left: 4px solid var(--accent, #5b9bd5); padding: 20px; border-radius: 12px; background: rgba(255,255,255,0.03); margin: 16px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);}
    .claim-card h3 {margin: 0 0 12px; font-size: 1.2rem; font-weight: 600; line-height: 1.4;}
    .claim-meta {display: flex; align-items: center; gap: 20px; margin: 12px 0; flex-wrap: wrap;}
    .confidence-badge {padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.9rem;}
    .confidence-high {background: rgba(48, 164, 108, 0.2); color: #30a46c; border: 1px solid rgba(48, 164, 108, 0.3);}
    .confidence-medium {background: rgba(230, 167, 0, 0.2); color: #e6a700; border: 1px solid rgba(230, 167, 0, 0.3);}
    .confidence-low {background: rgba(229, 72, 77, 0.2); color: #e5484d; border: 1px solid rgba(229, 72, 77, 0.3);}
    .classification-badge {padding: 6px 12px; border-radius: 20px; font-weight: 500; font-size: 0.85rem; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);}
    .evidence-summary {margin: 12px 0; padding: 12px; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);}
    .evidence-item {padding: 12px; margin: 8px 0; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid rgba(74, 144, 226, 0.5);}
    .evidence-title {font-weight: 600; margin-bottom: 4px; color: #CDD6F4;}
    .evidence-meta {font-size: 0.85rem; opacity: 0.8; margin-bottom: 6px;}
    .evidence-excerpt {font-size: 0.9rem; opacity: 0.9; line-height: 1.4;}
    .expand-button {background: rgba(74, 144, 226, 0.1); border: 1px solid rgba(74, 144, 226, 0.3); color: #4A90E2; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 0.9rem; transition: all 0.2s;}
    .expand-button:hover {background: rgba(74, 144, 226, 0.2);}
    .provenance-panel {background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 16px; margin: 16px 0;}
    .source-table {width: 100%; border-collapse: collapse; margin: 12px 0;}
    .source-table th, .source-table td {padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);}
    .source-table th {font-weight: 600; background: rgba(255,255,255,0.05);}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Custom button style ---
st.markdown(
    """
    <style>
    div.stButton > button:first-child {
        background-color: #14B8A6 !important;
        color: white !important;
        border-radius: 10px !important;
        height: 42px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #0D9488 !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Header ---
st.markdown(
    f"""
<div class='hero'>
{LOGO_SVG}
<div><h1>Clairvox</h1><div class='hero-sub'>Evidence-Backed AI Research Assistant</div></div>
</div>
<div class='search-help'>Enter your research question to get evidence-backed analysis.</div>
""",
    unsafe_allow_html=True,
)

# --- Start of the redesigned input box ---
# Step 1: Core Question
st.markdown("<div class='section-header'>Enter Your Research Question</div>", unsafe_allow_html=True)
typed_query = st.text_area(
    "Enter Your Research Question",
    placeholder="Type your research question here...",
    label_visibility="collapsed",
    height=115
)

st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

# Step 2: Supporting Material
st.markdown("<div class='section-header'>Add Supporting Material (Optional)</div>", unsafe_allow_html=True)

col1, col_divider, col2 = st.columns([5, 1, 5])
with col1:
    uploaded_file = st.file_uploader(
        "Upload a file (TXT, PDF, DOCX)",
        type=["txt", "pdf", "docx"],
        help="Upload a document containing your research material.",
        label_visibility="visible"
    )
    
with col_divider:
    st.markdown("<div class='or-divider'>OR</div>", unsafe_allow_html=True)

with col2:
    link_input = st.text_input(
        "Paste a URL for context",
        placeholder="https://example.com/article",
    )

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

# Centered Verify Button
verify_clicked = False
_, col_center, _ = st.columns([2, 1.2, 2])
with col_center:
    verify_clicked = st.button("Analyze Question", use_container_width=True)


# --- Determine the final query content ---
query = typed_query.strip()
if uploaded_file:
    file_content = ""
    file_type = uploaded_file.type
    if file_type == "application/pdf" and PyPDF2:
        try:
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                file_content += page.extract_text() + "\n"
        except Exception as e:
            st.error(f"Error reading PDF file: {e}")
    elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"] and docx:
        try:
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                file_content += para.text + "\n"
        except Exception as e:
            st.error(f"Error reading DOCX file: {e}")
    elif file_type.startswith("text"):
        file_content = uploaded_file.getvalue().decode("utf-8")
    query += "\n" + file_content.strip()
if link_input:
    query += "\n" + link_input.strip()

# --- Main App Logic (THIS SECTION IS MODIFIED) ---
if 'results' not in st.session_state:
    st.session_state.results = []

if verify_clicked:
    if not query.strip():
        st.error("Please enter a query or upload a file/paste a link.")
    else:
        # Check if the user provided a long text block to be used as context
        if len(query) > 300:
            st.info("Using provided text as analysis context.")
            context = query
        else:
            with st.spinner("Retrieving context from academic databases..."):
                context = fetch_wikipedia_summary(query)
                if not context:
                    st.warning("Could not retrieve web context. Analyzing the query directly.")
                    context = query
                else:
                    with st.expander("Show Retrieved Context"):
                        st.markdown(context)

        # Extract and analyze claims
        with st.spinner("Extracting claims from your question..."):
            claims = extract_claims_from_text(context, n=8)
            if not claims:
                st.error("Could not extract any claims from the context. Try rephrasing your query.")
                st.stop()

        st.success(f"Extracted {len(claims)} claims. Analyzing evidence...")
        
        st.session_state.results = []
        progress_bar = st.progress(0, text="Analyzing evidence for each claim...")

        for i, claim in enumerate(claims):
            claim_text = claim['text']
            with st.spinner(f"Analyzing Claim {i+1}: '{claim_text}'"):
                analysis_result = analyze_claim(claim_text, original_query=query)
                st.session_state.results.append(analysis_result)
            progress_bar.progress((i + 1) / len(claims), text=f"Analyzing claim {i+1}/{len(claims)}")
        
        time.sleep(0.5)
        progress_bar.empty()


# --- Display Results ---
if st.session_state.results:
    st.markdown("---")
    st.header("Analyzed Claims", anchor=False)
    
    # Add Clairvox branding
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem; padding: 1rem; background: rgba(74, 144, 226, 0.1); border-radius: 12px; border: 1px solid rgba(74, 144, 226, 0.2);'>
        <h4 style='margin: 0; color: #4A90E2;'>🔎 Evidence-Backed Analysis Complete</h4>
        <p style='margin: 0.5rem 0 0; opacity: 0.8; font-size: 0.9rem;'>Transparent, reproducible results with source verification</p>
    </div>
    """, unsafe_allow_html=True)

    for i, result in enumerate(st.session_state.results):
        claim_text = result['claim']
        confidence = result['confidence']
        explanation = result['explanation']
        
        # Get Clairvox result if available
        clairvox_result = result.get('clairvox_result', {})
        classification = clairvox_result.get('classification', 'Unsupported')
        
        # Determine confidence badge class
        if confidence >= 70:
            confidence_class = "confidence-high"
        elif confidence >= 40:
            confidence_class = "confidence-medium"
        else:
            confidence_class = "confidence-low"
        
        # Show severity banner if needed
        severity_banner = None
        if classification == 'Fabricated':
            severity_banner = "🚨 FABRICATED TERMS DETECTED"
        elif classification == 'Physically Implausible':
            severity_banner = "⚠️ PHYSICALLY IMPLAUSIBLE"
        
        # Create claim card
        st.markdown(f"""
        <div class='claim-card'>
            <h3>{claim_text}</h3>
            <div class='claim-meta'>
                <div class='confidence-badge {confidence_class}'>Confidence: {confidence}%</div>
                <div class='classification-badge'>{classification}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Show severity banner if needed
        if severity_banner:
            banner_color = "#e5484d" if "FABRICATED" in severity_banner else "#f59e0b"
            banner_icon = "🚨" if "FABRICATED" in severity_banner else "⚠️"
            
            st.markdown(f"""
            <div style='background: {banner_color}; color: white; padding: 12px 16px; border-radius: 8px; margin: 12px 0; text-align: center; font-weight: 600;'>
                <div style='font-size: 1.1rem; margin-bottom: 4px;'>{banner_icon} {severity_banner}</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>This claim requires immediate attention</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Evidence summary (inline, 1-2 key snippets)
        if clairvox_result.get('drivers'):
            st.markdown("<div class='evidence-summary'>")
            st.markdown("**Evidence Summary:**")
            for driver in clairvox_result['drivers'][:2]:  # Show only first 2 drivers inline
                st.markdown(f"• {driver}")
            st.markdown("</div>")
        
        # Show fabricated terms if any
        if clairvox_result.get('fabricated_terms'):
            st.markdown("""
            <div style='background: rgba(229, 72, 77, 0.1); border: 1px solid rgba(229, 72, 77, 0.3); border-radius: 8px; padding: 12px; margin: 12px 0;'>
                <div style='color: #e5484d; font-weight: 600; margin-bottom: 8px;'>🚨 Fabricated Terms Detected</div>
            """, unsafe_allow_html=True)
            
            for term in clairvox_result['fabricated_terms']:
                st.markdown(f"""
                <div style='background: rgba(229, 72, 77, 0.2); padding: 6px 8px; border-radius: 4px; margin: 4px 0; font-family: monospace; display: inline-block;'>
                    <span style='color: #e5484d; font-weight: 600;'>⚠️</span> <code style='background: none; color: #e5484d; font-weight: 600;'>{term}</code>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>")
        
        # Explanation
        st.markdown(f"<div style='margin: 12px 0; opacity: 0.9; line-height: 1.5;'>{explanation}</div>", unsafe_allow_html=True)
        
        # Expandable evidence panel
        with st.expander("View Evidence & Details", expanded=False):
            if result.get('evidence'):
                st.markdown("**Supporting Sources:**")
                for j, evidence in enumerate(result['evidence'][:5]):  # Show top 5
                    title = evidence.get('title', 'No title')
                    authors = evidence.get('authors', 'Unknown authors')
                    venue = evidence.get('venue', 'Unknown venue')
                    date = evidence.get('date', 'Unknown date')
                    doi = evidence.get('doi', '')
                    url = evidence.get('url', '')
                    excerpt = evidence.get('excerpt', '')
                    
                    # Truncate excerpt
                    if len(excerpt) > 200:
                        excerpt = excerpt[:200] + "..."
                    
                    evidence_type = evidence.get('type', 'unknown')
                    type_emoji = {
                        'peer-reviewed': '📚',
                        'preprint': '📄',
                        'conference': '🎯',
                        'news': '📰'
                    }.get(evidence_type, '📄')
                    
                    st.markdown(f"""
                    <div class='evidence-item'>
                        <div class='evidence-title'>{type_emoji} {title}</div>
                        <div class='evidence-meta'>
                            <strong>Authors:</strong> {authors} | 
                            <strong>Venue:</strong> {venue} ({date}) | 
                            <strong>DOI:</strong> {doi if doi else 'N/A'}
                        </div>
                        <div class='evidence-excerpt'>{excerpt if excerpt else 'No excerpt available'}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No direct evidence found for this claim.")
            
            # Contradictions
            if clairvox_result.get('contradictions'):
                st.markdown("**Contradictory Evidence:**")
                for contradiction in clairvox_result['contradictions'][:3]:  # Show top 3
                    title = contradiction.get('title', 'Unknown')
                    excerpt = contradiction.get('excerpt', '')[:100] + "..." if len(contradiction.get('excerpt', '')) > 100 else contradiction.get('excerpt', '')
                    st.markdown(f"• **{title}** - {excerpt}")
            
            # Suggested corrections
            if clairvox_result.get('suggested_corrections'):
                st.markdown("**Suggested Corrections:**")
                st.info(clairvox_result['suggested_corrections'])
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Provenance panel (right side)
        st.markdown("""
        <div class='provenance-panel'>
            <h4 style='margin: 0 0 12px; color: #CDD6F4;'>🔍 Provenance & Sources</h4>
        """, unsafe_allow_html=True)
        
        # Database sources
        if result.get('evidence'):
            sources = {}
            for evidence in result['evidence']:
                source = evidence.get('source', 'Unknown')
                sources[source] = sources.get(source, 0) + 1
            
            st.markdown("**Sources by Database:**")
            for source, count in sources.items():
                st.markdown(f"• {source}: {count} results")
        
        # Query terms
        if result.get('evidence'):
            queries_used = set()
            for evidence in result['evidence']:
                query = evidence.get('query_used', '')
                if query:
                    queries_used.add(query)
            
            if queries_used:
                st.markdown("**Search Queries:**")
                for query in list(queries_used)[:3]:
                    st.markdown(f"• `{query}`")
        
        st.markdown("</div>")
        st.markdown("---")
    
    # Add reproducible results panel
    if st.session_state.results:
        st.markdown("---")
        st.header("📊 Analysis Summary", anchor=False)
        
        # Create summary data
        summary_data = []
        for i, result in enumerate(st.session_state.results):
            clairvox_result = result.get('clairvox_result', {})
            classification = clairvox_result.get('classification', 'Unsupported')
            confidence = result['confidence']
            
            # Count evidence types
            evidence = result.get('evidence', [])
            peer_reviewed_count = sum(1 for e in evidence if e.get('type') == 'peer-reviewed')
            preprint_count = sum(1 for e in evidence if e.get('type') == 'preprint')
            
            # Get top 3 sources
            top_sources = []
            for j, source in enumerate(evidence[:3]):
                top_sources.append({
                    'title': source.get('title', 'No title'),
                    'doi': source.get('doi', 'N/A'),
                    'venue': source.get('venue', 'Unknown'),
                    'type': source.get('type', 'unknown')
                })
            
            summary_data.append({
                'Claim': f"Claim {i+1}: {result['claim'][:100]}{'...' if len(result['claim']) > 100 else ''}",
                'Confidence Score': f"{confidence}/100",
                'Classification': classification,
                'Peer-Reviewed Sources': peer_reviewed_count,
                'Preprint Sources': preprint_count,
                'Total Evidence': len(evidence),
                'Contradictions': result.get('contradiction_count', 0),
                'Top Sources': top_sources
            })
        
        # Display summary table
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(
            df_summary[['Claim', 'Confidence Score', 'Classification', 'Peer-Reviewed Sources', 'Total Evidence', 'Contradictions']],
            use_container_width=True,
            hide_index=True
        )
        
        # Display detailed source information
        st.markdown("### 📚 Sources by Claim")
        for i, data in enumerate(summary_data):
            st.markdown(f"**Claim {i+1} - {data['Classification']}**")
            if data['Top Sources']:
                for j, source in enumerate(data['Top Sources']):
                    st.markdown(f"**{j+1}.** {source['title']} | DOI: {source['doi']} | Venue: {source['venue']} | Type: {source['type']}")
            else:
                st.markdown("No sources found")
            st.markdown("---")



