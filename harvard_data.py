import streamlit as st
import pandas as pd
import sqlite3
import requests
import time
import extra_streamlit_components as stx

# Initialize session state
if "df_metadata" not in st.session_state:
    st.session_state.df_metadata = pd.DataFrame()
    st.session_state.df_media = pd.DataFrame()
    st.session_state.df_colors = pd.DataFrame()
    st.session_state.selected_classification = ""

#Setup
API_KEY = "1e634456-e2c9-4a1c-8290-eb41276035a0"
classification_url = "https://api.harvardartmuseums.org/classification"
object_url = "https://api.harvardartmuseums.org/object"
db_path = "harvard.db"

# Fetch classification options
#Classification Dropdown 
#Get Classifications with objectcount >= 2500
params = {
    "apikey": API_KEY,
    "size": 100
}
response = requests.get(classification_url, params=params)
classification_data = response.json()
classification_records = classification_data.get('records', [])

# Filter classifications with objectcount >= 2500
filtered_classifications = [i for i in classification_records if i.get('objectcount') >= 2500]
df_filtered_classifications = pd.DataFrame(filtered_classifications)
#Extract classification names
classification_names = df_filtered_classifications['name']
classification_name1 = classification_names[[1,2,4,6,7]]

# UI Header
st.title("🏛 Harvard’s Artifacts Collection")
st.text("Harvard’s museums curate renowned collections, pioneer cutting-edge research, and offer educational experiences for everyone.")

# Classification selection
selected_classification = st.selectbox("Select your classification:",classification_name1)

# Collect Data Button
if st.button("Collect data", type="primary"):
    all_records = []
    for page in range(1, 26):
        params = {
            "apikey": API_KEY,
            "size": 100,
            "page": page,
            "classification": selected_classification
        }
        response = requests.get(object_url, params=params)
        data = response.json()
        page_records = data.get("records", [])
        if page_records:
            all_records.extend(page_records)
        else:
            break
        time.sleep(0.5)

    #Separate into metadata, media, colors 
    artifact_metadata, artifact_media,artifact_colors = [],[],[]
    for record in all_records:
        artifact_metadata.append({ "id": record.get("id"),
            "title": record.get("title"),
            "culture": record.get("culture"),
            "period": record.get("period"),
            "century": record.get("century"),
            "medium": record.get("medium"),
            "dimensions": record.get("dimensions"),
            "description": record.get("description"),
            "department": record.get("department"),
            "classification": record.get("classification"),
            "accessionyear": record.get("accessionyear"),
            "accessionmethod": record.get("accessionmethod")
        })  
        artifact_media.append({"objectid": record.get("objectid"),
            "imagecount": record.get("imagecount"),
            "mediacount": record.get("mediacount"),
            "colorcount": record.get("colorcount"),
            "rank": record.get("rank"),
            "datebegin": record.get("datebegin"),
            "dateend": record.get("dateend")
        })
        if record.get("colors"):
            for color in record["colors"]:
                artifact_colors.append({"objectid": record.get("objectid"),
                    "color": color.get("color"),
                    "spectrum": color.get("spectrum"),
                    "hue": color.get("hue"),
                    "percent": color.get("percent"),
                    "css3": color.get("css3")
                })
    # Store in session state
    st.session_state.df_metadata = pd.DataFrame(artifact_metadata)
    st.session_state.df_media = pd.DataFrame(artifact_media)
    st.session_state.df_colors = pd.DataFrame(artifact_colors)
    st.session_state.selected_classification = selected_classification

    st.success(f"✅ Collected {len(all_records)} records for {selected_classification}")
    
# Use session state data
df_metadata = st.session_state.df_metadata
df_media = st.session_state.df_media
df_colors = st.session_state.df_colors


# Tab navigation
tab = stx.tab_bar(data=[
    stx.TabBarItemData(id="view", title="Select Your Choice", description=""),
    stx.TabBarItemData(id="migrate", title="Migrate to SQL", description=""),
    stx.TabBarItemData(id="query", title="SQL Queries", description=""),
], default="view")

# View Tab
if tab == "view":
    if not df_metadata.empty:
        st.info(f"Showing data for classification: {st.session_state.selected_classification}")
        st.subheader("🧾 Artifact Metadata")
        st.dataframe(df_metadata)
        st.subheader("🖼 Artifact Media")
        st.dataframe(df_media)
        st.subheader("🎨 Artifact Colors")
        st.dataframe(df_colors)
    else:
        st.info("📢 No data collected yet. Please select a classification and click 'Collect data'.")

# Tab 2: Migrate to SQL 
elif tab == "migrate":
    insert_tab = st.radio("Choose Action", ["Insert","View"])
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if insert_tab == "Insert":
        # Create tables
        if not df_metadata.empty  and "id" in df_metadata.columns:
            cursor.execute("""CREATE TABLE IF NOT EXISTS artifact_metadata (id INTEGER PRIMARY KEY,title TEXT,culture TEXT,
                period TEXT,
                century TEXT,
                medium TEXT,
                dimensions TEXT,
                description TEXT,
                department TEXT,
                classification TEXT,
                accessionyear INTEGER,
                accessionmethod TEXT)""")  
          
        if not df_media.empty  and "objectid" in df_media.columns:                       
            cursor.execute("""CREATE TABLE IF NOT EXISTS artifact_media (objectid INTEGER,imagecount INTEGER,
                mediacount INTEGER,
                colorcount INTEGER,
                rank INTEGER,
                datebegin INTEGER,
                dateend INTEGER,
                FOREIGN KEY (objectid) REFERENCES artifact_metadata(id))""")
           
        if not df_colors.empty  and "objectid" in df_colors.columns:
            cursor.execute("""CREATE TABLE IF NOT EXISTS artifact_colors (objectid INTEGER,color TEXT,spectrum TEXT,hue TEXT,
                percent REAL,
                css3 TEXT,
                FOREIGN KEY (objectid) REFERENCES artifact_metadata(id))""")
        conn.commit()

        # Insert data
        
        df_metadata.to_sql("artifact_metadata", conn, if_exists="replace", index=False)
        df_media.to_sql("artifact_media", conn, if_exists="replace", index=False)
        df_colors.to_sql("artifact_colors", conn, if_exists="replace", index=False)

        st.success("✅ Data inserted successfully!")

    # View data
    elif insert_tab == "View":
        st.subheader("📘 Artifact Metadata")
        st.dataframe(pd.read_sql_query("SELECT * FROM artifact_metadata", conn))

        st.subheader("🖼️ Artifact Media")
        st.dataframe(pd.read_sql_query("SELECT * FROM artifact_media", conn))

        st.subheader("🎨 Artifact Colors")
        st.dataframe(pd.read_sql_query("SELECT * FROM artifact_colors", conn))

      
# Tab 3: SQL Queries 
elif tab == "query":
   conn = sqlite3.connect(db_path)
   query_dict = {
    #artifact_metadata Table
    "List all artifacts from the 11th century belonging to Byzantine culture.": """
        SELECT * FROM artifact_metadata 
        WHERE century='11th century' AND culture='Byzantine'
    """,
    "What are the unique cultures represented in the artifacts?": """
        SELECT DISTINCT culture FROM artifact_metadata
    """,
    "List all artifacts from the Archaic Period.": """
        SELECT * FROM artifact_metadata 
        WHERE period='Archaic Period'
    """,
    "List artifact titles ordered by accession year in descending order.": """
        SELECT title, accessionyear FROM artifact_metadata 
        ORDER BY accessionyear DESC
    """,
    "How many artifacts are there per department?": """
        SELECT department, COUNT(*) AS total 
        FROM artifact_metadata 
        GROUP BY department
    """,

    #artifact_media Table
    "Which artifacts have more than 1 image?": """
        SELECT * FROM artifact_media 
        WHERE imagecount > 1
    """,
    "What is the average rank of all artifacts?": """
        SELECT AVG(rank) AS average_rank FROM artifact_media
    """,
    "Which artifacts have a higher colorcount than mediacount?": """
        SELECT * FROM artifact_media 
        WHERE colorcount > mediacount
    """,
    "List all artifacts created between 1500 and 1600.": """
        SELECT * FROM artifact_media 
        WHERE datebegin >= 1500 AND dateend <= 1600
    """,
    "How many artifacts have no media files?": """
        SELECT COUNT(*) AS no_media_count 
        FROM artifact_media 
        WHERE mediacount = 0
    """,

    #artifact_colors Table
    "What are all the distinct hues used in the dataset?": """
        SELECT DISTINCT hue FROM artifact_colors
    """,
    "What are the top 5 most used colors by frequency?": """
        SELECT color, COUNT(*) AS frequency 
        FROM artifact_colors 
        GROUP BY color 
        ORDER BY frequency DESC 
        LIMIT 5
    """,
    "What is the average coverage percentage for each hue?": """
        SELECT hue, AVG(percent) AS avg_coverage 
        FROM artifact_colors 
        GROUP BY hue
    """,
    "List all colors used for a given artifact ID.": """
        SELECT * FROM artifact_colors 
        WHERE objectid = ?
    """,
    "What is the total number of color entries in the dataset?": """
        SELECT COUNT(*) AS total_colors FROM artifact_colors
    """,

    #Join-Based Queries
    "List artifact titles and hues for all artifacts belonging to the Byzantine culture.": """
        SELECT m.title, c.hue 
        FROM artifact_metadata m 
        JOIN artifact_colors c ON m.id = c.objectid 
        WHERE m.culture = 'Byzantine'
    """,
    "List each artifact title with its associated hues.": """
        SELECT m.title, c.hue 
        FROM artifact_metadata m 
        JOIN artifact_colors c ON m.id = c.objectid
    """,
    "Get artifact titles, cultures, and media ranks where the period is not null.": """
        SELECT m.title, m.culture, me.rank 
        FROM artifact_metadata m 
        JOIN artifact_media me ON m.id = me.objectid 
        WHERE m.period IS NOT NULL
    """,
    "Find artifact titles ranked in the top 10 that include the color hue 'Grey'.": """
        SELECT m.title, me.rank, c.hue 
        FROM artifact_metadata m 
        JOIN artifact_media me ON m.id = me.objectid 
        JOIN artifact_colors c ON m.id = c.objectid 
        WHERE c.hue = 'Grey' 
        ORDER BY me.rank DESC 
        LIMIT 10
    """,
    "How many artifacts exist per classification, and what is the average media count for each?": """
        SELECT m.classification, COUNT(*) AS total, AVG(me.mediacount) AS avg_media 
        FROM artifact_metadata m 
        JOIN artifact_media me ON m.id = me.objectid 
        GROUP BY m.classification
    """,

    #own SQL Queries for Deeper Insights
    "Most Common Mediums Used Across Artifacts": """
        SELECT medium, COUNT(*) AS count
        FROM artifact_metadata
        GROUP BY medium
        ORDER BY count DESC
        LIMIT 10
    """,
    "Artifacts with Missing Descriptions": """
        SELECT id, title, culture, classification
        FROM artifact_metadata
        WHERE description IS NULL OR description = ''
    """,
    "Average Accession Year by Classification": """
        SELECT classification, AVG(accessionyear) AS avg_year
        FROM artifact_metadata
        GROUP BY classification
        ORDER BY avg_year DESC
    """,
    "Artifacts with Longest Time Span Between Creation Dates": """
        SELECT objectid, datebegin, dateend, (dateend - datebegin) AS duration
        FROM artifact_media
        ORDER BY duration DESC
        LIMIT 10
    """,
    "Top 5 Departments by Artifact Count": """
        SELECT department, COUNT(*) AS total
        FROM artifact_metadata
        GROUP BY department
        ORDER BY total DESC
        LIMIT 5
    """,
    "Most Frequently Used Hue Across All Artifacts": """
        SELECT hue, COUNT(*) AS frequency
        FROM artifact_colors
        GROUP BY hue
        ORDER BY frequency DESC
        LIMIT 1
    """
   }
   query_titles = list(query_dict.keys())
   selected_query = st.selectbox("Choose a query", query_titles)
# Handle parameterized query
   if "?" in query_dict[selected_query]:
        artifact_id = st.number_input("Enter Artifact ID", min_value=1)
        df_result = pd.read_sql_query(query_dict[selected_query], conn, params=(artifact_id,))
   else:
        df_result = pd.read_sql_query(query_dict[selected_query], conn)

   st.subheader(f"📊 Results for: {selected_query}")
   st.dataframe(df_result)
