from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

app = FastAPI() # Create an instance of the app

# Allow browser requests from any origin (public search API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database helper function
def get_db_connection():
    conn = sqlite3.connect('local_crocdb.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

# Request models to match Crocdb's expected POST payloads
class EntryRequest(BaseModel):
    slug: str

class SearchRequest(BaseModel):
    query: str
    platform: str = None

@app.post("/entry")
def get_entry(req: EntryRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch the main game entry
    cursor.execute("SELECT * FROM entries WHERE slug = ?", (req.slug,))
    entry_row = cursor.fetchone()
    
    if not entry_row:
        conn.close()
        return {"info": {"error": "Entry not found"}, "data": {}}
        
    # Fetch the associated download links
    cursor.execute("SELECT * FROM links WHERE entry_slug = ?", (req.slug,))
    link_rows = cursor.fetchall()
    
    conn.close()
    
    # Format the response to match the exact schema
    entry_data = dict(entry_row)
    entry_data["regions"] = ["us"] # Simplified region mapping
    entry_data["links"] = [dict(link) for link in link_rows]
    
    return {
        "info": {},
        "data": {
            "entry": entry_data
        }
    }

@app.post("/search")
def search_entries(req: SearchRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    search_term = f"%{req.query}%"
    
    if req.platform:
        cursor.execute("SELECT * FROM entries WHERE title LIKE ? AND platform_id = ? LIMIT 50", (search_term, req.platform))
    else:
        cursor.execute("SELECT * FROM entries WHERE title LIKE ? LIMIT 50", (search_term,))
        
    entry_rows = cursor.fetchall()
    
    results = []
    for row in entry_rows:
        entry_data = dict(row)
        
        # Fetch links for each result
        cursor.execute("SELECT * FROM links WHERE entry_slug = ?", (entry_data['slug'],))
        link_rows = cursor.fetchall()
        
        entry_data["regions"] = ["us"] 
        entry_data["links"] = [dict(link) for link in link_rows]
        results.append(entry_data)
        
    conn.close()
    
    return {
        "info": {},
        "data": {
            "results": results,
            "current_results": len(results),
            "total_results": len(results), # Simplified pagination for the local clone
            "current_page": 1,
            "total_pages": 1
        }
    }
