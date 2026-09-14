import pandas as pd
import requests
import math
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output

class FriepediaWebinarsEngine:
    def __init__(self, api_key=""):
        self.api_key = api_key
        self.base_url = "http://127.0.0.1:5000" 
        self.authenticated = True 

        self.design_map = {
            "Title": "Title",
            "Summary": "Raw Text",
            "Key Speakers": "Hollow Pills (Accent)",
            "Institution": "Institution",
            "Important Figures/Statistics": "Content Box"
        }

        self.component_order = [
            "Title",
            "Institution",
            "Key Speakers",
            "Important Figures/Statistics",
            "Summary"
        ]

        self.inventory = []
        
        # --- State Machine & Pagination Guardrails ---
        self.search_in_progress = False
        self.current_search_results = None
        self.current_page = 1
        self.items_per_page = 12
        
        try:
            response = requests.get(f"{self.base_url}/v1/webinars/schema", timeout=5)
            all_cols = response.json() if response.status_code == 200 else []
            self.nlp_columns = [col for col in all_cols if "_" in col and col != "Link"]
            self.searchable_cols = [c for c in list(self.design_map.keys()) if c in all_cols] or list(self.design_map.keys())
        except Exception as e:
            print(f"Warning: API offline during init. ({e})")
            self.nlp_columns = ['top_entities', 'top_stats', 'most_positive_sentences']
            self.searchable_cols = list(self.design_map.keys())

        self.output_area = widgets.Output()
        self.page_1_view = widgets.VBox()
        self.page_2_view = widgets.VBox()
        self.dynamic_canvas = widgets.VBox()

    def _inject_css(self):
        css = """
        <style>
            .frie-app-container { width: 100% !important; margin: 0 auto; background-color: #fafafa; padding: 25px; border: 1px solid #e0e0e0; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); display: flex; flex-direction: column; box-sizing: border-box; }
            .frie-card { border: 1px solid #a6a1a3; box-shadow: 0 4px 12px rgba(0,0,0,0.05); background-color: white; border-radius: 15px; padding: 25px; width: 100%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; flex-direction: column; box-sizing: border-box; min-width: 320px; height: 100%; transition: transform 0.2s ease; }
            .frie-card:hover { transform: translateY(-5px); }
            .jupyter-button.frie-header-pill { background-color: transparent !important; border: 2px solid #088395 !important; border-radius: 50px !important; color: #088395 !important; font-weight: bold !important; height: 45px !important; font-size: 1.1em !important; }
            .jupyter-button.frie-header-pill:hover { background-color: #088395 !important; color: white !important; }
            .frie-search-pill input, .frie-search-pill select { border: 2px solid #a6a1a3 !important; border-radius: 50px !important; background-color: white !important; color: #4e4b4c !important; padding: 8px 20px !important; height: 40px !important; }
            .jupyter-button.frie-action-pill { background-color: transparent !important; border: 2px solid #a6a1a3 !important; border-radius: 50px !important; color: #4e4b4c !important; height: 38px !important; font-size: 0.9em !important; margin: 5px !important; }
            .jupyter-button.frie-action-pill:hover { background-color: #a6a1a3 !important; color: white !important; }
            .jupyter-button.frie-add-pill { background-color: #088395 !important; border: none !important; border-radius: 50px !important; color: white !important; font-weight: bold !important; height: 38px !important; margin: 5px !important; }
            .jupyter-button.frie-add-pill:hover { background-color: #066b7a !important; }
            .jupyter-button.frie-nav-pill { background-color: #a6a1a3 !important; border: none !important; border-radius: 50px !important; color: white !important; font-weight: bold !important; height: 40px !important; width: 150px !important; margin: 5px !important; transition: 0.2s; }
            .jupyter-button.frie-nav-pill:hover { background-color: #088395 !important; }
            .jupyter-button.frie-nav-pill:disabled { background-color: #e0e0e0 !important; color: #a6a1a3 !important; }
            .frie-title { text-align: center; font-weight: 800; color: #088395; font-size: 1.4em; margin-bottom: 8px; line-height: 1.2; }
            .frie-inst { color: #4e4b4c; font-size: 0.95em; text-align: center; margin-bottom: 15px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; }
            .frie-pill-accent { border: 1px solid #088395; color: #088395; border-radius: 20px; padding: 5px 15px; display: inline-block; font-size: 0.85em; margin: 4px; font-weight: 700; }
            .frie-content-box { background-color: #088395; color: white; border-radius: 15px; padding: 20px; font-weight: 700; text-align: center; margin: 15px 0; font-size: 1.15em; box-shadow: inset 0 0 10px rgba(0,0,0,0.1); }
            .frie-raw-text { color: #4e4b4c; text-align: justify; font-size: 1em; line-height: 1.6; margin-bottom: 20px; flex-grow: 1; }
        </style>
        """
        display(HTML(css))

    def _format_aesthetic_name(self, col_name):
        return col_name.replace('_', ' ').title()

    def _build_header(self):
        btn_page_1 = widgets.Button(description="Page 1: Discovery", layout=widgets.Layout(width='40%'))
        btn_page_1.add_class('frie-header-pill')

        btn_page_2 = widgets.Button(description="Page 2: Inventory", layout=widgets.Layout(width='40%'))
        btn_page_2.add_class('frie-header-pill')

        btn_page_1.on_click(lambda b: self._switch_page(1))
        btn_page_2.on_click(lambda b: self._switch_page(2))

        return widgets.HBox([btn_page_1, btn_page_2], layout=widgets.Layout(justify_content='space-around', margin='0 0 25px 0'))

    def _switch_page(self, page_num):
        if page_num == 1:
            self.dynamic_canvas.children = [self.page_1_view]
        else:
            self._refresh_page_2()
            self.dynamic_canvas.children = [self.page_2_view]

    def _setup_page_1(self):
        self.search_input = widgets.Text(placeholder='Enter search query...', layout=widgets.Layout(width='50%'))
        self.search_input.add_class('frie-search-pill')

        self.search_dropdown = widgets.Dropdown(
            options=[(self._format_aesthetic_name(c), c) for c in self.searchable_cols],
            value=self.searchable_cols[0],
            description='Search From:',
            layout=widgets.Layout(width='30%')
        )
        self.search_dropdown.add_class('frie-search-pill')

        btn_search = widgets.Button(description="Search")
        btn_search.add_class('frie-add-pill')
        btn_search.on_click(self._execute_search)

        search_bar = widgets.HBox([self.search_dropdown, self.search_input, btn_search], layout=widgets.Layout(margin='0 0 15px 0'))
        self.results_container = widgets.Output()
        self.page_1_view = widgets.VBox([search_bar, widgets.HTML("<hr style='border:1px solid #e0e0e0;'>"), self.results_container])

    def _execute_search(self, b):
        query = self.search_input.value

        if not query:
            return

        # --- HARDWARE GUARDRAIL: Drop overlapping click events instantly ---
        if self.search_in_progress:
            return
        self.search_in_progress = True

        # Frontend Visual Locking
        b.disabled = True
        old_desc = b.description
        b.description = "Searching..."

        # Open and CLOSE the output block immediately just to paint the loading notification
        with self.results_container:
            clear_output(wait=True)
            print("Connecting to Friepedia Core...")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "target_column": self.search_dropdown.value, 
            "top_k": 48
        }

        try:
            # Network call executes cleanly outside any active ipywidgets context capture wrappers
            response = requests.post(f"{self.base_url}/v1/webinars/search", json=payload)
            
            if response.status_code == 200:
                self.current_search_results = pd.DataFrame(response.json())
                self.current_page = 1
                self._render_paginated_view()
            else:
                with self.results_container:
                    clear_output(wait=True)
                    error_msg = response.json().get("error", "Unknown API Error")
                    print(f"API Error ({response.status_code}): {error_msg}")
        except requests.exceptions.RequestException as e:
            with self.results_container:
                clear_output(wait=True)
                print(f"Connection Failed: Ensure the server is running at {self.base_url}.\nDetails: {e}")
        finally:
            # Re-enable controls safely
            b.disabled = False
            b.description = old_desc
            self.search_in_progress = False

    def _render_paginated_view(self):
        """Slices the dataframe and displays max 12 items inside an isolated stream context."""
        with self.results_container:
            clear_output(wait=True)
            
            if self.current_search_results is None or self.current_search_results.empty:
                print("No matches found.")
                return

            total_items = len(self.current_search_results)
            total_pages = math.ceil(total_items / self.items_per_page)

            start_idx = (self.current_page - 1) * self.items_per_page
            end_idx = start_idx + self.items_per_page
            page_df = self.current_search_results.iloc[start_idx:end_idx]

            cards = []
            for _, row in page_df.iterrows():
                cards.append(self._create_single_card(row.to_dict(), show_buttons=True))

            grid = widgets.GridBox(
                cards,
                layout=widgets.Layout(
                    width='100%',
                    grid_template_columns='repeat(auto-fill, minmax(320px, 1fr))',
                    grid_gap='25px',
                    padding='10px',
                    align_items='stretch'
                )
            )

            # Pagination Navigation Buttons
            btn_prev = widgets.Button(description="Previous Page")
            btn_prev.add_class('frie-nav-pill')
            btn_prev.disabled = (self.current_page == 1)
            btn_prev.on_click(self._prev_page)

            btn_next = widgets.Button(description="Next Page")
            btn_next.add_class('frie-nav-pill')
            btn_next.disabled = (self.current_page == total_pages)
            btn_next.on_click(self._next_page)

            page_info = widgets.HTML(f"<div style='text-align:center; padding:10px; font-weight:bold; color:#4e4b4c; font-size:1.1em;'>Page {self.current_page} of {total_pages}</div>")
            nav_box = widgets.HBox([btn_prev, page_info, btn_next], layout=widgets.Layout(justify_content='center', align_items='center', margin='20px 0'))

            # Single target display call maps to single context layout
            display(grid, nav_box)

    def _prev_page(self, b):
        self.current_page -= 1
        self._render_paginated_view()

    def _next_page(self, b):
        self.current_page += 1
        self._render_paginated_view()

    def _create_single_card(self, row_dict, show_buttons=True):
        card_html = "<div class='frie-card'>"

        for col_name in self.component_order:
            if col_name not in row_dict: continue
            val = str(row_dict[col_name])
            if not val or val == "nan": continue

            design_style = self.design_map.get(col_name)

            if design_style == "Title":
                card_html += f"<div class='frie-title'>{val}</div>"
            elif design_style == "Institution":
                card_html += f"<div class='frie-inst'>{val}</div>"
            elif design_style == "Hollow Pills (Accent)":
                pills = "".join([f"<span class='frie-pill-accent'>{p.strip()}</span>" for p in val.split(',') if p.strip()])
                card_html += f"<div style='text-align:center; margin-bottom:10px;'>{pills}</div>"
            elif design_style == "Content Box":
                card_html += f"<div class='frie-content-box'>{val}</div>"
            elif design_style == "Raw Text":
                card_html += f"<div class='frie-raw-text'>{val}</div>"

        html_content = widgets.HTML(value=card_html + "</div>", layout=widgets.Layout(width='100%'))

        if not show_buttons:
            return widgets.VBox([html_content], layout=widgets.Layout(width='100%'))

        btn_layout = widgets.Layout(width='95%', margin='5px auto')

        btn_nlp = widgets.Button(description="Toggle NLP Stats", layout=btn_layout)
        btn_nlp.add_class('frie-action-pill')

        link = row_dict.get("Link", "#")
        btn_link = widgets.Button(description="Visit Link", layout=btn_layout)
        btn_link.add_class('frie-action-pill')

        btn_add = widgets.Button(description="Add to Inventory", layout=btn_layout)
        btn_add.add_class('frie-add-pill')

        nlp_html = "<div style='background:#f8f9fa; padding:10px; border-radius:8px; margin: 5px 10px; border-left:4px solid #a6a1a3; font-size:0.85em;'>"
        nlp_html += "<b>Deep Dive Analytics:</b><br>"
        for nlp_col in self.nlp_columns:
            clean_name = self._format_aesthetic_name(nlp_col)
            nlp_val = str(row_dict.get(nlp_col, ''))
            if nlp_val and nlp_val != "nan":
                nlp_html += f"<i>{clean_name}:</i> {nlp_val[:100]}...<br>"
        nlp_html += "</div>"
        
        nlp_overlay = widgets.HTML(value=nlp_html)
        nlp_overlay.layout.display = 'none'

        def toggle_nlp(b, tgt=nlp_overlay):
            tgt.layout.display = 'block' if tgt.layout.display == 'none' else 'none'

        def open_link(b, url=link):
            display(HTML(f"<script>window.open('{url}', '_blank');</script>"))

        def add_inv(b, r=row_dict, btn=btn_add):
            if not any(item.get("Title") == r.get("Title") for item in self.inventory):
                self.inventory.append(r)
            btn.description = "Added!"
            btn.button_style = 'success'
            btn.disabled = True

        btn_nlp.on_click(toggle_nlp)
        btn_link.on_click(open_link)
        btn_add.on_click(add_inv)

        card_box = widgets.VBox([html_content, nlp_overlay, btn_nlp, btn_link, btn_add])
        card_box.add_class('frie-card')

        return card_box

    def _refresh_page_2(self):
        header = widgets.HTML(f"<h3 style='color:#088395; margin-bottom:10px;'>Your Inventory ({len(self.inventory)} Items)</h3>")

        if len(self.inventory) == 0:
            self.page_2_view.children = [
                header,
                widgets.HTML("<p style='color:#4e4b4c;'>No items added yet. Search and add cards from the Discovery page.</p>")
            ]
            return

        btn_csv = widgets.Button(description="Download CSV", layout=widgets.Layout(width='200px', margin='5px'))
        btn_csv.add_class('frie-add-pill')

        btn_xlsx = widgets.Button(description="Download Excel", layout=widgets.Layout(width='200px', margin='5px'))
        btn_xlsx.add_class('frie-add-pill')

        btn_csv.on_click(lambda b: self._trigger_download('csv'))
        btn_xlsx.on_click(lambda b: self._trigger_download('xlsx'))

        export_bar = widgets.HBox([btn_csv, btn_xlsx], layout=widgets.Layout(margin='0 0 25px 0'))

        inv_cards = []
        for item in self.inventory:
            card_widget = self._create_single_card(item, show_buttons=False)
            inv_cards.append(card_widget)

        grid = widgets.GridBox(
            inv_cards,
            layout=widgets.Layout(
                width='100%',
                grid_template_columns='repeat(auto-fill, minmax(320px, 1fr))',
                grid_gap='25px',
                padding='10px',
                align_items='stretch'
            )
        )
        self.page_2_view.children = [header, export_bar, grid]

    def _trigger_download(self, file_type):
        if not self.inventory: 
            print("Inventory is empty. Nothing to download.")
            return

        export_df = pd.DataFrame(self.inventory)
        export_cols = [c for c in export_df.columns if not c.startswith('vector_')]
        export_df = export_df[export_cols]

        filename = f'Friepedia_Inventory.{"csv" if file_type == "csv" else "xlsx"}'

        if file_type == 'csv':
            export_df.to_csv(filename, index=False)
        else:
            export_df.to_excel(filename, index=False)

    def run(self):
        if getattr(self, 'authenticated', False) is False:
            print("Cannot run. Engine initialization failed.")
            return

        clear_output(wait=True)
        self.output_area = widgets.Output()

        self._inject_css()
        header = self._build_header()
        self._setup_page_1()

        self.dynamic_canvas.children = [self.page_1_view]

        master_app = widgets.VBox([header, self.dynamic_canvas])
        master_app.add_class('frie-app-container')
        print("Please Switch the Google Colab Theme to Light Mode for the best experience!")

        self.output_area.clear_output(wait=True)
        with self.output_area:
            display(master_app)

        display(self.output_area)