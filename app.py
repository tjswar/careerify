import os
import re
import json
import datetime
from datetime import timedelta
import pandas as pd
import streamlit as st
import google.generativeai as genai
from ics import Calendar, Event
import PyPDF2
from docx import Document

# ──────────────────────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Career-iFy", page_icon="🧠", layout="wide")

# Get API key - try multiple methods
GEMINI_KEY = None

# Method 1: Try Streamlit secrets (for Streamlit Cloud)
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
except:
    pass

# Method 2: Try environment variable
if not GEMINI_KEY:
    GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Method 3: Try loading from .env file (for local development)
if not GEMINI_KEY:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        GEMINI_KEY = os.getenv("GEMINI_API_KEY")
    except:
        pass

# Check if we have a key
if not GEMINI_KEY:
    st.error("⚠️ GEMINI_API_KEY not found. Please add it to Streamlit Cloud Secrets or create a .env file locally.")
    st.info("""
    **For Streamlit Cloud:**
    1. Go to your app settings
    2. Click 'Secrets'
    3. Add: `GEMINI_API_KEY = "your_key_here"`
    
    **For Local Development:**
    Create a `.env` file with: `GEMINI_API_KEY=your_key_here`
    """)
    st.stop()

genai.configure(api_key=GEMINI_KEY)
MODEL_NAME = "gemini-2.5-flash"

# ──────────────────────────────────────────────────────────────
# Utility Functions
# ──────────────────────────────────────────────────────────────
def safe_gemini_text(resp) -> str:
    """Safely extract plain text from Gemini responses."""
    try:
        if getattr(resp, "candidates", None):
            cand = resp.candidates[0]
            parts = getattr(cand, "content", None)
            if parts and getattr(parts, "parts", None):
                text = "".join([p.text for p in parts.parts if hasattr(p, "text")])
                return text.strip()
    except Exception:
        return ""
    return ""

def clean_github_input(s: str) -> str:
    """Normalize GitHub username or URL."""
    s = (s or "").strip()
    return s.rstrip("/").split("/")[-1] if "github.com" in s else s

def fetch_github_repos(username: str) -> list[str]:
    """Fetch public GitHub repositories."""
    import requests
    url = f"https://api.github.com/users/{username}/repos"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Career-iFy-App"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return []
        return [repo.get("name", "") for repo in r.json() if isinstance(repo, dict)]
    except Exception:
        return []

def extract_text_from_pdf(file) -> str:
    """Extract text from uploaded PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file) -> str:
    """Extract text from uploaded DOCX file."""
    try:
        doc = Document(file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""

def extract_text_from_txt(file) -> str:
    """Extract text from uploaded TXT file."""
    try:
        return file.read().decode("utf-8").strip()
    except Exception as e:
        st.error(f"Error reading TXT: {e}")
        return ""

def extract_resume_text(uploaded_file) -> str:
    """Extract text from various resume formats."""
    if uploaded_file is None:
        return ""
    
    file_type = uploaded_file.type
    
    if file_type == "application/pdf":
        return extract_text_from_pdf(uploaded_file)
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(uploaded_file)
    elif file_type == "text/plain":
        return extract_text_from_txt(uploaded_file)
    else:
        st.error("Unsupported file format. Please upload PDF, DOCX, or TXT.")
        return ""

# ──────────────────────────────────────────────────────────────
# Gemini AI Logic
# ──────────────────────────────────────────────────────────────
def extract_skills_from_resume(resume_text: str) -> str:
    """Extract skills from resume using Gemini AI."""
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = (
        f"You are a career mentor AI. Analyze this resume and extract all technical skills, "
        f"programming languages, frameworks, tools, certifications, and soft skills mentioned.\n\n"
        f"Resume:\n{resume_text}\n\n"
        "Return only a comma-separated list of skills. Be comprehensive but concise."
    )
    resp = model.generate_content(prompt)
    return safe_gemini_text(resp)

def infer_skills_from_repos(repo_names: list[str]) -> str:
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = (
        f"You are a career mentor AI. Based on these GitHub project names:\n{repo_names}\n"
        "List the technical skills, frameworks, and tools the person is proficient in. "
        "Return only a comma-separated list."
    )
    resp = model.generate_content(prompt)
    return safe_gemini_text(resp)

def merge_skills(resume_skills: str, github_skills: str) -> str:
    """Merge and deduplicate skills from resume and GitHub."""
    all_skills = []
    
    if resume_skills:
        all_skills.extend([s.strip() for s in resume_skills.split(",")])
    if github_skills:
        all_skills.extend([s.strip() for s in github_skills.split(",")])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_skills = []
    for skill in all_skills:
        skill_lower = skill.lower()
        if skill_lower not in seen and skill:
            seen.add(skill_lower)
            unique_skills.append(skill)
    
    return ", ".join(unique_skills)

def get_job_market_context(job_title: str) -> str:
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = (
        f"Provide a concise overview of the current job market for the role '{job_title}'. "
        "Include:\n1. Top technical & soft skills in demand\n2. Common tools or certifications\n"
        "3. Industries or domains hiring for this role\nRespond in Markdown bullet points."
    )
    resp = model.generate_content(prompt)
    return safe_gemini_text(resp)

def generate_daily_plan(project_title: str, weeks: int, job_title: str) -> str:
    """Generate a detailed day-by-day learning plan for a project."""
    model = genai.GenerativeModel(MODEL_NAME)
    total_days = weeks * 7
    prompt = (
        f"You are a career mentor creating a detailed daily learning plan.\n\n"
        f"Project: {project_title}\n"
        f"Duration: {weeks} weeks ({total_days} days)\n"
        f"Target Role: {job_title}\n\n"
        f"Create a day-by-day breakdown with specific tasks. Use EXACTLY this format:\n\n"
        f"**Day 1:** [Specific actionable task]\n\n"
        f"**Day 2:** [Specific actionable task]\n\n"
        f"**Day 3:** [Specific actionable task]\n\n"
        f"And so on...\n\n"
        f"IMPORTANT FORMATTING RULES:\n"
        f"- Each day MUST be on its own line with double line breaks\n"
        f"- Use **Day X:** format (bold with markdown)\n"
        f"- Keep each task to 1-2 sentences maximum\n"
        f"- DO NOT write paragraphs - one task per day per line\n"
        f"- Include empty line between each day\n\n"
        f"Guidelines for content:\n"
        f"- Include setup, learning, implementation, and review phases\n"
        f"- Make tasks concrete and actionable (e.g., 'Set up React project and install dependencies')\n"
        f"- Every 7th day should be 'Review progress, consolidate learnings, and rest'\n"
        f"- Progress from basics to advanced concepts\n"
        f"- End with a deliverable or portfolio addition\n"
        f"- Be realistic about what can be done each day (2-3 hours of focused work)\n\n"
        f"Generate exactly {total_days} days. Start now:"
    )
    resp = model.generate_content(prompt)
    return safe_gemini_text(resp)

def compare_skills_and_suggest_projects(skills: str, job_title: str, market_data: str) -> str:
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = (
        f"My current skills: {skills}\n\nJob market overview for {job_title}:\n{market_data}\n\n"
        "Compare my skills with job market requirements and return three clear sections:\n"
        "### Matched Skills\n- ...\n\n"
        "### Missing Skills\n- ...\n\n"
        "### Suggested Projects\n"
        "Provide exactly **3** unique and practical projects aligned with the missing skills. "
        "Use this consistent format:\n"
        "1. Project Title — one-line description (skill learned)\n"
        "2. ...\n3. ...\n"
        "Make sure each title and description are on the same line."
    )
    resp = model.generate_content(prompt)
    return safe_gemini_text(resp)
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = (
        f"My current skills: {skills}\n\nJob market overview for {job_title}:\n{market_data}\n\n"
        "Compare my skills with job market requirements and return three clear sections:\n"
        "### Matched Skills\n- ...\n\n"
        "### Missing Skills\n- ...\n\n"
        "### Suggested Projects\n"
        "Provide exactly **3** unique and practical projects aligned with the missing skills. "
        "Use this consistent format:\n"
        "1. Project Title — one-line description (skill learned)\n"
        "2. ...\n3. ...\n"
        "Make sure each title and description are on the same line."
    )
    resp = model.generate_content(prompt)
    return safe_gemini_text(resp)

# ──────────────────────────────────────────────────────────────
# Streamlit App
# ──────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align: center;'>🧠 Career-iFy: AI-Powered Career Planner</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Analyze your skills from resume + GitHub and get a personalized learning roadmap</p>", unsafe_allow_html=True)

st.markdown("---")

# ──────────────────────────────────────────────────────────────
# Input Section
# ──────────────────────────────────────────────────────────────
st.markdown("## 📋 Step 1: Provide Your Information")

# Info cards explaining options
st.markdown("### ℹ️ How It Works")
col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.info("""
    **📄 Resume Only**
    - Extracts skills from your resume
    - Analyzes your experience & certifications
    - Best for: Career changers, traditional backgrounds
    """)

with col_info2:
    st.success("""
    **🐙 GitHub Only**
    - Analyzes your repositories
    - Infers practical coding skills
    - Best for: Self-taught developers, bootcamp grads
    """)

with col_info3:
    st.warning("""
    **🚀 Resume + GitHub (Recommended)**
    - Complete skill analysis
    - Professional + practical skills
    - Best for: Most comprehensive recommendations
    """)

st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📄 Upload Resume (Optional)")
    uploaded_resume = st.file_uploader(
        "Upload your resume (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        help="Upload your resume for comprehensive skill analysis"
    )
    
with col2:
    st.markdown("### 🐙 GitHub Profile (Optional)")
    gh_input = st.text_input(
        "GitHub username or profile URL",
        placeholder="e.g., octocat",
        help="We'll analyze your public repositories"
    )

st.markdown("### 🎯 Target Job Role (Required)")
job_title = st.text_input(
    "What role are you targeting?",
    placeholder="e.g., Data Scientist, Full Stack Developer, ML Engineer",
    help="Be specific about your target role"
)

st.markdown("---")

# ──────────────────────────────────────────────────────────────
# Analysis Section
# ──────────────────────────────────────────────────────────────
if st.button("🚀 Analyze My Career Path", type="primary", use_container_width=True):
    if not job_title:
        st.warning("⚠️ Please enter your target job role to continue.")
        st.stop()
    
    if not uploaded_resume and not gh_input:
        st.warning("⚠️ Please provide at least a resume OR GitHub profile to analyze.")
        st.stop()

    resume_skills = ""
    github_skills = ""
    repos = []
    
    # Determine analysis mode
    analysis_mode = ""
    if uploaded_resume and gh_input:
        analysis_mode = "📊 **Analysis Mode:** Resume + GitHub (Comprehensive)"
        st.info(analysis_mode)
    elif uploaded_resume:
        analysis_mode = "📊 **Analysis Mode:** Resume Only (Professional Skills)"
        st.info(analysis_mode)
    elif gh_input:
        analysis_mode = "📊 **Analysis Mode:** GitHub Only (Technical Skills)"
        st.info(analysis_mode)

    # Step 1 – Extract Resume Skills
    if uploaded_resume:
        with st.spinner("📄 Analyzing your resume..."):
            resume_text = extract_resume_text(uploaded_resume)
            if resume_text:
                resume_skills = extract_skills_from_resume(resume_text)
                st.success("✅ Resume analyzed successfully!")
            else:
                st.warning("⚠️ Could not extract text from resume.")

    # Step 2 – Fetch GitHub repos and infer skills
    if gh_input:
        username = clean_github_input(gh_input)
        with st.spinner("🔍 Fetching your GitHub repositories..."):
            repos = fetch_github_repos(username)
        
        if repos:
            with st.spinner("🧠 Analyzing GitHub projects..."):
                github_skills = infer_skills_from_repos(repos)
            st.success(f"✅ Analyzed {len(repos)} GitHub repositories!")
        else:
            st.info("ℹ️ Could not fetch GitHub repositories. Continuing with resume analysis only...")

    # Step 3 – Merge Skills
    combined_skills = merge_skills(resume_skills, github_skills)
    
    if not combined_skills:
        st.error("❌ Could not extract skills from the provided sources. Please check your inputs and try again.")
        st.stop()

    # Step 4 – Job Market Trends
    with st.spinner("🌍 Analyzing job market trends..."):
        market_data = get_job_market_context(job_title)
    
    # Step 5 – Skill Comparison + Project Ideas
    with st.spinner("🤖 Generating personalized projects..."):
        report = compare_skills_and_suggest_projects(combined_skills, job_title, market_data)
    
    # Store everything in session state
    st.session_state.analysis_complete = True
    st.session_state.resume_skills = resume_skills
    st.session_state.github_skills = github_skills
    st.session_state.combined_skills = combined_skills
    st.session_state.market_data = market_data
    st.session_state.report = report
    st.session_state.job_title = job_title
    st.session_state.analysis_mode = analysis_mode

# Display results if analysis is complete
if st.session_state.get("analysis_complete", False):
    # Display analysis mode
    if st.session_state.get("analysis_mode"):
        st.markdown("---")
        st.markdown(st.session_state.analysis_mode)
    
    # Display Skills Analysis
    st.markdown("---")
    st.markdown("## 💼 Your Current Skills")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Resume Skills", len(st.session_state.resume_skills.split(",")) if st.session_state.resume_skills else 0)
    with col2:
        st.metric("GitHub Skills", len(st.session_state.github_skills.split(",")) if st.session_state.github_skills else 0)
    with col3:
        st.metric("Total Unique Skills", len(st.session_state.combined_skills.split(",")))
    
    with st.expander("📝 View All Extracted Skills", expanded=True):
        st.success(st.session_state.combined_skills)
    
    st.markdown("---")
    st.markdown("## 📊 Job Market Snapshot")
    st.markdown(st.session_state.market_data)
    
    st.markdown("---")
    st.markdown("## 🔎 Skill Fit Report & Project Recommendations")
    st.markdown(st.session_state.report)

    # ──────────────────────────────────────────────────────────────
    # Learning Planner Section
    # ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🗓️ Create Your Learning Planner")

    # --- Improved Project Extraction Logic ---
    report = st.session_state.report
    pattern_variants = [
        r"\*\*Title\*\*[:\-]?\s*(.+)",
        r"###\s*Project\s*\d*[:\-]?\s*(.+)",
        r"\d+[.)-]\s*(.+)",
        r"[-•]\s*(.+)"
    ]

    project_titles = []
    for pat in pattern_variants:
        matches = re.findall(pat, report)
        for m in matches:
            cleaned = re.sub(r"[\*\_#\-•]+", "", m).strip()
            if cleaned and len(cleaned.split()) > 2:
                project_titles.append(cleaned)

    project_titles = list(dict.fromkeys(project_titles))[:3]

    # --- Display Planner ---
    if project_titles:
        # Initialize persistent states only once - use a hash to detect if projects changed
        project_hash = hash(tuple(project_titles))
        
        if "project_hash" not in st.session_state or st.session_state.project_hash != project_hash:
            st.session_state.project_hash = project_hash
            st.session_state.projects = project_titles
            st.session_state.weeks = {i: 2 for i in range(1, len(project_titles) + 1)}
            st.session_state.planner_generated = False

        st.write("### 📚 Suggested Projects for Planning")
        st.info("💡 Adjust the number of weeks for each project based on your availability and learning pace.")

        # Store weeks directly in session state without intermediate variable
        for i, title in enumerate(st.session_state.projects, 1):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text_input(f"Project {i}", value=title, key=f"title_{i}", disabled=True)
            with col2:
                # Use a unique key and store directly in session state
                weeks_key = f"weeks_input_{i}"
                st.session_state.weeks[i] = st.number_input(
                    "Weeks",
                    min_value=1,
                    max_value=12,
                    value=st.session_state.weeks.get(i, 2),
                    key=weeks_key,
                    help="Set how many weeks you plan to spend on this project"
                )

        st.markdown("---")

        # Stateful Planner Button
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📅 Generate Learning Planner", key="generate_planner_btn", type="primary", use_container_width=True):
                st.session_state.planner_generated = True
                st.session_state.daily_plan_generated = False  # Reset daily plan
        
        with col2:
            if st.session_state.get("planner_generated", False):
                if st.button("📋 Generate Detailed Daily Plan", key="generate_daily_plan_btn", type="secondary", use_container_width=True):
                    st.session_state.daily_plan_generated = True

        # Generate planner table if user clicked
        if st.session_state.get("planner_generated", False):
            st.markdown("### 📅 Your Personalized Learning Schedule")
            
            start_date = datetime.date.today()
            events = []
            total_weeks = 0
            
            for i, title in enumerate(st.session_state.projects, 1):
                weeks = int(st.session_state.weeks[i])
                total_weeks += weeks
                end_date = start_date + timedelta(weeks=weeks) - timedelta(days=1)
                events.append({
                    "Project": title,
                    "Start Date": start_date.strftime("%Y-%m-%d"),
                    "End Date": end_date.strftime("%Y-%m-%d"),
                    "Duration (Weeks)": weeks
                })
                start_date = end_date + timedelta(days=1)

            df = pd.DataFrame(events)
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Projects", len(events))
            with col2:
                st.metric("Total Duration", f"{total_weeks} weeks")
            with col3:
                completion_date = events[-1]["End Date"]
                st.metric("Expected Completion", completion_date)
            
            st.dataframe(df, use_container_width=True)

            # Generate detailed daily plan if requested
            if st.session_state.get("daily_plan_generated", False):
                st.markdown("---")
                st.markdown("### 📋 Detailed Day-by-Day Learning Plan")
                st.info("🤖 Generating personalized daily tasks for each project...")
                
                # Store daily plans in session state
                if "daily_plans" not in st.session_state:
                    st.session_state.daily_plans = {}
                
                all_daily_tasks = []
                current_date = datetime.date.today()
                
                for i, row in enumerate(events, 1):
                    project_title = row["Project"]
                    weeks = row["Duration (Weeks)"]
                    
                    # Generate daily plan for this project if not already done
                    if project_title not in st.session_state.daily_plans:
                        with st.spinner(f"📝 Creating daily plan for Project {i}..."):
                            daily_plan = generate_daily_plan(
                                project_title, 
                                weeks, 
                                st.session_state.job_title
                            )
                            st.session_state.daily_plans[project_title] = daily_plan
                    else:
                        daily_plan = st.session_state.daily_plans[project_title]
                    
                    # Display the plan for this project
                    with st.expander(f"📖 {project_title} - Daily Breakdown", expanded=(i==1)):
                        st.markdown(daily_plan)
                    
                    # Parse daily plan and create structured data
                    day_pattern = r"Day (\d+):\s*(.+)"
                    matches = re.findall(day_pattern, daily_plan)
                    
                    for day_num, task in matches:
                        task_date = current_date + timedelta(days=int(day_num) - 1)
                        all_daily_tasks.append({
                            "Date": task_date.strftime("%Y-%m-%d"),
                            "Day": f"Day {day_num}",
                            "Project": project_title,
                            "Task": task.strip()
                        })
                    
                    # Move to next project start date
                    current_date = current_date + timedelta(weeks=weeks)
                
                # Create comprehensive daily task dataframe
                if all_daily_tasks:
                    daily_df = pd.DataFrame(all_daily_tasks)
                    
                    st.markdown("### 📊 Complete Daily Task Schedule")
                    st.dataframe(daily_df, use_container_width=True, height=400)
                    
                    # Download options
                    st.markdown("### 💾 Download Your Detailed Planner")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Download summary planner as CSV
                        csv_summary = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "📊 Download Summary (CSV)",
                            csv_summary,
                            "career_planner_summary.csv",
                            "text/csv",
                            key="download_csv_summary",
                            use_container_width=True
                        )
                    
                    with col2:
                        # Download detailed daily plan as CSV
                        csv_detailed = daily_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "📋 Download Daily Plan (CSV)",
                            csv_detailed,
                            "career_planner_detailed.csv",
                            "text/csv",
                            key="download_csv_detailed",
                            use_container_width=True
                        )
                    
                    with col3:
                        # Download as .ics calendar with daily tasks
                        cal = Calendar()
                        for _, task_row in daily_df.iterrows():
                            e = Event()
                            e.name = f"{task_row['Project']}: {task_row['Day']}"
                            e.begin = task_row['Date']
                            e.description = task_row['Task']
                            e.duration = timedelta(hours=2)  # Default 2 hour task
                            cal.events.add(e)
                        
                        st.download_button(
                            "📆 Download Calendar (.ics)",
                            str(cal),
                            "career_planner_daily.ics",
                            "text/calendar",
                            key="download_ics_daily",
                            use_container_width=True
                        )
                    
                    st.success("✅ Your detailed day-by-day planner is ready! Download and start learning! 🚀")
                else:
                    st.warning("⚠️ Could not parse daily tasks. Please try regenerating the plan.")
            
            elif not st.session_state.get("daily_plan_generated", False):
                st.info("💡 Click 'Generate Detailed Daily Plan' to get a day-by-day breakdown of tasks for each project!")
    else:
        st.info("💡 No project titles detected — try analyzing again for better project details.")

# Footer
st.markdown("---")

# Reset button
col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])
with col_reset2:
    if st.button("🔄 Reset & Start Fresh", key="reset_button", type="secondary", use_container_width=True):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ All data cleared! Refresh the page to start over.")
        st.rerun()

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 12px;'>"
    "Made with ❤️ using Streamlit and Google Gemini AI | "
    "© 2025 Career-iFy"
    "</p>",
    unsafe_allow_html=True
)