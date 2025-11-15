# Aino - Business Advisory Service 2.0

Our solution for the City of Espoo challenge at Junction 2025. A ChatGPT-style chatbot interface that guides entrepreneurs through completing their business information form via conversational dialogue, with real-time progress tracking and multi-language support.

🎯 Challenge Background

Addresses the Business Advisory Service 2.0 challenge: creating a digital service to help entrepreneurs prepare for advisory meetings, especially international entrepreneurs lacking knowledge of Finnish business procedures. Our chatbot enables better preparation and clearer communication before live meetings.

🌐 Web Application

We provide a Flask web interface for seamless business form completion:

**Web Application Features:**

- **ChatGPT-style chat interface** for natural, conversational form completion
- **Visual progress tracker** showing completion status of each form step
- **Real-time validation** and guidance throughout the process
- **Multi-language support** ready for international entrepreneurs
- **Responsive design** accessible on various devices

**Quick Start:**

```bash
python app.py
```

Access at `http://127.0.0.1:5001`

The web app guides users through:
- **Initial Form**: Company name, preferred language, business sphere, education, experience, location
- **Business Plan Questions**: Multi-section business plan with core and optional questions
- **Progress Tracking**: Visual progress with points-based tier system
- **Document Generation**: Automatic DOCX business plan generation
- **Email Reports**: Automatic email delivery with business plan attachment
- **Voice Features**: Text-to-speech and audio transcription support

📊 Form Data Structure

The system collects structured business information through conversational dialogue. Here's the data structure:

**Form Steps:**

```
Form Completion Flow
├── company_name          # Business name
│   └── Collected via: Natural conversation
├── language              # Preferred language (English, Spanish, French, German, etc.)
│   └── Collected via: Language selection with intelligent detection
├── sphere                # Business industry/sphere
│   └── Collected via: Open-ended industry description
├── education             # Educational background
│   └── Collected via: Educational qualification input
├── experience            # Years of business experience
│   └── Collected via: Experience level input
└── location              # Business location
    └── Collected via: Location specification
```

**API Response Structure:**

```json
{
  "response": "Bot response message",
  "completed_steps": ["company_name", "language", ...],
  "business_plan_progress": [...],
  "form_data": {...},
  "points": 15,
  "current_tier": "experienced_business_professional",
  "email_collected": true,
  "report_sent": false
}
```

**Progress Tracking:**

- Real-time progress tracking for initial form and business plan sections
- Points-based tier system (Beginner → Master Entrepreneur)
- Section-by-section completion status
- Core and optional question tracking

🔧 Technical Architecture

**Backend:**
- Flask web framework for API endpoints
- OpenAI GPT-4o-mini for conversational responses
- Answer validation with retry logic and gibberish detection
- YAML-based business plan structure
- DOCX document generation
- Email service with SMTP integration
- Text-to-speech and audio transcription (OpenAI Whisper/TTS)

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

🚀 Future Enhancements

- **Form Data Persistence**: Save progress and allow users to resume later
- **Integration with Business Espoo**: Connect with existing advisory service workflows
- **Personalized Recommendations**: AI-driven suggestions based on collected information

💡 Impact & Alignment with Espoo's Vision

**Accessibility:** Makes business advisory preparation accessible to entrepreneurs regardless of language or experience level

**Preparation:** Helps users arrive at advisory meetings better prepared with clear business information

**Inclusivity:** Addresses language barriers and knowledge gaps, especially for international entrepreneurs

**Scalability:** Digital-first approach allows the service to scale beyond current capacity

**Human-Centered Design:** Intuitive chat interface reduces friction and makes the process feel natural

📄 License

This project is released into the public domain under the Unlicense.
