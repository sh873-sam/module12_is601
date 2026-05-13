# Module 12 - FastAPI Calculations API

## Overview

This project is a FastAPI-based REST API that provides:

- User registration
- User authentication with JWT tokens
- Protected calculation endpoints
- CRUD operations for calculations
- Pytest automated testing
- GitHub Actions CI/CD integration

The API allows authenticated users to create, retrieve, update, and delete calculations securely.

---

# Technologies Used

- Python 3.12
- FastAPI
- SQLAlchemy
- Pydantic
- JWT Authentication
- Redis
- SQLite
- Pytest
- GitHub Actions
- Uvicorn

---

# Features

## Authentication

- User Registration
- User Login
- JWT Access Tokens
- Protected Routes
- Token Blacklisting

## Calculations

Authenticated users can:

- Create calculations
- View calculations
- Update calculations
- Delete calculations

Supported calculation types include:

- Addition
- Subtraction
- Multiplication
- Division

---

# Project Structure

```text
module12_is601/
│
├── .github/
├── .pytest_cache/
├── .vscode/
├── app/
│   ├── auth/
│   ├── core/
│   ├── models/
│   ├── operations/
│   ├── schemas/
│   ├── database.py
│   ├── database_init.py
│   └── main.py
│
├── tests/
│   ├── integration/
│   └── unit/
│
├── templates/
├── htmlcov/
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
└── README.md
