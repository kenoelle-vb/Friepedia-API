import os
import pandas as pd
import numpy as np
import warnings
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Suppress warnings for clean server logs
warnings.filterwarnings('ignore')
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

class FriepediaWebinarsEngine:
    def __init__(self, api_key=""):
        self.api_key = api_key
        
        # 1. API Key Validation
        if self.api_key != "FRIE-KENOELLE":
            print("Authentication Failed. Invalid Internal API Key.")
            self.authenticated = False
            return

        self.authenticated = True

        # 2. Dynamic Path Detection (Adjusted for being inside the 'friepedia' folder)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        self.data_path = os.path.join(root_dir, "database", "friepedia webinars mock dataset.csv")

        # 3. Load Data
        try:
            self.df = pd.read_csv(self.data_path)
            self.df.fillna("", inplace=True)
            print(f"Successfully loaded dataset: {len(self.df)} rows.")
        except Exception as e:
            print(f"Error loading dataset at {self.data_path}: {e}")
            self.df = pd.DataFrame()

        # 4. Silent Initialization of Heavy AI Models
        print("Loading AI Models into Server RAM...")
        self.vector_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Engine Ready.")

    def search(self, query, target_col=None, columns=None, top_k=48):
        """
        BACKEND API METHOD (DUAL POINTING SYSTEM WITH STRICT GUARDRAILS):
        1. Validates schema strictly. Fails fast and loudly instead of using hidden fallbacks.
        2. Ranks strictly by exact string match count (+1 point per matching word).
        3. Uses Vector Similarity (0-10) only as a secondary tie-breaker.
        """
        if not self.authenticated:
            raise PermissionError("API Key not authenticated.")

        if self.df.empty:
            raise ValueError("Database is empty or failed to load.")

        # --- STRICT SCHEMA GUARDRAIL (FAIL FAST & LOUDLY) ---
        if not target_col:
            raise ValueError("Missing payload parameter: 'target_column' must be explicitly specified by the client.")

        if target_col not in self.df.columns:
            raise KeyError(f"Invalid column request: '{target_col}'. This does not match your active media dataset schema. Available database columns are: {list(self.df.columns)}")
        # -----------------------------------------------------

        # 1. Dynamic Vectorization & Cache Check
        vec_col_name = f"vector_{target_col}"
        if vec_col_name not in self.df.columns:
            print(f"Generating new semantic vectors for column: '{target_col}'...")
            self.df[vec_col_name] = list(self.vector_model.encode(self.df[target_col].astype(str).tolist()))

        # 2. VECTOR SCORING (0.0 to 1.0 multiplied by 10)
        query_vec = self.vector_model.encode(query).reshape(1, -1)
        vec_array = np.stack(self.df[vec_col_name].values)
        self.df['vector_score'] = cosine_similarity(query_vec, vec_array)[0] * 10.0

        # 3. STRING MATCHING SCORING (+1 point for every matching word in the raw database cell)
        query_words = [w.lower() for w in query.split(" ") if w.strip()]
        
        def calc_string_points(text):
            text_lower = str(text).lower()
            # Directly checks the raw cell contents, preserving matching capabilities through structural characters like ["
            return sum(1 for word in query_words if word in text_lower)

        self.df['string_points'] = self.df[target_col].apply(calc_string_points)
        
        # 4. DUAL-TIER SORTING
        # Filters and organizes results strictly prioritizing explicit word hits first
        results = self.df.sort_values(by=['string_points', 'vector_score'], ascending=[False, False]).head(top_k).copy()

        # CONVERT NDARRAY TO LIST FOR JSON SERIALIZATION
        for col in results.columns:
            if col.startswith("vector_"):
                results[col] = results[col].apply(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)

        internal_scores = ['vector_score', 'string_points']
        
        if columns:
            return results[columns]
        else:
            return results.drop(columns=[c for c in internal_scores if c in results.columns])

    def get_schema(self):
        if self.df.empty:
            return []
        return list(self.df.columns)