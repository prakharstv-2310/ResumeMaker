# ResumeMaker — AI Resume Builder 🚀

> UI redesigned by **Prakhar Srivastava**

ResumeMaker is a modern, high-fidelity web application built with Python Flask, MongoDB, and the Google Gemini API. It features a premium, responsive glassmorphic UI and empowers users to construct, organize, and instantly export professional resume profiles into print-ready A4 PDF documents.

---

## ✨ Features

*   **Premium Glassmorphic Design:** Sleek typography (Outfit & Inter), harmony-focused color palettes, subtle micro-interactions, responsive headers with user dropdown menus, and floating animated visual blobs.
*   **Gemini AI Summary Writer:** Generates custom, professional summaries tailored to your target role, key skills, and work experience using the Google Gemini API.
*   **Dynamic ATS Match Analysis:** Paste a target Job Description and use Gemini to scan your resume alignment in real-time. It returns a dynamic match score (0-100%), color-coded grading, matched keywords/skills, missing requirements, and actionable feedback.
*   **Secure Authentication System:** Session-based user sign-up and login with password cryptographic hashing via `werkzeug.security`.
*   **Interactive Dynamic Builder:** Add multiple education milestones, career experiences, and custom sections on the fly with a dynamic client-side DOM injector.
*   **Direct PDF Engine:** Export clean, perfectly styled, and A4 print-optimized documents directly to local storage using `html2pdf.js`.

---

## 🛠️ Tech Stack

*   **Backend:** Python 3.x, Flask (v3.0.0), Gunicorn (production server)
*   **AI Engine:** Google GenAI SDK (`google-genai`)
*   **Database:** MongoDB (using `pymongo` driver with SSL trust via `certifi`)
*   **Frontend:** Semantic HTML5, Vanilla JavaScript, and Custom CSS

---

## 📂 Folder Structure

```text
resume-maker/
├── app.py                  # Core Flask controller & API routes
├── requirements.txt        # Backend dependencies
├── static/
│   ├── css/
│   │   ├── index.css       # Home page styles
│   │   ├── auth.css        # Authentication layout styles
│   │   ├── dashboard.css   # Dynamic builder styles
│   │   ├── dropdown.css    # Header user profile dropdown styles
│   │   └── resume.css      # Print & digital A4 resume document styling
│   └── js/
│       ├── auth.js         # Slide-switching container behaviors
│       └── dropdown.js     # User profile dropdown click handlers
└── templates/
    ├── index.html          # Landing page view
    ├── auth.html           # Dual signup/login view
    ├── dashboard.html      # Interactive resume form & builder view
    ├── admin.html          # Admin management dashboard view
    ├── my_resumes.html     # User saved resumes management view
    ├── profile.html        # Account profile settings view
    └── resume.html         # Live print preview and export engine view
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have the following installed on your system:
*   [Python 3.8+](https://www.python.org/downloads/)
*   [MongoDB Community Server](https://www.mongodb.com/docs/manual/administration/install-community/) (running locally on standard port `27017`)
*   A [Google Gemini API Key](https://ai.google.dev/) (for AI features)

### 2. Installation
Clone or navigate to the repository directory and set up a virtual environment:

```bash
# Initialize a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file in the root directory (added to `.gitignore` to keep credentials secure) and define these variables:

```env
SECRET_KEY="your-random-session-secret-key"
MONGO_URI="mongodb://localhost:27017/" # Or your MongoDB Atlas connection string
GEMINI_API_KEY="your-google-gemini-api-key"
FLASK_DEBUG="True"
```

### 4. Running the Server
Make sure your MongoDB server is up and running. Then, execute:

```bash
python app.py
```

Open your browser and navigate to `http://127.0.0.1:5000` to start building your resumes!

---

## 🌐 Production Deployment

This application is ready for production hosting using **MongoDB Atlas** (cloud database) and **Render** (application server).

### Environment Variables for Render
When deploying on Render, configure the following **Environment Variables** under the Environment tab:

| Key | Value | Description |
| :--- | :--- | :--- |
| `MONGO_URI` | `mongodb+srv://...` | MongoDB Atlas cluster connection URI |
| `GEMINI_API_KEY` | `AQ.Ab...` | Google Gemini API Key |
| `SECRET_KEY` | `[Random String]` | A secure random string for Flask session signing |
| `FLASK_DEBUG` | `False` | Disables Flask debug mode |

---

## 👤 Author

**Prakhar Srivastava** — author, UI design & front-end engineering.

---

## 📄 License
This project is open-source and available under the MIT License.
