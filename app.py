# --------- Imports ---------
from flask import Flask, render_template, request, redirect, url_for, jsonify  # Flask core utilities
import vacore  # VACore main package
from vacore.metadata import company_meta_data as comeda  # Company metadata (not used directly here)
from vacore.searchengine.searchengine_elastic import get_advance_search_data_from_es  # Elasticsearch search method
from vacore.searchengine.es_bulk_insert import fetch_company_info  # Company fetch utility (not used directly)
from vacore.metadata.sli_parameter_data import get_company_sli_param_map  # Line item mapping method
from vacore.metadata.company_period_data import CompanyPeriodData as cop  # Period data class
from vacore.dal.standardized_data import get_fy_data  # Main financial data fetch method
import traceback  # For error trace printing

# --------- Flask App Initialization ---------
app = Flask(__name__)

# --------- VACore Configuration ---------
# Load a dummy config and apply the DEV environment settings to VACore
config = vacore.get_dummy_config()
vacore.CONFIG = vacore.Settings("DEV")
vacore.CONFIG.set_config(config)

# --------- Route: Home Redirect ---------
@app.route('/')
def home():
    return redirect(url_for('dashboard'))  # Redirect root URL to /dashboard

# --------- Route: New Analysis Page ---------
@app.route('/new-analysis')
def new_analysis():
    return render_template('index.html')  # Renders the company/line item/period selection UI

# --------- Route: Dashboard Page ---------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    return render_template('dashboard.html')  # Main dashboard view with result tables



# --------- API: Company Search (Elasticsearch) ---------
@app.route('/api/search-companies')
def search_companies():
    query = request.args.get("q", "").strip()  # Get query string from URL params
    if not query:
        return jsonify([])  # Return empty if no query

    # Build wildcard search query for both company name and ticker
    es_query = {
        "query": {
            "bool": {
                "should": [
                    {"wildcard": {"company_name": {"value": f"*{query}*"}}},
                    {"wildcard": {"ticker": {"value": f"*{query}*"}}}
                ]
            }
        },
        "collapse": {"field": "cid"},  # Collapse duplicate company entries
    }

    try:
        result = get_advance_search_data_from_es(es_query)
        hits = result.get("hits", {}).get("hits", [])
        suggestions = []
        for item in hits:
            source = item.get("_source", {})
            cid = source.get("cid") or source.get("companyid")
            name = source.get("company_name") or source.get("name")
            if cid and name:
                suggestions.append({"companyid": cid, "name": name})  # Collect company suggestion
        return jsonify(suggestions)
    except Exception as e:
        return jsonify([])  # Fail silently with empty list



# --------- API: Line Items by Company IDs ---------
@app.route('/api/get-line-items', methods=['POST'])
def get_line_items_for_companies():
    try:
        data = request.get_json()
        company_ids = data.get("company_ids", [])  # List of selected company IDs
        line_item_counter = {}  # To aggregate and deduplicate line items across companies

        for cid in company_ids:
            items = get_company_sli_param_map(cid)  # Fetch line items for each company
            if not isinstance(items, list):
                continue
            for item in items:
                sli_id = item.get("UniqueSliId")
                sli_name = item.get("SliName", "Unnamed")
                param = item.get("Category", "General")
                if sli_id not in line_item_counter:
                    line_item_counter[sli_id] = {"name": sli_name, "param": param, "count": 1}
                else:
                    line_item_counter[sli_id]["count"] += 1  # Count occurrences for commonality

        # Build response list
        line_item_list = []
        for sli_id, info in line_item_counter.items():
            line_item_list.append({
                "sli_id": sli_id,
                "name": f"{info['name']} ({info['count']})",  # Append count
                "param": info["param"]
            })
        return jsonify(line_item_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error if failed



# --------- API: Periods for Selected Companies ---------
@app.route('/api/get-periods', methods=['POST'])
def get_periods():
    try:
        data = request.get_json()
        company_ids = data.get("company_ids", [])
        period_type = data.get("period_type", "FY")  # Either FY or CY

        cpd = cop(company_ids)  # Initialize CompanyPeriodData
        mapping = cpd.company_calendar_to_fiscal_map  # Dict mapping CY → FY

        all_periods = set()
        for cid in company_ids:
            company_map = mapping.get(cid, {})
            if period_type == "FY":
                fy_set = {v for v in company_map.values() if isinstance(v, str) and v.startswith("FY-")}
                all_periods.update(fy_set)
            elif period_type == "CY":
                cy_set = {k for k in company_map if isinstance(k, str) and k.startswith("CY-")}
                all_periods.update(cy_set)

        # Sort periods numerically by year
        sorted_periods = sorted(all_periods, key=lambda x: int(x.split("-")[1]))
        return jsonify(sorted_periods)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# --------- API: Batch Financial Data Retrieval ---------
@app.route('/api/batch-data', methods=['POST'])
def batch_data():
    try:
        data = request.get_json()
        companies = data.get("companies", [])  # List of company names
        periods = data.get("periods", [])  # Selected periods like FY-2023
        line_items = data.get("line_items", [])  # Selected line items
        currency = data.get("currency", "USD")  # Selected currency

        if not companies or not periods or not line_items:
            return jsonify({"error": "Missing input data."}), 400  # Input validation

        # --------- Step 1: Map Company Names to CIDs ---------
        company_ids = {}
        for company in companies:
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "query_string": {
                                    "query": f"*{company}*",
                                    "fields": ["company_name", "ticker", "name"]
                                }
                            }
                        ]
                    }
                },
                "collapse": {"field": "cid"}
            }

            results = get_advance_search_data_from_es(query)
            hits = results.get("hits", {}).get("hits", [])
            if hits:
                source = hits[0]["_source"]
                cid = source.get("cid") or source.get("companyid")
                if cid:
                    company_ids[company] = cid  # Map name → cid

        print("Mapped Company IDs:", company_ids)

        # --------- Step 2: Map Line Item Labels to Unique SLI IDs ---------
        sli_ids = {}
        for company, cid in company_ids.items():
            items = get_company_sli_param_map(cid)
            for line_item in line_items:
                label = line_item.split("(")[0].strip()  # Extract name without (count)
                for item in items:
                    if item.get("SliName", "").strip().lower() == label.lower():
                        sli_ids[line_item] = item.get("UniqueSliId")
                        break

        print("Mapped SLI IDs:",sli_ids)

        # --------- Step 3: Retrieve Financial Data from VACore ---------
        result = get_fy_data(
            list_company_id=list(company_ids.values()),
            list_universal_or_uniquesli_id=list(sli_ids.values()),
            list_fy_cy=periods,
            list_source_id=[13001],  # Source ID for consensus data
            is_uniquesli_id=True,
            to_currency_iso_code=currency,
            need_formatting=False
        )

        # --------- Step 4: Construct Response Dictionary ---------
        response = {}
        for company, cid in company_ids.items():
            response[company] = {}
            for line_item, sli_id in sli_ids.items():
                response[company][line_item] = {}
                for period in periods:
                    value = (
                        result.get(cid, {})
                              .get(13001, {})  # Source ID
                              .get(sli_id, {})
                              .get(period, {})
                              .get("v", "N/A")  # Extract value or return N/A
                    )
                    response[company][line_item][period] = value

        print(response)
        return jsonify(response)

    except Exception as e:
        import traceback
        traceback.print_exc()  # Print full traceback in console
        return jsonify({"error": str(e)})



# --------- Main Entry Point ---------
if __name__ == "__main__":
    app.run(debug=True)  # Enable debug mode for development
