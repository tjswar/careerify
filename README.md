# 🧠 Career-iFy: AI-Powered Career Planner

An intelligent career planning tool that analyzes your skills from resume and GitHub, compares them with job market demands, and creates a personalized day-by-day learning roadmap.

## ✨ Features

- 📄 **Resume Analysis** - Extract skills from PDF, DOCX, or TXT resumes
- 🐙 **GitHub Integration** - Analyze your repositories for technical skills
- 🎯 **Job Market Insights** - Get current trends for your target role
- 🔍 **Skill Gap Analysis** - See what you have vs. what you need
- 📚 **Project Recommendations** - Get 3 personalized learning projects
- 🗓️ **Day-by-Day Planner** - Detailed daily tasks for each project
- 📊 **Export Options** - Download as CSV or Calendar (.ics)

## 🚀 Live Demo

[Visit Career-iFy](https://careerify.streamlit.app) 

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **AI**: Google Gemini 2.5 Flash
- **APIs**: GitHub REST API
- **Data Processing**: Pandas, PyPDF2, python-docx
- **Calendar**: ICS library

## 📋 Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get it here](https://makersuite.google.com/app/apikey))
- GitHub account (optional, for repository analysis)

## 🔧 Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/careerify.git
cd careerify
```

### 2. Create virtual environment
```bash
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.streamlit/secrets.toml` file:
```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
```

Or create a `config.py` file:
```python
import os

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "your_key_here")
```

### 5. Run the app
```bash
streamlit run app.py
```

## 🌐 Deploying to Streamlit Cloud

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/careerify.git
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository: `YOUR_USERNAME/careerify`
5. Main file path: `app.py`
6. Click "Advanced settings"
7. Add secrets:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key_here"
   ```
8. Click "Deploy"!

## 📖 How to Use

### Option 1: Resume Only
1. Upload your resume (PDF, DOCX, or TXT)
2. Enter target job role
3. Click "Analyze My Career Path"
4. Review skills and project recommendations
5. Generate your learning planner

### Option 2: GitHub Only
1. Enter your GitHub username
2. Enter target job role
3. Click "Analyze My Career Path"
4. Review skills from your repositories
5. Generate your learning planner

### Option 3: Resume + GitHub (Recommended)
1. Upload resume AND enter GitHub username
2. Enter target job role
3. Get comprehensive skill analysis
4. Generate detailed learning planner
5. Download CSV or Calendar

## 📸 Screenshots

*(Add screenshots of your app here)*

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Google Gemini AI for intelligent analysis
- Streamlit for the amazing framework
- GitHub API for repository data

## 📧 Contact

Sai Tejaswar Reddy Dalli

Project Link: [https://github.com/tjswar/careerify]

---

Made with ❤️ and AI
