# Attend-X: Smart Face Recognition Attendance System

Attend-X is a modern, responsive web application that automates employee attendance tracking using facial recognition technology. Built with Python, Flask, and OpenCV, it provides a secure and seamless way to register employees, mark their attendance, and manage records via an Admin Dashboard.

## 🚀 Features

- **Face Registration:** Easily register new employees by capturing their facial encodings using a webcam.
- **Automated Attendance:** Mark attendance seamlessly. The system verifies the employee's unique ID and matches their face in real-time.
- **Admin Dashboard:** Secure manager dashboard to view real-time statistics (Total Employees, Present, Late, Absent).
- **Responsive UI:** A beautiful, modern, and fully responsive user interface that works perfectly on laptops, tablets, and mobile devices.
- **Data Export:** Export attendance records easily.

## 🛠️ Tech Stack

- **Backend:** Python, Flask, Pandas
- **Computer Vision:** OpenCV, dlib, `face_recognition`
- **Frontend:** HTML5, Vanilla CSS (Custom Design System), JavaScript
- **AI Integration:** Google Generative AI (Gemini)

## 💻 Local Setup Instructions

### Prerequisites
Make sure you have Python 3.8+ installed. You will also need `cmake` installed on your system to build the `dlib` library.

### 1. Clone the repository
```bash
git clone https://github.com/your-username/Facial-Recognition-Attendance-System.git
cd Facial-Recognition-Attendance-System
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python web_app.py
```
Open your browser and navigate to `http://localhost:5000`

## ☁️ Deployment (Render via Docker)

This application is ready to be deployed on platforms like Render using Docker, which is the most reliable way to deploy `face_recognition` and `dlib` without OS-level dependency issues.

1. Create a new Web Service on Render.
2. Connect this GitHub repository.
3. Select **Docker** as the environment.
4. Deploy! Render will automatically use the provided `Dockerfile` to install `cmake`, build the environment, and run the app via Gunicorn.

## ⚠️ Security Note
If making this repository public, ensure you do not commit any sensitive API keys or passwords directly in `config.py`. Use Environment Variables (`os.environ`) for production.

---
*Built with ❤️ for secure and smart attendance management.*
