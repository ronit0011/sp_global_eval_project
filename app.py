from flask import Flask, render_template, request, redirect, url_for, jsonify
import vacore
from vacore.metadata import company_meta_data as comeda
from vacore.searchengine.searchengine_elastic import get_advance_search_data_from_es
from vacore.searchengine.es_bulk_insert import fetch_company_info
from vacore.metadata.sli_parameter_data import get_company_sli_param_map

app = Flask(__name__)

# --------- VACore CONFIGURATION ---------
config = vacore.get_dummy_config()
vacore.CONFIG = vacore.Settings("DEV")
vacore.CONFIG.set_config(config)

# --------- ROUTES ---------

# ✅ Default route - load dashboard directly
@app.route('/')
def home():
    return redirect(url_for('dashboard'))

# STEP 1: index.html - used to create a new analysis
@app.route('/new-analysis')
def new_analysis():
    return render_template('index.html')

# STEP 2: dashboard.html - main dashboard page
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        selected_companies = request.form.getlist('companies[]')
        selected_periods = request.form.getlist('periods[]')
        selected_line_items = request.form.getlist('line_items[]')

        return render_template(
            'dashboard.html',
            companies=selected_companies,
            periods=selected_periods,
            line_items=selected_line_items
        )
    else:
        return render_template('dashboard.html')

# API: Fetch list of companies (for static dropdown fallback or testing)
@app.route('/api/company-list')
def get_company_list():
    try:
        rows, _ = fetch_company_info()
        companies = [
            {"companyid": row["cid"], "name": row["company_name"]}
            for row in rows if "cid" in row and "company_name" in row
        ]
        return jsonify(companies)
    except Exception as e:
        return jsonify({"error": str(e)})

# API: Fetch metadata company list (optional, not used currently)
@app.route('/api/company-data')
def company_data():
    try:
        data = comeda.get_company_meta_data()
        return jsonify(data[:100])
    except Exception as e:
        return jsonify({"error": str(e)})

# API: Dummy data for cell values (dashboard)
@app.route('/api/data')
def get_data():
    company = request.args.get('company')
    line_item = request.args.get('line_item')
    period = request.args.get('period')
    currency = request.args.get('currency')

    # Dummy response
    return jsonify({"value": f"{line_item} of {company} in {period} ({currency})"})

# ✅ API: ElasticSearch-powered Company Name Autocomplete

@app.route('/api/search-companies')
def search_companies():
    search_text = request.args.get('q', '').strip().lower()
    print("🔍 Search Text:", search_text)

    if not search_text:
        return jsonify([])

    es_query = {
        "query": {
            "bool": {
                "should": [
                    {
                        "wildcard": {
                            "company_name": {
                                "value": f"*{search_text}*"
                            }
                        }
                    },
                    {
                        "wildcard": {
                            "ticker": {
                                "value": f"*{search_text}*"
                            }
                        }
                    }
                ]
            }
        },
        "collapse": {
            "field": "cid"
        }
    }

    try:
        results = get_advance_search_data_from_es(es_query)
        hits = results.get("hits", {}).get("hits", [])

        print("🟢 Raw Hits:", hits)

        suggestions = []
        for item in hits:
            print("🔎 Inspecting Hit:", item)

            source = item.get("_source", {})
            company_id = source.get("companyid") or source.get("cid")
            company_name = source.get("company_name") or source.get("name")

            if company_id and company_name:
                suggestions.append({
                    "companyid": company_id,
                    "name": company_name
                })

        print("✅ Suggestions:", suggestions)
        return jsonify(suggestions)

    except Exception as e:
        print("❌ Elasticsearch error:", str(e))
        return jsonify([])




# @app.route('/api/search-companies')
# def search_companies():
#     search_text = request.args.get('q', '').strip().lower()
#     if not search_text:
#         return jsonify([])
    
#     es_query = {
#     "query": {
#         "bool": {
#             "should": [
#                 {
#                     "wildcard": {
#                         "company_name.keyword": f"*{search_text.upper()}*"
#                     }
#                 },
#                 {
#                     "wildcard": {
#                         "ticker.keyword": f"*{search_text.upper()}*"
#                     }
#                 }
#             ]
#         }
#     },
#     "collapse": {
#         "field": "cid"
#     }
# }



#     # es_query = {
#     #     "query": {
#     #         "query_string": {
#     #             "query": f"*{search_text}*",
#     #             "fields": ["company_name", "ticker"]
#     #         }
#     #     },
#     #     "collapse": {
#     #         "field": "cid"
#     #     }
#     # }


#     try:
#         result = get_advance_search_data_from_es(es_query)

#         # ✅ Correctly extract hits
#         hit_list = result.get("hits", {}).get("hits", [])

#         suggestions = []
#         for item in hit_list:
#             source = item.get("_source", {})
#             company_id = source.get("cid")
#             company_name = source.get("company_name")
#             if company_id and company_name:
#                 suggestions.append({
#                     "companyid": company_id,
#                     "name": company_name
#                 })

#         return jsonify(suggestions)

#     except Exception as e:
#         print("Elasticsearch error:", str(e))
#         return jsonify({"error": str(e)})



#     # try:
#     #     results = get_advance_search_data_from_es(es_query)
#     #     suggestions = []
#     #     for item in results:
#     #         source = item.get("_source", item)
#     #         company_id = source.get("cid") or source.get("companyid")
#     #         company_name = source.get("company_name") or source.get("name")
#     #         if company_id and company_name:
#     #             suggestions.append({"companyid": company_id, "name": company_name})
#     #     return jsonify(suggestions)
#     # except Exception as e:
#     #     print("Elasticsearch error:", str(e))
#     #     return jsonify({"error": str(e)})




@app.route('/api/get-line-items', methods=['POST'])
def get_line_items_for_companies():
    try:
        data = request.get_json()
        company_ids = data.get("company_ids", [])  # list of integers
        all_items = {}

        for cid in company_ids:
            item_map = get_company_sli_param_map(cid)
            for label, details in item_map.items():
                if label not in all_items:
                    all_items[label] = details  # Only add once

        line_item_list = [
            {"name": key, "sli_id": value["sli_id"], "param": value["param"]}
            for key, value in all_items.items()
        ]

        return jsonify(line_item_list)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ✅ Run the Flask server
if __name__ == "__main__":
    app.run(debug=True)
