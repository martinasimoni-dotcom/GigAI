Material Change Coordinator
An intelligent, event-driven workflow automation system for construction material change coordination. This system automatically processes material change events from meetings, project management tools, and calendars, then generates coordinated actions with AI-powered decision intelligence.
🎯 Project Overview
The Material Change Coordinator automates the complex workflow of tracking, approving, and executing material changes in construction projects. When a material change is mentioned (e.g., "Change 3rd floor windows from aluminum to wood frames"), the system:

Captures the event from multiple sources (Fireflies transcripts, ACC, Google Calendar)
Processes and normalizes the data into structured format
Enriches with context (floor plans, suppliers, team contacts, historical data)
Analyzes impact and generates intelligent actions (emails, tasks, calendar events, drawing markups)
Presents a proposal to the PM with confidence scoring
Executes approved actions automatically
Learns from decisions to improve future recommendations

🏗️ Architecture
┌─────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                          │
│  Fireflies • ACC • Google Calendar → Event Bus (Pub/Sub)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        SYSTEM LAYER                          │
│                                                              │
│  Event Normalization → Context Enrichment →                 │
│  Domain Processing → Decision Intelligence                  │
│                                                              │
│  (PostgreSQL for historical data & learning)                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        OUTPUT LAYER                          │
│  Proposal Builder → PM Decision → Action Gateway            │
│  → Feedback & Learning Layer                                │
└─────────────────────────────────────────────────────────────┘
✨ Key Features

Multi-Source Event Capture: Integrates with Fireflies (meeting transcripts), Autodesk Construction Cloud (ACC), and Google Calendar
Intelligent Context Enrichment: Combines API data with markup files (floor plans, team contacts, supplier database)
AI-Powered Action Generation: Uses Claude API to generate contextual emails, tasks, calendar events, and drawing markups
Confidence Scoring: Machine learning-based confidence scoring (>80% = auto-approve eligible)
Continuous Learning: Feedback loop improves decision accuracy over time
Event-Driven Architecture: Scalable, loosely-coupled design using Google Cloud Pub/Sub

📋 Example Scenario
Input: Meeting transcript

"We need to change the third floor windows from aluminum frames to wood frames. That's 12 units total."

Processing:

Extracts: Material change (Aluminum → Wood), Location (3rd floor), Quantity (12 units)
Enriches: Adds floor plan (units W-301 to W-312), supplier info (Premium Wood Co., 3-4 week lead time, $450/unit), team contacts
Analyzes: Identifies procurement need, schedule impact, stakeholder notifications
Generates: Email to supplier, task for procurement officer, calendar follow-up, drawing markup

Output:
Proposal with 86% confidence showing:

Alert: "Windows change alert - 3rd floor"
Actions: 4 coordinated actions ready to execute
Cost: $5,400 estimated
PM Decision: Accept → All actions execute automatically

🚀 Quick Start
Prerequisites

Node.js 18+ (for application runtime)
PostgreSQL 14+ (for historical data storage)
Google Cloud Platform account (for Pub/Sub event bus)
API Keys:

Fireflies API key
Autodesk Construction Cloud (ACC) API key
Google Calendar API credentials
Anthropic Claude API key



Installation
bash# Clone the repository
git clone <your-repo-url>
cd material-change-coordinator

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Set up database
npm run db:setup

# Run migrations
npm run db:migrate

# Seed initial data
npm run db:seed

# Start the application
npm run dev
Development
bash# Run in development mode with hot reload
npm run dev

# Run tests
npm test

# Run end-to-end tests
npm run test:e2e

# Build for production
npm run build

# Start production server
npm start
📁 Project Structure
material-change-coordinator/
├── src/
│   ├── input/              # Connectors (Fireflies, ACC, Google Calendar)
│   ├── system/             # Core processing logic
│   │   ├── data-processing/
│   │   ├── context/
│   │   ├── domain-processing/
│   │   └── decision-intelligence/
│   ├── output/             # Proposal building and action execution
│   └── shared/             # Models, utils, middleware
├── database/               # SQL migrations and seeds
├── config/                 # Configuration files
├── docs/                   # Detailed documentation
└── tests/                  # Test suites
🔧 Configuration
Event Sources
Configure your event sources in config/connectors.yml:
yamlconnectors:
  fireflies:
    type: webhook
    endpoint: /webhooks/fireflies
  acc:
    type: api_pull
    polling_interval: 300
  google_calendar:
    type: api_pull
Confidence Thresholds
Adjust confidence thresholds in config/system/decision-intelligence/threshold-config.json:
json{
  "auto_approve_threshold": 80,
  "requires_review_threshold": 50
}
📚 Documentation

Product Requirements Document (PRD) - Detailed requirements and user stories
Architecture Documentation - System design and data flow
Event Schemas - Data structure specifications
API Documentation - REST API reference
Deployment Guide - Production deployment instructions

🧪 Testing
bash# Run all tests
npm test

# Run unit tests only
npm run test:unit

# Run integration tests
npm run test:integration

# Run with coverage
npm run test:coverage
Example Test Scenario
The end-to-end test simulates the complete workflow:
javascript// Test: Window material change (Aluminum → Wood, 12 units, 3rd floor)
// Expected: Proposal created with >80% confidence
// Expected: 4 actions generated (email, task, calendar, drawing)
// Expected: Actions execute successfully on PM approval
🔐 Security

All API keys stored in environment variables (never committed)
Event data encrypted in transit (HTTPS/TLS)
Database credentials rotated regularly
Scope filtering prevents out-of-scope changes
PM approval required for high-impact changes

📊 Monitoring & Logging
The system logs:

All incoming events
Processing steps and transformations
Confidence scores and decision outcomes
Action execution results
PM decisions and feedback

Logs are structured for easy parsing and analysis.
🤝 Contributing

Fork the repository
Create a feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.
🙋 Support
For questions, issues, or feature requests:

Open an issue on GitHub
Contact the development team
Check the documentation

🗺️ Roadmap
Phase 1 (Current)

✅ Core event processing pipeline
✅ Claude API integration for action generation
✅ Basic PM decision interface
✅ PostgreSQL historical data storage

Phase 2 (Planned)

🔲 Advanced ML-based confidence scoring
🔲 Multi-project support
🔲 Mobile app for PM decisions
🔲 Real-time dashboard

Phase 3 (Future)

🔲 Predictive analytics (anticipate material changes)
🔲 Cost optimization recommendations
🔲 Supplier performance tracking
🔲 Regulatory compliance checking

🏆 Success Metrics

PM Time Saved: Target 80% reduction in manual coordination
Confidence Accuracy: Target >90% accuracy on high-confidence proposals
Response Time: Target <5 minutes from event to proposal
Adoption Rate: Track PM acceptance rate of proposals


Built with ❤️ for construction project managers who deserve better tools.