# Aino - Business Advisory Service 2.0

Our solution for the City of Espoo challenge at Junction 2025. A ChatGPT-style chatbot interface that guides entrepreneurs through completing their business information form via conversational dialogue, with real-time progress tracking and multi-language support.

### Challenge Background

Addresses the Business Advisory Service 2.0 challenge: creating a digital service to help entrepreneurs prepare for advisory meetings, especially international entrepreneurs lacking knowledge of Finnish business procedures. Our chatbot enables better preparation and clearer communication before live meetings.

### Web Application

We provide a Flask web interface for seamless business form completion:

**Web Application Features:**

- **Customized AI assistant** with specialized knowledge of business documents and resources
- **ChatGPT-style chat interface** for natural, conversational form completion
- **Visual progress tracker** showing completion status of each form step
- **Real-time validation** and guidance throughout the process
- **Multi-language support** ready for international entrepreneurs
- **Responsive design** accessible on various devices


### Screenshots

#### First Steps
<img src="resources/screenshots/First Steps.png" alt="First Steps" width="700"><br>
The chatbot guides users through the initial form collection, gathering company name, preferred language, business sphere, education, experience, and location with real-time progress tracking.

#### Business Questions
<img src="resources/screenshots/Questions.png" alt="Questions" width="700"><br>
Multi-section business plan questionnaire with core and optional questions, showing progress across sections and the points-based tier system.

#### Data Export
<img src="resources/screenshots/Data Export.png" alt="Data Export" width="700"><br>
Download the completed business plan as a DOCX document or receive it via email with all collected information formatted and ready for advisory meetings.

### Demo Video

Watch the full demo video showcasing Aino in action:

[![Demo Video](https://img.youtube.com/vi/pGLmcPnXBgw/maxresdefault.jpg)](https://www.youtube.com/watch?v=pGLmcPnXBgw)

[Watch on YouTube](https://www.youtube.com/watch?v=pGLmcPnXBgw)

### Project Presentation

View the project presentation: [Aino. Business Advisory Service 2.0.pdf](resources/presentation/Aino.%20Business%20Advisory%20Service%202.0.pdf)

### Quick Start

```bash
python app.py
```

Access at `http://127.0.0.1:5001`

The web app guides users through:
- **Initial Form**: Company name, preferred language, business sphere, education, experience, location
- **Business Plan Questions**: Multi-section business plan with core and optional questions, with validation and retry logic
- **Progress Tracking**: Visual progress with points-based tier system
- **Document Generation**: Automatic DOCX business plan generation
- **Email Reports**: Automatic email delivery with business plan attachment when form is complete (email extracted from conversation)
- **Voice Features**: Text-to-speech and audio transcription support

### Form Data Structure

The system collects structured business information through conversational dialogue. Here's the data structure:

**API Response Structure:**

```json
{
  "response": "Bot response message",
  "completed_steps": ["company_name", "language", ...],
  "business_plan_progress": [...],
  "initial_form_complete": true,
  "form_data": {...},
  "points": 15,
  "current_tier": "experienced_business_professional",
  "tiers": [...],
  "email_collected": true,
  "report_sent": false
}
```

**Progress Tracking:**

- Real-time progress tracking for initial form and business plan sections
- Points-based tier system: Beginner (0) → Motivated Entrepreneur (3) → Growing Entrepreneur (6) → Experienced Business Professional (10) → Master Entrepreneur (20)
- Points allocation: Initial form steps (1 point each), core questions (3 points each), optional questions (5 points each)
- Section-by-section completion status
- Core and optional question tracking with skip functionality after validation retries

### Technical Architecture

**Backend:**
- Flask web framework for API endpoints
- Customized OpenAI GPT-4o-mini assistant with specialized knowledge of business documents, links, and resources tailored for business advisory services
- Answer validation with retry logic (max 1 retry) and gibberish detection, with automatic skip after failed retries
- YAML-based business plan structure loaded from config
- DOCX document generation from form data
- Email service with SMTP integration (automatic email delivery when business plan is complete)
- Text-to-speech (OpenAI TTS) and audio transcription (OpenAI Whisper)
- Automatic email extraction from user messages

**Frontend:**
- Modern, responsive HTML/CSS/JavaScript
- Real-time chat interface with message history
- Dynamic progress bar with step indicators
- Smooth animations and transitions

**API Endpoints:**
- `GET /` - Main application page
- `GET /api/business-plan-structure` - Get business plan structure
- `POST /api/chat` - Send message and receive bot response with progress updates
- `POST /api/tts` - Convert text to speech audio
- `POST /api/transcribe` - Transcribe audio to text
- `POST /api/send-report` - Manually send email report
- `GET /api/download-report` - Download business plan as DOCX
- `POST /api/reset` - Reset form data

### Future Enhancements

- **Form Data Persistence**: Save progress and allow users to resume later
- **Integration with Business Espoo**: Connect with existing advisory service workflows
- **Personalized Recommendations**: AI-driven suggestions based on collected information

### Impact & Alignment with Espoo's Vision

**Accessibility:** Makes business advisory preparation accessible to entrepreneurs regardless of language or experience level

**Preparation:** Helps users arrive at advisory meetings better prepared with clear business information

**Inclusivity:** Addresses language barriers and knowledge gaps, especially for international entrepreneurs

**Scalability:** Digital-first approach allows the service to scale beyond current capacity

**Human-Centered Design:** Intuitive chat interface reduces friction and makes the process feel natural

### License

This project is released into the public domain under the Unlicense.
