# Veridion

An e-learning platform featuring tamper-evident, hash-chained digital certificates.
Certificates are time-bound, expiring periodically and verifiable instantly by their unique ID.
Includes an intelligent AI re-proof examiner that assesses learner competence to renew expiring certificates.

## Getting Started

To run the application:

```bash
py main.py
```

## Configuration

The AI re-proof examination feature requires the `GEMINI_API_KEY` environment variable. If the variable is not set, the system automatically falls back to a built-in question bank.
