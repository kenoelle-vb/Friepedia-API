import os
import pandas as pd
import numpy as np
import spacy
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
        
        # 1. API Key Validation (Server-Side Internal Check)
        if self.api_key != "FRIE-KENOELLE":
            print("Authentication Failed. Invalid Internal API Key.")
            self.authenticated = False
            return

        self.authenticated = True

        # 2. Dynamic Path Detection (The Backend Fortress Logic)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        self.data_path = os.path.join(root_dir, "database", "friepedia webinars mock dataset.csv")

        # 3. Load Data from the Dynamic Path
        try:
            self.df = pd.read_csv(self.data_path)
            self.df.fillna("", inplace=True)
            print(f"Successfully loaded dataset: {len(self.df)} rows.")
        except Exception as e:
            print(f"Error loading dataset at {self.data_path}: {e}")
            self.df = pd.DataFrame()

        # 4. Silent Initialization of Heavy AI Models
        print("Loading NLP and Vector Models into Server RAM...")
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            print("Warning: spaCy en_core_web_sm not found. Keyword bonus will degrade to simple split.")
            self.nlp = None
            
        self.vector_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Engine Ready.")

    def search(self, query, columns=None, top_k=6):
        """
        BACKEND API METHOD:
        Performs a semantic RAG search and returns a clean DataFrame including vectors.
        """
        if not self.authenticated:
            raise PermissionError("API Key not authenticated.")

        if self.df.empty:
            raise ValueError("Database is empty or failed to load.")

        # Identify target column (Default to Summary)
        target_col = "Summary" if "Summary" in self.df.columns else self.df.columns[0]

        # 1. Vectorization Cache Check (Using the 'vector_' prefix)
        vec_col_name = f"vector_{target_col}"
        if vec_col_name not in self.df.columns:
            print(f"Generating new vectors for column: {target_col}...")
            self.df[vec_col_name] = list(self.vector_model.encode(self.df[target_col].astype(str).tolist()))

        # 2. Vector Similarity
        query_vec = self.vector_model.encode(query).reshape(1, -1)
        vec_array = np.stack(self.df[vec_col_name].values)
        self.df['vector_score'] = cosine_similarity(query_vec, vec_array)[0]

        # 3. Hybrid Logic (Keyword Bonus)
        if self.nlp:
            doc = self.nlp(query)
            anchors = [t.text.lower() for t in doc if t.pos_ in ["PROPN", "NOUN", "VERB"]]
        else:
            anchors = query.lower().split()

        def calc_bonus(text):
            text_lower = str(text).lower()
            return 0.15 if any(a in text_lower for a in anchors) else 0.0

        self.df['string_bonus'] = self.df[target_col].apply(calc_bonus)
        self.df['final_score'] = self.df['vector_score'] + self.df['string_bonus']

        # 4. Result Extraction
        results = self.df.sort_values(by='final_score', ascending=False).head(top_k).copy()

        # --- CRITICAL FIX: CONVERT NDARRAY TO LIST FOR JSON SERIALIZATION ---
        # This prevents the 'ndarray is not JSON serializable' error
        for col in results.columns:
            if col.startswith("vector_"):
                results[col] = results[col].apply(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)
        # --------------------------------------------------------------------

        # 5. Smart Cleanup for Stress Testing & Export
        # We drop the internal math scores but KEEP the 'vector_' columns for the client
        internal_scores = ['vector_score', 'string_bonus', 'final_score']

        if columns:
            # If client specifically requested columns, return exactly those
            return results[columns]
        else:
            # Drop only the scores to keep the payload clean but informative
            return results.drop(columns=[c for c in internal_scores if c in results.columns])

    def get_schema(self):
        """Returns the available data points for the backend developer to query."""
        if self.df.empty:
            return []
        return list(self.df.columns)