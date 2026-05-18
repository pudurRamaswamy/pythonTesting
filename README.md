This repository demonstrates a production-grade UI and API automation architecture using **Playwright**, **Pytest**, and **Pydantic**.

## 🚀 Key Architectural Features:
- **Contract Testing:** Uses Pydantic to enforce schema validation on API responses, catching backend breaking changes at type-level.
- **Horizontal Scaling:** GitHub Actions YAML configured with **Matrix Sharding** to run tests in parallel across multiple runners.
- **Advanced OOP:** Implements **Abstract Base Classes (ABC)** for Page Objects to ensure a strict contract across the Page Object Model (POM).
- **Network Interception:** Demonstrates `page.route` to mock backend responses for resilient UI testing.
- **Isolation:** Utilizes Playwright's `BrowserContext` to ensure zero state-leakage between parallel test executions.
- login once and keep the sesssion context and use it for subsequent tests.

## 🛠️ How to run:
1. `pip install -r requirements.txt`
2. `playwright install`
3. `pytest --shard 1/2`