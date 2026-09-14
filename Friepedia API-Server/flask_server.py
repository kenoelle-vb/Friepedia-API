import os
import pandas as pd
from flask import Flask, request, jsonify

# The "Brain" - Importing your proprietary logic from the friepedia folder
from friepedia.friepedia_webinars import FriepediaWebinarsEngine

# 1. Dynamic OS-Aware Pathing
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "html_templates")
DATABASE_DIR = os.path.join(CURRENT_DIR, "database")

# Initialize Flask with the dynamic template folder
app = Flask(__name__, template_folder=TEMPLATE_DIR)

# 2. Master Engine Initialization
print("Initializing Friepedia Server Engine...")
engine = FriepediaWebinarsEngine(api_key="FRIE-KENOELLE")
print("Engine Initialized. Ready for requests.")

def verify_and_burn_quota(user_key):
    """Gatekeeper Logic: Checks API key and quota."""
    xlsx_path = os.path.join(DATABASE_DIR, "0_friepedia_api_keys_database.xlsx")
    csv_path = os.path.join(DATABASE_DIR, "0_friepedia_api_keys_database.csv")
    
    if os.path.exists(xlsx_path):
        db_path = xlsx_path
        is_csv = False
        df_keys = pd.read_excel(db_path)
    elif os.path.exists(csv_path):
        db_path = csv_path
        is_csv = True
        df_keys = pd.read_csv(db_path)
    else:
        return False, "API Vault Missing (Database not found on server)."

    user_row = df_keys[df_keys['api_key'] == user_key]
    if user_row.empty:
        return False, "Unauthorized: Invalid API Key."
    
    current_quota = user_row.iloc[0]['call_quota']
    if current_quota <= 0:
        return False, "Unauthorized: API Quota Exhausted."
    
    df_keys.loc[df_keys['api_key'] == user_key, 'call_quota'] = current_quota - 1
    
    if is_csv:
        df_keys.to_csv(db_path, index=False)
    else:
        df_keys.to_excel(db_path, index=False)
        
    return True, "Authorized"

# --- API ROUTES ---

@app.route('/v1/webinars/search', methods=['POST'])
def api_webinar_search():
    """The specialized endpoint for Webinar RAG search."""
    data = request.json
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400
        
    api_key = data.get("api_key")
    query = data.get("query")
    target_column = data.get("target_column") 
    requested_cols = data.get("columns", None)
    top_k = data.get("top_k", 48)

    if not api_key or not query:
        return jsonify({"error": "Missing 'api_key' or 'query' parameters"}), 400

    is_valid, message = verify_and_burn_quota(api_key)
    if not is_valid:
        return jsonify({"error": message}), 403

    try:
        results_df = engine.search(
            query=query, 
            target_col=target_column, 
            columns=requested_cols, 
            top_k=top_k
        )
        return jsonify(results_df.to_dict(orient='records')), 200
    except Exception as e:
        return jsonify({"error": f"Webinar search failed: {str(e)}"}), 500

@app.route('/v1/webinars/schema', methods=['GET'])
def api_webinar_schema():
    try:
        return jsonify(engine.get_schema()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)