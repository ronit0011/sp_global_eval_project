from flask import Flask, render_template, request, session, redirect, url_for,jsonify
from vacore.searchengine.es_bulk_insert import fetch_company_info
from vacore.metadata.company_meta_data import get_company_meta_data
from vacore.metadata.sli_parameter_data import get_company_sli_param_map

app = Flask(__name__)
app.secret_key = 'secret-key'  # Needed to use session

@app.route('/', methods=['GET', 'POST'])
def home():
    # Get tickers from VACore
    tickers = []
    try:
        rows, _ = fetch_company_info()
        
        tickers = ({row.get("ticker") for row in rows if row.get("ticker")})
        ids =({row.get("cid") for row in rows })
        #print(ids)
        #print(tickers)
        
        
    except Exception as e:
        print("Error fetching tickers:", str(e))

    # Initialize ticker list in session
    if 'selected_tickers' not in session:
        session['selected_tickers'] = []

    # Handle form submission
    if request.method == 'POST':
        selected_ticker = request.form.get("ticker")
        if selected_ticker and selected_ticker not in session['selected_tickers']:
            session['selected_tickers'].append(selected_ticker)
            print( session['selected_tickers'])
            session.modified = True  # Mark session as changed

    return render_template('index2.html', tickers=tickers, selected=session['selected_tickers'])

# Route to clear selected tickers
@app.route('/clear')
def clear():
    session.pop('selected_tickers', None)
    return redirect(url_for('home'))

@app.route('/submit', methods=['POST'])
def submit():
    tickers = session.get('selected_tickers', [])
    return render_template('submit.html', tickers=tickers)



@app.route('/get-line-items-by-ticker', methods=['POST'])
def get_line_items_by_ticker():
    tickers = session.get("selected_tickers", [])
    rows, _ = fetch_company_info()
    ids=[]
    for t in tickers:
        i = ({row.get("cid") for row in rows if row.get('ticker')==t})
        ids.append(str(i))
    combined_line_items = []

    for cid in ids:
        try:
            line_items = get_company_sli_param_map([cid])
            print(line_items)  # returns a list of dicts

            for item in line_items:
                combined_line_items.append({
                    "company_id": item.get("CompanyId"),
                    "sli_id": item.get("SLIId"),
                    "name": item.get("SliName"),
                    "tab": item.get("Tab"),
                    "category": item.get("Category")
                })

        except Exception as e:
            print(f"❌ Error for company ID {cid}: {str(e)}")
    print(combined_line_items)
    return combined_line_items

        

   



if __name__ == '__main__':
    app.run(debug=True)
