#  Financial Analysis Dashboard (VACore Powered)

A full-stack web application for comparative financial analysis across companies using line items, fiscal/calendar periods, and currency normalization. Built with a modern HTML/CSS/JS frontend and a Flask backend powered by S&P's internal VACore API.

---

##  Features

- **Search Companies** with live suggestions using ElasticSearch
- **Select Line Items** (common and company-specific)
- **Choose Period Type** (Fiscal Year / Calendar Year) and Range
- **Compare Values Across Companies**
- **Save & Resume Analyses**
- **Clean UI with Chips, Accordions, and Dynamic Tables**

---

##  Project Structure
```
project-root/
│
├── static/
│   └── (optional custom JS/CSS if needed)
│
├── templates/
│   ├── index.html         # Create new analysis
│   └── dashboard.html     # View/edit analysis
│
├── app.py                 # Flask backend with all routes
└── README.md              # You're reading this
```

---

##  Backend API (Flask)

### `/api/search-companies`
> Returns company suggestions using a wildcard ElasticSearch query  
**Input**: `q=<query>`  
**Output**: `[{ name, cid }]`

---

### `/api/get-line-items`
> Retrieves available line items for selected companies  
**POST Body**:
```json
{ "company_ids": [101, 102] }
```

---

### `/api/get-periods`
> Returns available CY/FY periods for selected companies  
**POST Body**:
```json
{ "company_ids": [101, 102], "period_type": "CY" }
```

---

### `/api/batch-data`
> Returns financial data matrix for all selected companies, line items, and periods  
**POST Body**:
```json
{
  "companies": ["Apple", "Google"],
  "line_items": [{ "name": "Revenue", "id": 1234 }],
  "periods": ["CY-2023", "CY-2024"],
  "currency": "USD"
}
```

---

##  Frontend Flow

### `index.html`

1. **Step 1**: Search & Select Companies  
2. **Step 2**: Auto-load Line Items → Select from checkbox list  
3. **Step 3**: Choose Period Type and From–To range  
4. **Step 4**: Enter Analysis Title & Save  
→ Redirects to `dashboard.html`

---

### `dashboard.html`

- Loads saved analysis from `localStorage`
- Displays selected companies and line items as **chips**
- Data tables shown inside **accordion-style dropdowns**
- Add or remove:
  - Companies
  - Line Items
  - Period Range
  - Currency
- Changes reflected live via API calls

---


##  LocalStorage Structure

| Key                  | Description                          |
|----------------------|--------------------------------------|
| selectedCompanies    | List of selected company names       |
| selectedCompanyObjects | List of company `{ name, id }`     |
| selectedLineItems    | List of selected line item names     |
| selectedPeriods      | List of periods (e.g., FY-2023)      |
| analysisTitle        | Name of saved analysis               |
| savedAnalyses        | Array of saved analysis titles       |



-----



## Technologies Used

| Layer       | Stack                           |
|-------------|---------------------------------|
| Frontend    | HTML, CSS (Poppins), JavaScript |
| Backend     | Flask (Python)                  |
| Search      | ElasticSearch (VACore API)      |
| Data Engine | VACore: `get_fy_data`, `get_company_sli_param_map`, `get_company_meta_data`, `CompanyPeriodData`, `get_advance_search_data_from_es` |

---

## Setup & Run

1. **Clone the repository**
```bash
git clone <repo-url>
cd <project-folder>
```

2. **Install dependencies**
```bash
pip install flask
```

3. **Run the app**
```bash
python app.py
```

4. **Navigate to**
```
http://localhost:5000/dashboard
```

---

## Notes

- All user selections are saved using `localStorage`
- No database is used for persistence — session-based analysis only
- `currency` is hardcoded to "USD" unless modified in future

---


