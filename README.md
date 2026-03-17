# dayflow — Daily OS

> A full-stack personal productivity platform to manage your tasks, goals, schedule, notes, and calendar — all in one place.

---

## Features

- **Dashboard** — Live overview of tasks today, completion rate, active goals and upcoming events
- **Task Manager** — Create, complete and filter tasks by status and priority
- **Goal Tracker** — Set goals with target dates and track progress with visual progress rings
- **Schedule** — Plan your day with time blocking on a weekly timeline
- **Calendar** — Monthly calendar with event creation and email reminders
- **Notes** — Minimalist note-taking with live search
- **Profile** — Personal stats including task completion rate and goal progress
- **Email Reminders** — Get notified for calendar events and pinned tasks
- **JWT Authentication** — Secure login and registration
- **Fully Responsive** — Works on mobile, tablet and desktop

---

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| Django | Core web framework |
| Django REST Framework | RESTful API |
| djangorestframework-simplejwt | JWT Authentication |
| django-cors-headers | Cross-origin requests |
| SQLite | Database |
| Django Email Backend | Email reminders |

### Frontend
| Technology | Purpose |
|---|---|
| React.js 18 | UI framework |
| Tailwind CSS | Styling |
| React Router v6 | Client-side routing |
| Axios | API requests |
| Vite | Build tool |

---

## Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

---

### Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/fadi4programing-lab/dayflow.git
cd dayflow

# 2. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file and add your settings
SECRET_KEY=your_secret_key
DEBUG=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_email_password

# 5. Run migrations
python manage.py migrate

# 6. Start the backend server
python manage.py runserver
Frontend Setup
# 1. Go to frontend folder
cd frontend

# 2. Install dependencies
npm install

# 3. Start the frontend
npm run dev
Now open your browser and go to http://localhost:5173 ✅

Author
Fadi — @fadi4programing-lab
Built with Django REST Framework & React.js
This project is open source and available under the MIT License.
